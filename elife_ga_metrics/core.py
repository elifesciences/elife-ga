#!/usr/bin/python
# -*- coding: utf-8 -*-

# Analytics API:
# https://developers.google.com/analytics/devguides/reporting/core/v3/reference

__author__ = [
    'Luke Skibinski <l.skibinski@elifesciences.org>',
]

from os.path import join
from collections import Counter
import os, sys, re, argparse, json, time, random, json
from datetime import datetime, timedelta
from pprint import pprint
import httplib2
from apiclient.errors import HttpError
from apiclient import errors
from apiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import SignedJwtAssertionCredentials
from oauth2client import file as oauth_file
from httplib2 import Http
from elife_ga_metrics.utils import ymd, memoized
import logging

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.level = logging.INFO

OUTPUT_DIR = join(os.path.dirname(os.path.dirname(__file__)), 'output')
VIEWS_INCEPTION = datetime(year=2014, month=3, day=12)
DOWNLOADS_INCEPTION = datetime(year=2015, month=2, day=13)

# Declare command-line flags.
argparser = argparse.ArgumentParser(add_help=False)
argparser.add_argument('table_id', type=str,
                     help=('The table ID of the profile you wish to access. '
                           'Format is ga:xxx where xxx is your profile ID.'))

#
# utils
#

def enplumpen(artid):
    "takes an article id like e01234 and returns a DOI like 10.7554/eLife.01234"
    return artid.replace('e', '10.7554/eLife.')

def deplumpen(artid):
    "takes an article id like eLife.01234 and returns a DOI like e01234"
    try:
        return "e" + artid.split('.')[1]
    except IndexError:
        LOG.error("unable to deplump %r", artid)
        return artid

def sanitize_ga_response(ga_response):
    """The GA responses contain no sensitive information, however it does
    have a collection of identifiers I'd feel happier if the world didn't
    have easy access to."""
    for key in ['profileInfo', 'id', 'selfLink']:
        if ga_response.has_key(key):
            del ga_response[key]
    if ga_response['query'].has_key('ids'):
        del ga_response['query']['ids']
    return ga_response

@memoized
def ga_service(table_id):
    service_name = 'analytics'    
    settings_file = 'client-secrets.json'
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

#
#
#

def event_counts_query(table_id, from_date, to_date):
    "returns the raw GA results for PDF downloads between the two given dates"
    assert isinstance(from_date, datetime), "'from' date must be a datetime object. received %r" % from_date
    assert isinstance(to_date, datetime), "'to' date must be a datetime object. received %r" % to_date
    service = ga_service(table_id)
    return service.data().ga().get(
        ids = table_id,
        max_results=10000, # 10,000 is the max GA will ever return
        start_date = ymd(from_date),
        end_date = ymd(to_date),
        metrics = 'ga:totalEvents',
        dimensions = 'ga:eventLabel',
        sort = '-ga:totalEvents',
        # ';' separates AND expressions, ',' separates OR expressions
        filters = r'ga:eventAction==Download;ga:eventCategory==Article;ga:eventLabel=~pdf-article',
    )

def download_counts(row_list):
    "parses the list of rows returned by google to extract the doi and count"
    def parse(row):
        label, count = row
        return label.split('::')[0], int(count)
    return dict(map(parse, row_list))

def path_counts_query(table_id, from_date, to_date):
    "returns the raw GA results for article page views between the two given dates"
    assert isinstance(from_date, datetime), "'from' date must be a datetime object. received %r" % from_date
    assert isinstance(to_date, datetime), "'to' date must be a datetime object. received %r" % to_date

    # regular expression suffixes (escape special chars)
    suffix_list = [
        '\.full',
        '\.abstract',
        '\.short',
        '/abstract-1',
        '/abstract-2',
    ]
    # wrap each suffix in a zero-or-one group. ll: ['(\.full)?', '(\.abstract)?', ...]
    suffix_list = ['(%s)?' % suffix for suffix in suffix_list]

    # pipe-delimit the suffix list. ll: '(\.full)?|(\.abstract)?|...)'
    suffix_str = '|'.join(suffix_list)
    
    service = ga_service(table_id)    
    return service.data().ga().get(
        ids = table_id,
        max_results=10000, # 10,000 is the max GA will ever return
        start_date = ymd(from_date),
        end_date = ymd(to_date),
        metrics = 'ga:pageviews',
        dimensions = 'ga:pagePath',
        sort = '-ga:pageviews',
        filters = ','.join([
            # these filters are OR'ed
            r'ga:pagePath=~^/content/.*/e[0-9]{5}(%s)$' % suffix_str,
            r'ga:pagePath=~^/content/.*/elife\.[0-9]{5}$',
        ])
    )


TYPE_MAP = {
    None: 'full',
    'full': 'full',
    'abstract': 'abstract',
    'short': 'abstract',
    'abstract-1': 'abstract',
    'abstract-2': 'digest'
}
SPLITTER = re.compile('\.|/')

