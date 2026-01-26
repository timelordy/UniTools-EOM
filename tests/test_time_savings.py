# -*- coding: utf-8 -*-

import os
import sys
import unittest


# Add EOMTemplateTools.extension/lib to sys.path for import
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'EOMTemplateTools.extension', 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)


import time_savings  # noqa: E402


class TestTimeSavings(unittest.TestCase):
    def setUp(self):
        # Clear session counts before each test
        time_savings._session_counts.clear()

    def test_set_and_get_element_count(self):
        time_savings.set_element_count('sockets_general', 100)
        self.assertEqual(time_savings.get_element_count('sockets_general'), 100)

    def test_get_element_count_unknown(self):
        self.assertEqual(time_savings.get_element_count('unknown_tool'), 0)

    def test_calculate_time_saved(self):
        # sockets_general has 0.5 min per socket
        result = time_savings.calculate_time_saved('sockets_general', 100)
        self.assertEqual(result, 50.0)  # 100 * 0.5 = 50 minutes

    def test_calculate_time_saved_zero(self):
        result = time_savings.calculate_time_saved('sockets_general', 0)
        self.assertEqual(result, 0)

    def test_format_time_saved_minutes(self):
        # 512 sockets * 0.5 = 256 minutes
        result = time_savings.format_time_saved('sockets_general', 512)
        self.assertIn(u'час', result)  # Should be in hours

    def test_format_time_saved_few_minutes(self):
        # 10 sockets * 0.5 = 5 minutes
        result = time_savings.format_time_saved('sockets_general', 10)
        self.assertEqual(result, u'~5 минут')

    def test_format_time_saved_one_minute(self):
        # 2 sockets * 0.5 = 1 minute
        result = time_savings.format_time_saved('sockets_general', 2)
        self.assertEqual(result, u'~1 минута')

    def test_format_time_saved_less_than_minute(self):
        # 1 socket * 0.5 = 0.5 minutes
        result = time_savings.format_time_saved('sockets_general', 1)
        self.assertEqual(result, u'меньше минуты')

    def test_format_time_saved_zero(self):
        result = time_savings.format_time_saved('sockets_general', 0)
        self.assertIsNone(result)


class TestMockOutput:
    """Mock output object for testing report function."""
    def __init__(self):
        self.messages = []
    
    def print_md(self, msg):
        self.messages.append(msg)


class TestTimeSavingsReport(unittest.TestCase):
    def setUp(self):
        time_savings._session_counts.clear()

    def test_report_with_count(self):
        output = TestMockOutput()
        result = time_savings.report(output, 'sockets_general', 512)
        self.assertTrue(result)
        self.assertEqual(len(output.messages), 1)
        self.assertIn(u'Сэкономлено времени', output.messages[0])
        self.assertIn('512', output.messages[0])

    def test_report_zero_count(self):
        output = TestMockOutput()
        result = time_savings.report(output, 'sockets_general', 0)
        self.assertFalse(result)
        self.assertEqual(len(output.messages), 0)


if __name__ == '__main__':
    unittest.main()
