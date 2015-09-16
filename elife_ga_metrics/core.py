#!/usr/bin/python
# -*- coding: utf-8 -*-

# Analytics API:
# https://developers.google.com/analytics/devguides/reporting/core/v3/reference

__author__ = [
    'Luke Skibinski <l.skibinski@elifesciences.org>',
    'Nick Mihailovski <api.nickm@gmail.com>', # (ga client sample)
]

from os.path import join
from collections import Counter
import os, sys, re, argparse, json, time, random, json
from datetime import datetime, timedelta
from pprint import pprint

from apiclient.errors import HttpError
from apiclient import sample_tools
from apiclient import errors
from oauth2client.client import AccessTokenRefreshError

import logging

logging.basicConfig()
LOG = logging.getLogger(__name__)

OUTPUT_DIR = join(os.path.dirname(os.path.dirname(__file__)), 'output')
VIEWS_INCEPTION = datetime(year=2014, month=03, day=12)
DOWNLOADS_INCEPTION = datetime(year=2015, month=02, day=13)

# Declare command-line flags.
argparser = argparse.ArgumentParser(add_help=False)
argparser.add_argument('table_id', type=str,
                     help=('The table ID of the profile you wish to access. '
                           'Format is ga:xxx where xxx is your profile ID.'))

#
# utils
#

def ymd(dt):
    return dt.strftime("%Y-%m-%d")

def enplumpen(artid):
    "takes an article id like e01234 and returns a DOI"
    return artid.replace('e', '10.7554/eLife.')

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

#
#
#

def event_counts_query(service, table_id, from_date, to_date):
    "returns the raw GA results for PDF downloads between the two given dates"
    assert isinstance(from_date, datetime), "'from' date must be a datetime object. received %r" % from_date
    assert isinstance(to_date, datetime), "'to' date must be a datetime object. received %r" % to_date
    
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
    def parse(row):
        label, count = row
        return label.split('::')[0], count
    return dict(map(parse, row_list))

def path_counts_query(service, table_id, from_date, to_date):
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
    
    return service.data().ga().get(
        ids = table_id,
        max_results=10000, # 10,000 is the max GA will ever return
        start_date = ymd(from_date),
        end_date = ymd(to_date),
        metrics = 'ga:pageviews',
        dimensions = 'ga:pagePath',
        sort = '-ga:pageviews',
        #filters = 'ga:pagePath=~/e[0-9]+((\.full)?|(\.abstract)|(\.abstract-2)(/abstract))?$',
        filters = r'ga:pagePath=~/e[0-9]{5}(%s)$' % suffix_str,
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
        if '/elife/' in pair[0]:
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
    except AssertionError:
        # we have an unhandled path
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
            LOG.info("query attempt %r" % (n + 1))
            response = query.execute()
            query = response['query']
            from_date = datetime.strptime(query['start-date'], "%Y-%m-%d")
            to_date = datetime.strptime(query['end-date'], "%Y-%m-%d")
            results_type = 'downloads' if 'ga:eventLabel' in query['filters'] else 'views'
            path = output_path(results_type, from_date, to_date)
            write_results(response, path)
            return response

        except TypeError, error:      
            # Handle errors in constructing a query.
            print ('There was an error in constructing your query : %s' % error)
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
            print ('The credentials have been revoked or expired, please re-run '
                   'the application to re-authorize')
            raise    



def output_path(results_type, from_date, to_date):
    assert results_type in ['views', 'downloads'], "results type must be either 'views' or 'downloads'"
    if not isinstance(from_date, str): # they tend to come as pairs
        from_date, to_date = ymd(from_date), ymd(to_date)
    # different formatting if two different dates are provided
    if from_date == to_date:
        dt_str = to_date
    else:
        dt_str = "%s_%s" % (from_date, to_date)

    partial = ""
    if to_date == ymd(datetime.now()):
        # anything gathered today will only ever be partial
        # when run again on a future day there will be cache miss
        # and the full results downloaded
        partial = ".partial"
        
    # ll: output/downloads/2014-04-01.json
    # ll: output/views/2014-04-01_2015-01-01.json
    return join(OUTPUT_DIR, results_type, dt_str + ".json" + partial)

def write_results(results, path):
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        assert os.system("mkdir -p %s" % dirname) == 0, "failed to make output dir %r" % dirname
    LOG.info("writing %r", path)
    json.dump(sanitize_ga_response(results), open(path, 'w'), indent=4, sort_keys=True)
    return path
    

#
#
#

def wrangle_dates(result_type, from_date, to_date):
    "total hack"
    if from_date == to_date:
        # we use 'None' on the `to_date` param to indicate 'the same day'
        to_date = None
    inception = DOWNLOADS_INCEPTION if result_type == 'downloads' else VIEWS_INCEPTION
    if from_date < inception:
        LOG.warning("given `from_date` %r for %s is older than known inception %r. capping", from_date, result_type, inception)
        from_date = inception

    # now that from_date has been adjusted, we can set the to_date
    if not to_date:
        to_date = from_date

    # output_path is just a convenience. sorry.
    return from_date, to_date, output_path(result_type, from_date, to_date)    

def article_views(service, table_id, from_date, to_date, cached=False):
    from_date, to_date, path = wrangle_dates('views', from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    else:
        raw_data = query_ga(path_counts_query(service, table_id, from_date, to_date))
        write_results(raw_data, path)
    return article_counts(raw_data.get('rows', []))

def article_downloads(service, table_id, from_date, to_date=None, cached=False):
    from_date, to_date, path = wrangle_dates('downloads', from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    else:
        raw_data = query_ga(event_counts_query(service, table_id, from_date, to_date))
        write_results(raw_data, path)
    return download_counts(raw_data['rows'])

def article_metrics(service, table_id, from_date, to_date, cached=False):
    "returns a dictionary of article metrics, combining the pdf downloads and the views"
    views = article_views(service, table_id, from_date, to_date, cached)
    downloads = article_downloads(service, table_id, from_date, to_date, cached)

    download_dois = set(downloads.keys())
    views_dois = set(views.keys())
    sset = download_dois - views_dois
    if sset:
        msg = "downloads with no corresponding page view: %r"
        LOG.warn(msg, {missing_doi:downloads[missing_doi] for missing_doi in list(sset)})
    
    # update the views in-place :(
    #for key, val in views.items():
    #    views[key]['pdf'] = downloads.get(key, 0)
    #return views

    # keep the two separate until we introduce POAs? or just always
    return {'views': views, 'downloads': downloads}


#
# bootstrap
#

def ga_service(table_id):
    # Authenticate and construct service.
    service, flags = sample_tools.init(
      [__name__, table_id], 'analytics', 'v3', __doc__, __file__, parents=[argparser],
      scope='https://www.googleapis.com/auth/analytics.readonly')
    return service

def main(table_id):
    """has to be called with the 'table-id', which looks like 12345678
    call this app like: python core.py 'ga:12345678'"""
    service = ga_service(table_id)
    to_date = from_date = datetime.now()
    return article_metrics(service, table_id, from_date, to_date, cached=True)

if __name__ == '__main__':
    pprint(main(sys.argv[1]))
