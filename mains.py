#!/usr/bin/python
# -*- coding: utf-8 -*-

# Analytics API:
# https://developers.google.com/analytics/devguides/reporting/core/v3/reference

__author__ = ['api.nickm@gmail.com (Nick Mihailovski)',
              'Luke Skibinski <l.skibinski@elifesciences.org>']

from os.path import join
from collections import Counter
import os, sys, re, argparse, json
from datetime import datetime, timedelta
from pprint import pprint

from apiclient.errors import HttpError
from apiclient import sample_tools
from oauth2client.client import AccessTokenRefreshError

import logging

LOG = logging.getLogger(__name__)

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

#
#
#

def event_counts(service, table_id, from_date, to_date):
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
        #dimensions='ga:url,ga:keyword',
        sort = '-ga:pageviews',
        #filters = 'ga:pagePath=~/e[0-9]+((\.full)?|(\.abstract)|(\.abstract-2)(/abstract))?$',
        filters = r'ga:pagePath=~/e[0-9]{5}(%s)$' % suffix_str,
    )

def article_counts(path_count_pairs):
    """takes raw path data from GA and groups by article, returning a
    list of (artid, full-count, abstract-count, digest-count)"""

    type_map = {
        None: 'full',
        'full': 'full',
        'abstract': 'abstract',
        'short': 'abstract',
        'abstract-1': 'abstract',
        'abstract-2': 'digest'
    }
    splitter = re.compile('\.|/')

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
            more_bits = re.split(splitter, art, maxsplit=1)
            suffix = None
            if len(more_bits) > 1:
                art, suffix = more_bits
            assert suffix in type_map, "unknown suffix %r! received: %r split to %r" % (suffix, pair, more_bits)
            return art, type_map[suffix], int(pair[1])
        except AssertionError:
            # we have an unhandled path
            LOG.warn("skpping unhandled path %s", pair)
    
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
            continue # bad row
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

def query_ga(q):
    # Try to make a request to the API. Print the results or handle errors.
    try:
        return q.execute()
            
    except TypeError, error:      
        # Handle errors in constructing a query.
        print ('There was an error in constructing your query : %s' % error)
        raise

    except HttpError, error:
        # Handle API errors.
        print ('Arg, there was an API error : %s : %s' %
               (error.resp.status, error._get_reason()))
        raise

    except AccessTokenRefreshError:
        # Handle Auth errors.
        print ('The credentials have been revoked or expired, please re-run '
               'the application to re-authorize')
        raise    

def output_path(results_type, from_date, to_date):
    # ll: output/downloads/2015-09-10.raw
    assert results_type in ['views', 'downloads'], "results type must be either 'views' or 'downloads'"
    from_date, to_date = ymd(from_date), ymd(to_date)
    return join('output', results_type, to_date + ".json")

def write_results(results, path):
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        assert os.system("mkdir -p %s" % dirname) == 0, "failed to make output dir"
    json.dump(results, open(path, 'w'), indent=4)
    return path
    

#
#
#

def article_views(service, table_id, from_date, to_date, cached=False):
    path = output_path('views', from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    else:
        raw_data = query_ga(path_counts_query(service, table_id, from_date, to_date))
        write_results(raw_data, path)
    return article_counts(raw_data['rows'])

def article_downloads(service, table_id, from_date, to_date, cached=False):
    path = output_path('downloads', from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    else:
        raw_data = query_ga(event_counts(service, table_id, from_date, to_date))
        write_results(raw_data, path)
    return download_counts(raw_data['rows'])



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
    call this app like: python mains.py 'ga:12345678'"""

    service = ga_service(table_id)
    
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    cached = True

    return {'views': article_views(service, table_id, yesterday, today, cached),
            'downloads': article_downloads(service, table_id, yesterday, today, cached)}

if __name__ == '__main__':
    pprint(main(sys.argv[1]))
