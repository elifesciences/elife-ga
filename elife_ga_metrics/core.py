#!/usr/bin/python
# -*- coding: utf-8 -*-

# Analytics API:
# https://developers.google.com/analytics/devguides/reporting/core/v3/reference

__author__ = [
    'Luke Skibinski <l.skibinski@elifesciences.org>',
]

from os.path import join
from collections import Counter
import os, re, argparse, json, time, random, json
from datetime import datetime, timedelta
from pprint import pprint
import httplib2
from googleapiclient.errors import HttpError
from googleapiclient import errors
from googleapiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import SignedJwtAssertionCredentials
from oauth2client import file as oauth_file
from httplib2 import Http
from elife_ga_metrics.utils import ymd, memoized, firstof
import logging

import elife_v1, elife_v2

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.level = logging.INFO

OUTPUT_SUBDIR = 'output'

SECRETS_LOCATIONS = [
    'client-secrets.json',
    '/etc/elife-ga-metrics/client-secrets.json'
]

def output_dir():
    root = os.path.dirname(os.path.dirname(__file__))
    if os.environ.get('TESTING'):
        root = os.getenv('TEST_OUTPUT_DIR')
    return join(root, OUTPUT_SUBDIR)

VIEWS_INCEPTION = datetime(year=2014, month=3, day=12)
DOWNLOADS_INCEPTION = datetime(year=2015, month=2, day=13)

SITE_SWITCH = datetime(year=2016, month=2, day=9)

#
# custom classes
#

class NoSettings(RuntimeError):
    def __init__(self, settings_locations):
        msg = "could not find the credentials file! I looked here:\n%s" % '\n'.join(settings_locations)
        super(NoSettings, self).__init__(msg)

#
# utils
#

def valid_dt_pair(dt_pair, inception):
    "returns true if both dates are greater than the date we started collecting on"    
    from_date, to_date = dt_pair
    return from_date >= inception and to_date >= inception

def valid_view_dt_pair(dt_pair):
    "returns true if both dates are greater than the date we started collecting on"
    return valid_dt_pair(dt_pair, VIEWS_INCEPTION)

def valid_downloads_dt_pair(dt_pair):
    "returns true if both dates are greater than the date we started collecting on"
    return valid_dt_pair(dt_pair, DOWNLOADS_INCEPTION)

SANITISE_THESE = ['profileInfo', 'id', 'selfLink']

def sanitize_ga_response(ga_response):
    """The GA responses contain no sensitive information, however it does
    have a collection of identifiers I'd feel happier if the world didn't
    have easy access to."""
    for key in SANITISE_THESE:
        if ga_response.has_key(key):
            del ga_response[key]
    if ga_response['query'].has_key('ids'):
        del ga_response['query']['ids']
    return ga_response

def oauth_secrets():
    settings_file_locations = SECRETS_LOCATIONS
    settings_file = firstof(os.path.exists, settings_file_locations)
    if not settings_file:
        raise NoSettings(settings_file_locations)
    return settings_file

@memoized
def ga_service():
    service_name = 'analytics'
    settings_file = oauth_secrets()
    settings_data = sd = json.load(open(settings_file, 'r'))
    scope = 'https://www.googleapis.com/auth/analytics.readonly'
    
    storage = oauth_file.Storage(service_name + '.dat')
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = SignedJwtAssertionCredentials(sd['client_email'], sd['private_key'], scope)

    http = Http()
    credentials.authorize(http) # does this 'put' back into the credentials file??
    service = build(service_name, 'v3', http=http)
    return service

def query_ga(query_map, num_attempts=5):
    "talks to google with the given query, applying exponential back-off if rate limited"

    # build the query
    if isinstance(query_map, dict):
        query = ga_service().data().ga().get(**query_map)
    else:
        # a regular query object can be passed in
        query = query_map

    # execute it
    for n in range(0, num_attempts):
        try:
            if n > 1:
                LOG.info("query attempt %r" % (n + 1))
            else:
                LOG.info("querying ...")
            return query.execute()

        except TypeError, error:      
            # Handle errors in constructing a query.
            LOG.exception('There was an error in constructing your query : %s', error)
            raise
        
        except errors.HttpError, e:
            LOG.warn("HttpError ... can we recover?")

            status_code = e.resp.status
            
            if status_code in [403, 503]:

                # apply exponential backoff.
                val = (2 ** n) + random.randint(0, 1000) / 1000
                if status_code == 503:
                    # wait even longer
                    val = val * 2
                
                LOG.info("rate limited. backing off %r", val)
                time.sleep(val)

            else:
                # some other sort of HttpError, re-raise
                LOG.exception("unhandled exception!")
                raise

        except AccessTokenRefreshError:
            # Handle Auth errors.
            LOG.exception ('The credentials have been revoked or expired, please re-run ' \
                   'the application to re-authorize')
            raise
    
    raise AssertionError("Failed to execute query after %s attempts" % num_attempts)

