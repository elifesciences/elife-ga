from base import BaseCase
from datetime import datetime, timedelta
from elife_ga_metrics import core, elife_v1, elife_v2, utils

class TestCore(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_module_picker_daily(self):
        d1 = timedelta(days=1)
        expectations = [
            # on the day, we still use v1 of the urls
            (core.SITE_SWITCH, elife_v1),
            # previous to the switchover, we used v1
            (core.SITE_SWITCH - d1, elife_v1),
            # after switchover, we use v2
            (core.SITE_SWITCH + d1, elife_v2)
        ]
        for dt, expected_module in expectations:
            self.assertEqual(expected_module, core.module_picker(dt, dt))

    def test_module_picker_monthly(self):
        d1 = timedelta(days=1)
        jan, feb, march = utils.dt_month_range_gen(
            datetime(year=2016, month=1, day=1), datetime(year=2016, month=3, day=30))
        expectations = [
            # on the day, we still use v1 of the urls
            (jan, elife_v1),
            # previous to the switchover, we used v1
            (feb, elife_v2),
            # after switchover, we use v2
            (march, elife_v2)
        ]
        for dtpair, expected_module in expectations:
            try:
                self.assertEqual(expected_module, core.module_picker(*dtpair))
            except AssertionError:
                print dtpair,expected_module
                raise
