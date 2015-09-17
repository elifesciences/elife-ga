"""Bulk loading of eLife metrics from Google Analytics."""

import os, sys, time, random, json, calendar
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
    if not to_date:
        to_date = from_date
    if from_date > to_date:
        to_date, from_date = from_date, to_date
    diff = to_date - from_date
    for increment in range(0, diff.days + 1):
        yield from_date + timedelta(days=increment)

def dt_month_range(from_date, to_date):
    # figure out a list of years and months the dates span
    ym = set()
    for dt in dt_range(from_date, to_date):
        ym.add((dt.year, dt.month))
    # for each pair, generate a month max,min datetime pair
    dt_list = []
    for year, month in sorted(ym):
        mmin, mmax = calendar.monthrange(year, month)
        print year,month,mmin,mmax
        dt_list.append((datetime(year=year, month=month, day=1), \
                        datetime(year=year, month=month, day=mmax)))
    return dt_list

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

def bulk_query(query_list):
    "executes a list of queries"
    return map(core.query_ga, query_list)

#
# daily metrics
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
# monthly metrics
#

def monthly_metrics_between(table_id, from_date, to_date, use_cached=True):
    pass

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
