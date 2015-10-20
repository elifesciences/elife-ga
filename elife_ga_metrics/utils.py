import calendar
from datetime import datetime, date, timedelta
import logging

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.level = logging.INFO

def ymd(dt):
    "returns a yyyy-mm-dd version of the given datetime object"
    return dt.strftime("%Y-%m-%d")

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
