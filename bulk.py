"""
Bulk loading of eLife metrics from Google Analytics.

"""

import sys
import mains
from datetime import datetime, timedelta
from apiclient.http import BatchHttpRequest
import logging

logging.basicConfig()
LOG = logging.getLogger(__name__)

# not really, we just switched to a different GA profile on this date
INCEPTION = datetime(year=2014, month=03, day=01)
GA_HARD_LIMIT = 1000

def dt_range(from_date, to_date):
    """returns a series of datetime objects starting at from_date
    and ending on to_date includsive."""
    if from_date > to_date:
        to_date, from_date = from_date, to_date
    diff = to_date - from_date
    for increment in range(0, diff.days + 1):
        yield from_date + timedelta(days=increment)

def partition_query_list(query_list, partition_at=1000):
    "GA will only handle 1000 per batch, so we need to split them up if query_list > 1000"
    partitions = []
    while True:
        if len(query_list) == 0:
            break
        partitions.append(query_list[:partition_at])
        query_list = query_list[partition_at:]
    return partitions

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

def bulk_query(query_list):
    for i, ql_partition in enumerate(partition_query_list(query_list)):
        batch = BatchHttpRequest(callback=write_results_callback)
        map(batch.add, ql_partition)
        print 'executing batch',i+1
        batch.execute()


#
# bootstrap
#

def main(table_id):
    service = mains.ga_service(table_id)
    query_list = generate_queries(service, table_id, mains.path_counts_query)
    bulk_query(query_list)

if __name__ == '__main__':
    main(sys.argv[1])
