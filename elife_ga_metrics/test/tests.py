from datetime import datetime
import unittest
from elife_ga_metrics import core

class BaseCase(unittest.TestCase):
    pass

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
