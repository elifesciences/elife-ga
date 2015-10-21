import calendar, collections, functools
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

def firstof(fn, x):
    for i in x:
        if fn(i):
            return i

# stolen from: https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
class memoized(object):
    '''Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    '''
    def __init__(self, func):
        self.func = func
        self.cache = {}
    def __call__(self, *args):
        if not isinstance(args, collections.Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args)
        
        if args in self.cache:
            return self.cache[args]
        else:
            value = self.func(*args)
            self.cache[args] = value
            return value
        
    def __repr__(self):
        '''Return the function's docstring.'''
        return self.func.__doc__
    
    def __get__(self, obj, objtype):
        '''Support instance methods.'''
        return functools.partial(self.__call__, obj)
