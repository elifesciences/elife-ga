"""
Bulk loading of eLife metrics from Google Analytics.

"""

import sys, time, random, json
import mains
from datetime import datetime, timedelta
from apiclient.http import BatchHttpRequest
from apiclient import errors
from pprint import pprint
import logging

logging.basicConfig()
LOG = logging.getLogger(__name__)

# not really, we just switched to a different GA profile on this date
INCEPTION = datetime(year=2014, month=03, day=12)
GA_HARD_LIMIT = 1000

def dt_range(from_date, to_date):
    """returns a series of datetime objects starting at from_date
    and ending on to_date includsive."""
    if from_date > to_date:
        to_date, from_date = from_date, to_date
    diff = to_date - from_date
    for increment in range(0, diff.days + 1):
        yield from_date + timedelta(days=increment)

"""
# WORKS, BUT IS RATE-LIMITED ALMOST IMMEDIATELY.
def partition_query_list(query_list, partition_at=1000):
    "GA will only handle 1000 per batch, so we need to split them up if query_list > 1000"
    partitions = []
    while True:
        if len(query_list) == 0:
            break
        partitions.append(query_list[:partition_at])
        query_list = query_list[partition_at:]
    return partitions

def bulk_query(query_list):
    for i, ql_partition in enumerate(partition_query_list(query_list)):
        batch = BatchHttpRequest(callback=write_results_callback)
        map(batch.add, ql_partition)
        print 'executing batch',i+1
        batch.execute()


def write_results_callback(request_id, response, exception):
    if exception:
        LOG.error("callback with id %r received an exception %r", request_id, exception)
    else:
        query = response['query']
        from_date = datetime.strptime(query['start-date'], "%Y-%m-%d")
        to_date = datetime.strptime(query['end-date'], "%Y-%m-%d")
        results_type = 'downloads' if 'ga:eventLabel' in query['filters'] else 'views'
        path = mains.output_path(results_type, from_date, to_date)
        mains.write_results(response, path)


"""


def generate_queries(service, table_id, query_func, from_date=None, to_date=None):
    if not from_date:
        from_date = INCEPTION
    if not to_date:
        to_date = datetime.now()    
    query_list = []
    for date_in_time in dt_range(from_date, to_date):
        q = query_func(service, table_id, date_in_time, date_in_time)
        query_list.append(q)
    return query_list

def exec_query(query):
    num_attempts = 5
    for n in range(0, num_attempts):
        try:
            LOG.info("query attempt %r" % n)
            response = query.execute()
            query = response['query']
            from_date = datetime.strptime(query['start-date'], "%Y-%m-%d")
            to_date = datetime.strptime(query['end-date'], "%Y-%m-%d")
            results_type = 'downloads' if 'ga:eventLabel' in query['filters'] else 'views'
            path = mains.output_path(results_type, from_date, to_date)
            mains.write_results(response, path)
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
    return map(exec_query, query_list)

#
# bootstrap
#

def main(table_id):
    service = mains.ga_service(table_id)
    query_list = []
    query_list.extend(generate_queries(service, table_id, mains.path_counts_query))
    query_list.extend(generate_queries(service, table_id, mains.event_counts_query))
    
    return bulk_query(query_list)

if __name__ == '__main__':
    pprint(main(sys.argv[1]))
