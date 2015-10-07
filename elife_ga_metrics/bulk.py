"""Bulk loading of eLife metrics from Google Analytics."""

import os, sys, time, random, json, calendar
import core
from core import ymd
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
        dt = from_date + timedelta(days=increment)
        yield (dt, dt)  # daily

def dt_month_range(from_date, to_date):
    # figure out a list of years and months the dates span
    ym = set()
    for dt1, dt2 in dt_range(from_date, to_date):
        ym.add((dt1.year, dt1.month))
    # for each pair, generate a month max,min datetime pair
    for year, month in sorted(ym):
        mmin, mmax = calendar.monthrange(year, month)
        yield (datetime(year=year, month=month, day=1), \
               datetime(year=year, month=month, day=mmax))

def generate_queries(table_id, query_func, datetime_list, use_cached=False, use_only_cached=False):
    "returns a list of queries to be executed by google"
    query_list = []
    query_type = 'views' if query_func == core.path_counts_query else 'downloads'
    for start_date, end_date in datetime_list:
        output_path = core.output_path(query_type, start_date, end_date)
        if use_cached:
            if os.path.exists(output_path):
                LOG.debug("we have %r results for %r to %r already", query_type, ymd(start_date), ymd(end_date))
                continue
            else:
                LOG.info("no cache file for %r results for %r to %r", query_type, ymd(start_date), ymd(end_date))
        else:
            LOG.debug("couldn't find file %r", output_path)
        
        if use_only_cached:
            LOG.info("skipping google query, using only cache files")
            continue
        
        q = query_func(table_id, start_date, end_date)
        query_list.append(q)

    if use_only_cached:
        assert query_list == [], "code problem. use_only_cached=True but we're accumulating queries somehow"
        
    return query_list

def bulk_query(query_list):
    "executes a list of queries"
    return map(core.query_ga, query_list)

#
# daily metrics
#

def metrics_for_range(table_id, dt_range_list, use_cached=False, use_only_cached=False):
    # tell core to do it's data wrangling for us (using cached data)
    results = OrderedDict({})
    for from_date, to_date in dt_range_list:
        res = core.article_metrics(table_id, from_date, to_date, use_cached, use_only_cached)
        results[(ymd(from_date), ymd(to_date))] = res
    return results

def daily_metrics_between(table_id, from_date, to_date, use_cached=True, use_only_cached=False):
    "does a DAILY query between two dates, NOT a single query within a date range"
    date_list = dt_range(from_date, to_date)
    views_dt_range = filter(core.valid_view_dt_pair, date_list)
    pdf_dt_range = filter(core.valid_downloads_dt_pair, date_list)

    # ensure our raw data exists on disk
    query_list = []
    query_list.extend(generate_queries(table_id, \
                                       core.path_counts_query, \
                                       views_dt_range, \
                                       use_cached, use_only_cached))
    
    query_list.extend(generate_queries(table_id, \
                                       core.event_counts_query, \
                                       pdf_dt_range,
                                       use_cached, use_only_cached))
    
    bulk_query(query_list)
    
    # everything should be cached by now
    use_cached = True # DELIBERATE here. the above 
    return metrics_for_range(table_id, views_dt_range, use_cached, use_only_cached)

#
# monthly metrics
#

def monthly_metrics_between(table_id, from_date, to_date, use_cached=True, use_only_cached=False):
    date_list = dt_month_range(from_date, to_date)
    views_dt_range = filter(core.valid_view_dt_pair, date_list)
    pdf_dt_range = filter(core.valid_downloads_dt_pair, date_list)
    
    query_list = []
    query_list.extend(generate_queries(table_id, \
                                       core.path_counts_query, \
                                       views_dt_range,
                                       use_cached, use_only_cached))
    
    query_list.extend(generate_queries(table_id, \
                                       core.event_counts_query, \
                                       pdf_dt_range,
                                       use_cached, use_only_cached))
    bulk_query(query_list)
    
    # everything should be cached by now
    use_cached = True # DELIBERATE
    return metrics_for_range(table_id, views_dt_range, use_cached, use_only_cached)

#
#
#

def fill_gaps():
    """goes through all files we have output and looks for 'gaps' and then creates a query that will fill it. NOT a replacement for regenerate_results """

#
# bootstrap
#

def regenerate_results(table_id):
    "this will perform all queries again, overwriting the results in `output`"
    today = datetime.now()
    use_cached, use_only_cached = False, False
    LOG.info("querying daily metrics ...")
    daily_metrics_between(table_id, \
                          core.VIEWS_INCEPTION, \
                          today, \
                          use_cached, use_only_cached)    

    LOG.info("querying monthly metrics ...")
    monthly_metrics_between(table_id, \
                            core.DOWNLOADS_INCEPTION, \
                            today, \
                            use_cached, use_only_cached)


def main(table_id):
    "returns daily results for the last week, monthly results for the current month"
    from_date = datetime.now() - timedelta(days=7)
    to_date = datetime.now()
    use_cached, use_only_cached = True, not os.path.exists('client-secrets.json')
    
    print daily_metrics_between(table_id, \
                                from_date, \
                                to_date, \
                                use_cached, use_only_cached)

    print monthly_metrics_between(table_id, \
                                  to_date, \
                                  to_date, \
                                  use_cached, use_only_cached)

if __name__ == '__main__':
    main(sys.argv[1])