def output_path(results_type, from_date, to_date):
    "generates a path for results of the given type"
    assert results_type in ['views', 'downloads'], "results type must be either 'views' or 'downloads'"
    if isinstance(from_date, str): # given strings
        from_date_dt = datetime.strptime(from_date, "%Y-%m-%d")
        to_date_dt = datetime.strptime(to_date, "%Y-%m-%d")
    else: # given dt objects
        from_date_dt, to_date_dt = from_date, to_date
        from_date, to_date = ymd(from_date), ymd(to_date)

    now, now_dt = ymd(datetime.now()), datetime.now()

    # different formatting if two different dates are provided
    if from_date == to_date:
        dt_str = to_date
    else:
        dt_str = "%s_%s" % (from_date, to_date)

    partial = ""
    if to_date == now or to_date_dt >= now_dt:
        # anything gathered today or for the future (month ranges)
        # will only ever be partial. when run again on a future day
        # there will be cache miss and the full results downloaded
        partial = ".partial"
    
    # ll: output/downloads/2014-04-01.json
    # ll: output/views/2014-01-01_2014-01-31.json.partial
    return join(output_dir(), results_type, dt_str + ".json" + partial)

def output_path_from_results(response):
    """determines a path where the given response can live, using the
    dates within the response and guessing the request type"""
    assert response.has_key('query') and response['query'].has_key('filters'), \
      "can't parse given response: %r" % str(response)
    query = response['query']
    from_date = datetime.strptime(query['start-date'], "%Y-%m-%d")
    to_date = datetime.strptime(query['end-date'], "%Y-%m-%d")
    results_type = 'downloads' if 'ga:eventLabel' in query['filters'] else 'views'
    return output_path(results_type, from_date, to_date)

def write_results(results, path):
    "writes sanitised response from Google as json to the given path"
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        assert os.system("mkdir -p %s" % dirname) == 0, "failed to make output dir %r" % dirname
    LOG.info("writing %r", path)
    #json.dump(results, open(path + '.raw', 'w'), indent=4, sort_keys=True)
    json.dump(sanitize_ga_response(results), open(path, 'w'), indent=4, sort_keys=True)
    return path

def query_ga_write_results(query, num_attempts=5):
    "convenience. queries GA then writes the results, returning both the original response and the path to results"
    response = query_ga(query, num_attempts)
    path = output_path_from_results(response)
    return response, write_results(response, path)


#
#
#

def module_picker(from_date, to_date):
    daily = from_date == to_date
    module = elife_v1
    if daily:
        if from_date > SITE_SWITCH:
            module = elife_v2
    else: # monthly
        # TODO, WARN: partial month logic here
        if SITE_SWITCH > from_date and SITE_SWITCH < to_date:
            # everything up to the switchover will not be counted correctly
            # in this scenario, we have 9 days worth
            module = elife_v2
    return module

#
#
#


def article_views(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns article view data either from the cache or from talking to google"
    if not valid_view_dt_pair((from_date, to_date)):
        LOG.warning("given date range %r for views is older than known inception %r, skipping", (ymd(from_date), ymd(to_date)), VIEWS_INCEPTION)
        return {}
    
    path = output_path('views', from_date, to_date)
    module = module_picker(from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    elif only_cached:
        # no cache exists and we've been told to only use cache.
        # no results found.
        raw_data = {}
    else:
        # talk to google
        query_map = module.path_counts_query(table_id, from_date, to_date)
        raw_data, actual_path = query_ga_write_results(query_map)
        assert path == actual_path, "the expected output path (%s) doesn't match the path actually written to (%s)" % (path, actual_path)
    return module.path_counts(raw_data.get('rows', []))

def article_downloads(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns article download data either from the cache or from talking to google"
    if not valid_downloads_dt_pair((from_date, to_date)):
        LOG.warning("given date range %r for downloads is older than known inception %r, skipping", (ymd(from_date), ymd(to_date)), DOWNLOADS_INCEPTION)
        return {}
    path = output_path('downloads', from_date, to_date)
    module = module_picker(from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    elif only_cached:
        # no cache exists and we've been told to only use cache.
        # no results found.
        raw_data = {}
    else:
        # talk to google
        query_map = module.event_counts_query(table_id, from_date, to_date)
        raw_data, actual_path = query_ga_write_results(query_map)
        assert path == actual_path, "the expected output path (%s) doesn't match the path actually written to (%s)" % (path, actual_path)
    return module.event_counts(raw_data.get('rows', []))

def article_metrics(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns a dictionary of article metrics, combining both article views and pdf downloads"
    views = article_views(table_id, from_date, to_date, cached, only_cached)
    downloads = article_downloads(table_id, from_date, to_date, cached, only_cached)

    download_dois = set(downloads.keys())
    views_dois = set(views.keys())
    sset = download_dois - views_dois
    if sset:
        msg = "downloads with no corresponding page view: %r"
        LOG.warn(msg, {missing_doi:downloads[missing_doi] for missing_doi in list(sset)})
    
    # keep the two separate until we introduce POAs? or just always
    return {'views': views, 'downloads': downloads}


#
# bootstrap
#

def main(table_id):
    to_date = from_date = datetime.now() - timedelta(days=1)
    # use cache if available. use cache exclusively if the client-secrets.json file not found
    #use_cached, use_only_cached = True, not os.path.exists('client-secrets.json')
    use_cached, use_only_cached = True, not oauth_secrets()
    print 'cached?',use_cached
    print 'only cached?',use_only_cached
    #use_cached = use_only_cached = False
    return article_metrics(table_id, from_date, to_date, use_cached, use_only_cached)

if __name__ == '__main__':
    "call this app like: GA_TABLE='ga:12345678' python core.py"
    assert os.environ.has_key('GA_TABLE'), "the environment variable 'GA_TABLE' not found. It looks like 'ga:12345678'"
    pprint(main(os.environ['GA_TABLE']))
