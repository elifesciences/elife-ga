from datetime import datetime
import unittest
from elife_ga_metrics import core, bulk

class BaseCase(unittest.TestCase):
    maxDiff = None

class TestUtils(BaseCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ymd(self):
        dt = datetime(year=1997, month=8, day=29, hour=6, minute=14) # UTC ;)
        self.assertEqual(core.ymd(dt), "1997-08-29")

    def test_enplumpen(self):
        self.assertEqual("10.7554/eLife.01234", core.enplumpen("e01234"))

    def test_month_range(self):
        expected_output = [
            (datetime(year=2014, month=12, day=1), datetime(year=2014, month=12, day=31)),
            (datetime(year=2015, month=1, day=1), datetime(year=2015, month=1, day=31)),
            (datetime(year=2015, month=2, day=1), datetime(year=2015, month=2, day=28)),
            (datetime(year=2015, month=3, day=1), datetime(year=2015, month=3, day=31)),
        ]
        start_dt = datetime(year=2014, month=12, day=15)
        end_dt = datetime(year=2015, month=3, day=12)
        self.assertEqual(expected_output, bulk.dt_month_range(start_dt, end_dt))
