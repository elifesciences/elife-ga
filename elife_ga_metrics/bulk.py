"""Bulk loading of eLife metrics from Google Analytics."""

import os, sys, time, random, json
import core
from datetime import datetime, date, timedelta
from apiclient.http import BatchHttpRequest
from apiclient import errors
from pprint import pprint
import logging
from collections import OrderedDict

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.level = logging.INFO

#
# bulk requests to ga
#

def dt_range(from_date, to_date):
    """returns series of datetime objects starting at from_date
    and ending on to_date inclusive."""
    if from_date > to_date:
        to_date, from_date = from_date, to_date
    diff = to_date - from_date
    for increment in range(0, diff.days + 1):
        yield from_date + timedelta(days=increment)

def generate_queries(service, table_id, query_func, from_date, to_date, use_cached=False):
    "returns a list of queries to be executed by google"
    query_list = []
    query_type = 'views' if query_func == core.path_counts_query else 'downloads'
    for date_in_time in dt_range(from_date, to_date):
        output_path = core.output_path(query_type, date_in_time, date_in_time)
        if use_cached:
            if os.path.exists(output_path):
                LOG.info("we have %r results for %r already", query_type, date_in_time)
                continue
            else:
                LOG.info("no cache file for %r results for %r", query_type, date_in_time)
        else:
            LOG.info("couldn't find path %r", output_path)
        q = query_func(service, table_id, date_in_time, date_in_time)
        query_list.append(q)
    return query_list

def exec_query(query):
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
            path = core.output_path(results_type, from_date, to_date)
            core.write_results(response, path)
            return response
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

def bulk_query(query_list):
    "executes a list of queries"
    return map(exec_query, query_list)

#
#
#

def daily_metrics_between(table_id, from_date, to_date, use_cached=True):
    "does a DAILY query between two dates, NOT a single query within a date range"
    service = core.ga_service(table_id)
    views_from_date, views_to_date, _ = core.wrangle_dates('views', from_date, to_date)
    pdf_from_date, pdf_to_date, _ = core.wrangle_dates('downloads', from_date, to_date)

    # ensure our raw data exists on disk
    query_list = []
    query_list.extend(generate_queries(service, table_id, core.path_counts_query, views_from_date, views_to_date, use_cached))
    query_list.extend(generate_queries(service, table_id, core.event_counts_query, pdf_from_date, pdf_to_date, use_cached))
    bulk_query(query_list)
    # everything should be cached by now
    
    results = OrderedDict({})
    for day_in_time in dt_range(from_date, to_date):
        results[core.ymd(day_in_time)] = \
            core.article_metrics(service, table_id, from_date=day_in_time, to_date=None, cached=True) # cached=True is DELIBERATE
    return results



#
# bootstrap
#

def regenerate_results(table_id):
    "this will perform all queries again, overwriting the results in `output`"
    return daily_metrics_between(table_id, core.VIEWS_INCEPTION, datetime.now(), use_cached=False)    

def main(table_id):
    "returns all results for today"
    return daily_metrics_between(table_id, from_date=datetime.now(), to_date=None)

if __name__ == '__main__':
    pprint(dict(main(sys.argv[1])))