def article_count(pair):
    "figures out the type of the given path using the suffix (if one available)"
    try:
        if pair[0].lower().startswith('/content/early/'):
            # handles POA article variation 1 "/content/early/yyyy/mm/dd/doi/" type urls
            bits = pair[0].split('/', 6)
            bits[-1] = deplumpen(bits[-1])

        elif pair[0].lower().startswith('/content/elife/early/'):
            # handles POA article variation 2 "/content/elife/early/yyyy/mm/dd/doi/" type urls
            bits = pair[0].split('/', 7)
            bits[-1] = deplumpen(bits[-1])

        elif pair[0].lower().startswith('/content/elife/'):
            # handles valid but unsupported /content/elife/volume/id paths
            # these paths appear in PDF files I've been told
            bits = pair[0].split('/', 4)
            
        else:
            # handles standard /content/volume/id/ paths
            bits = pair[0].split('/', 3)
        
        art = bits[-1]
        art = art.lower() # website isn't case sensitive, we are
        more_bits = re.split(SPLITTER, art, maxsplit=1)
        
        suffix = None
        if len(more_bits) > 1:
            art, suffix = more_bits
        assert suffix in TYPE_MAP, "unknown suffix %r! received: %r split to %r" % (suffix, pair, more_bits)
        return art, TYPE_MAP[suffix], int(pair[1])

    except AssertionError, e:
        # we have an unhandled path
        #LOG.warn("skpping unhandled path %s (%r)", pair, e)
        LOG.warn("skpping unhandled path %s", pair)

def article_counts(path_count_pairs):
    """takes raw path data from GA and groups by article, returning a
    list of (artid, full-count, abstract-count, digest-count)"""
    
    # for each path, build a list of path_type: value
    article_groups = {}
    for pair in path_count_pairs:
        row = Counter({
            'full': 0,
            'abstract': 0,
            'digest': 0,
        })
        triplet = article_count(pair)
        if not triplet:
            continue # skip bad row
        art, art_type, count = triplet
        group = article_groups.get(art, [row])
        group.append(Counter({art_type: count}))
        article_groups[art] = group

    # take our list of Counter objects and count them up
    def update(a,b):
        # https://docs.python.org/2/library/collections.html#collections.Counter.update
        a.update(b)
        return a

    return {enplumpen(art): reduce(update, group) for art, group in article_groups.items()}    

def query_ga(query):
    "talks to google with the given query, applying exponential back-off if rate limited"
    num_attempts = 5
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
            error = json.loads(e.content)
            if error.get('code') == 403 \
              and error.get('errors')[0].get('reason') in ['rateLimitExceeded', 'userRateLimitExceeded']:

              # apply exponential backoff.
              val = (2 ** n) + random.randint(0, 1000) / 1000
              LOG.info("rate limited, backing off %r", val)
              time.sleep(val)

            else:
              # some other sort of HttpError, re-raise
              LOG.exception("unhandled exception!")
              raise

        except AccessTokenRefreshError:
            # Handle Auth errors.
            LOG.exception ('The credentials have been revoked or expired, please re-run '
                   'the application to re-authorize')
            raise    

def query_ga_write_results(*args, **kwargs):
    response = query_ga(*args, **kwargs)
    query = response['query']            
    from_date = datetime.strptime(query['start-date'], "%Y-%m-%d")
    to_date = datetime.strptime(query['end-date'], "%Y-%m-%d")
    results_type = 'downloads' if 'ga:eventLabel' in query['filters'] else 'views'
    path = output_path(results_type, from_date, to_date)
    write_results(response, path)
    return response

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
    return join(OUTPUT_DIR, results_type, dt_str + ".json" + partial)

def write_results(results, path):
    "writes sanitised response from Google as json to the given path"
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        assert os.system("mkdir -p %s" % dirname) == 0, "failed to make output dir %r" % dirname
    LOG.info("writing %r", path)
    json.dump(sanitize_ga_response(results), open(path, 'w'), indent=4, sort_keys=True)
    return path
    

#
#
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

def article_views(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns article view data either from the cache or from talking to google"
    if not valid_view_dt_pair((from_date, to_date)):
        LOG.warning("given date range %r for views is older than known inception %r, skipping", (ymd(from_date), ymd(to_date)), VIEWS_INCEPTION)
        return {}
    
    path = output_path('views', from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    elif only_cached:
        # no cache exists and we've been told to only use cache.
        # no results found.
        raw_data = {}
    else:
        # talk to google
        raw_data = query_ga_write_results(path_counts_query(table_id, from_date, to_date))
        write_results(raw_data, path)
    return article_counts(raw_data.get('rows', []))

def article_downloads(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns article download data either from the cache or from talking to google"
    if not valid_downloads_dt_pair((from_date, to_date)):
        LOG.warning("given date range %r for downloads is older than known inception %r, skipping", (ymd(from_date), ymd(to_date)), DOWNLOADS_INCEPTION)
        return {}
    path = output_path('downloads', from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    elif only_cached:
        # no cache exists and we've been told to only use cache.
        # no results found.
        raw_data = {}
    else:
        # talk to google
        raw_data = query_ga_write_results(event_counts_query(table_id, from_date, to_date))
        write_results(raw_data, path)
    return download_counts(raw_data.get('rows', []))

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
    """has to be called with the 'table-id', which looks like 12345678
    call this app like: python core.py 'ga:12345678'"""
    to_date = from_date = datetime.now() - timedelta(days=1)
    use_cached, use_only_cached = True, not os.path.exists('client-secrets.json')
    return article_metrics(table_id, from_date, to_date, use_cached, use_only_cached)

if __name__ == '__main__':
    pprint(main(sys.argv[1]))
