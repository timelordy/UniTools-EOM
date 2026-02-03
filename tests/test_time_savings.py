# -*- coding: utf-8 -*-

import os
import sys
import unittest
import tempfile
import shutil


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
        time_savings.set_element_count('switches', 100)
        self.assertEqual(time_savings.get_element_count('switches'), 100)
        self.assertEqual(time_savings.get_element_count('switches_doors'), 100)

    def test_get_element_count_unknown(self):
        self.assertEqual(time_savings.get_element_count('unknown_tool'), 0)

    def test_calculate_time_saved(self):
        # lights_center: 1–3 min per unit => avg 2 min
        result = time_savings.calculate_time_saved('lights_center', 10)
        self.assertEqual(result, 20.0)

    def test_calculate_time_saved_range(self):
        result_min, result_max = time_savings.calculate_time_saved_range('lights_center', 10)
        self.assertEqual(result_min, 10.0)
        self.assertEqual(result_max, 30.0)

    def test_calculate_time_saved_zero(self):
        result = time_savings.calculate_time_saved('lights_center', 0)
        self.assertEqual(result, 0)

    def test_format_time_saved_minutes(self):
        # lights_center: avg 2 min => 120 units => 240 minutes
        result = time_savings.format_time_saved('lights_center', 120)
        self.assertIn(u'час', result)  # Should be in hours

    def test_format_time_saved_few_minutes(self):
        # lights_center: avg 2 min => 2 units => 4 minutes
        result = time_savings.format_time_saved('lights_center', 2)
        self.assertEqual(result, u'~4 минуты')

    def test_format_time_saved_one_minute(self):
        # Unknown tool uses default 0.5 min per unit => 2 units => 1 minute
        result = time_savings.format_time_saved('unknown_tool', 2)
        self.assertEqual(result, u'~1 минута')

    def test_format_time_saved_less_than_minute(self):
        # Unknown tool uses default 0.5 min per unit => 1 unit => 0.5 minutes
        result = time_savings.format_time_saved('unknown_tool', 1)
        self.assertEqual(result, u'меньше минуты')

    def test_format_time_saved_zero(self):
        result = time_savings.format_time_saved('unknown_tool', 0)
        self.assertIsNone(result)

    def test_persists_count_to_temp_file(self):
        temp_dir = tempfile.mkdtemp()
        old_temp = os.environ.get('TEMP')
        old_tmp = os.environ.get('TMP')
        old_session = os.environ.get('EOM_SESSION_ID')
        try:
            os.environ['TEMP'] = temp_dir
            os.environ['TMP'] = temp_dir
            time_savings._session_counts.clear()
            time_savings.set_element_count('lights_center', 31)
            time_savings._session_counts.clear()
            self.assertEqual(time_savings.get_element_count('lights_center'), 31)
        finally:
            if old_session is None:
                os.environ.pop('EOM_SESSION_ID', None)
            else:
                os.environ['EOM_SESSION_ID'] = old_session
            if old_temp is None:
                os.environ.pop('TEMP', None)
            else:
                os.environ['TEMP'] = old_temp
            if old_tmp is None:
                os.environ.pop('TMP', None)
            else:
                os.environ['TMP'] = old_tmp
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_session_id_fallback_to_generic_counts_file(self):
        temp_dir = tempfile.mkdtemp()
        old_temp = os.environ.get('TEMP')
        old_tmp = os.environ.get('TMP')
        old_session = os.environ.get('EOM_SESSION_ID')
        try:
            os.environ['TEMP'] = temp_dir
            os.environ['TMP'] = temp_dir
            os.environ['EOM_SESSION_ID'] = 'session-test'
            time_savings._session_counts.clear()
            generic_path = os.path.join(temp_dir, 'eom_time_savings_counts.json')
            with open(generic_path, 'w', encoding='utf-8') as f:
                f.write('{"lights_center": 31}')
            self.assertEqual(time_savings.get_element_count('lights_center'), 31)
        finally:
            if old_session is None:
                os.environ.pop('EOM_SESSION_ID', None)
            else:
                os.environ['EOM_SESSION_ID'] = old_session
            if old_temp is None:
                os.environ.pop('TEMP', None)
            else:
                os.environ['TEMP'] = old_temp
            if old_tmp is None:
                os.environ.pop('TMP', None)
            else:
                os.environ['TMP'] = old_tmp
            shutil.rmtree(temp_dir, ignore_errors=True)


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
        result = time_savings.report(output, 'lights_center', 10)
        self.assertTrue(result)
        self.assertEqual(len(output.messages), 1)
        self.assertIn(u'Сэкономлено времени', output.messages[0])
        self.assertIn(u'диапазон', output.messages[0])
        self.assertIn('10', output.messages[0])

    def test_report_zero_count(self):
        output = TestMockOutput()
        result = time_savings.report(output, 'sockets_general', 0)
        self.assertFalse(result)
        self.assertEqual(len(output.messages), 0)

    def test_report_writes_log_entry(self):
        temp_dir = tempfile.mkdtemp()
        old_temp = os.environ.get('TEMP')
        old_tmp = os.environ.get('TMP')
        old_session = os.environ.get('EOM_SESSION_ID')
        old_override = os.environ.get('EOM_LIFT_SHAFT_COUNT_OVERRIDE')
        try:
            os.environ['TEMP'] = temp_dir
            os.environ['TMP'] = temp_dir
            os.environ['EOM_SESSION_ID'] = 'session-test'
            output = TestMockOutput()
            result = time_savings.report(output, 'lights_center', 3)
            self.assertTrue(result)
            entry = time_savings.get_last_time_saved_entry('lights_center')
            self.assertIsNotNone(entry)
            self.assertEqual(entry.get('tool_key'), 'lights_center')
            self.assertEqual(entry.get('count'), 3)
            self.assertEqual(entry.get('minutes'), time_savings.calculate_time_saved('lights_center', 3))
        finally:
            if old_session is None:
                os.environ.pop('EOM_SESSION_ID', None)
            else:
                os.environ['EOM_SESSION_ID'] = old_session
            if old_override is None:
                os.environ.pop('EOM_LIFT_SHAFT_COUNT_OVERRIDE', None)
            else:
                os.environ['EOM_LIFT_SHAFT_COUNT_OVERRIDE'] = old_override
            if old_temp is None:
                os.environ.pop('TEMP', None)
            else:
                os.environ['TEMP'] = old_temp
            if old_tmp is None:
                os.environ.pop('TMP', None)
            else:
                os.environ['TMP'] = old_tmp
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_lights_elevator_override_count(self):
        temp_dir = tempfile.mkdtemp()
        old_temp = os.environ.get('TEMP')
        old_tmp = os.environ.get('TMP')
        old_override = os.environ.get('EOM_LIFT_SHAFT_COUNT_OVERRIDE')
        try:
            os.environ['TEMP'] = temp_dir
            os.environ['TMP'] = temp_dir
            os.environ['EOM_LIFT_SHAFT_COUNT_OVERRIDE'] = '2'
            time_savings._session_counts.clear()
            minutes = time_savings.calculate_time_saved('lights_elevator', 26)
            self.assertEqual(minutes, 20.0)
            output = TestMockOutput()
            result = time_savings.report(output, 'lights_elevator', 26)
            self.assertTrue(result)
            entry = time_savings.get_last_time_saved_entry('lights_elevator')
            self.assertIsNotNone(entry)
            self.assertEqual(entry.get('count'), 2)
        finally:
            if old_override is None:
                os.environ.pop('EOM_LIFT_SHAFT_COUNT_OVERRIDE', None)
            else:
                os.environ['EOM_LIFT_SHAFT_COUNT_OVERRIDE'] = old_override
            if old_temp is None:
                os.environ.pop('TEMP', None)
            else:
                os.environ['TEMP'] = old_temp
            if old_tmp is None:
                os.environ.pop('TMP', None)
            else:
                os.environ['TMP'] = old_tmp
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cluster_xy_points_two_clusters(self):
        points = [(0.0, 0.0), (0.4, 0.3), (10.0, 10.0), (10.2, 9.8)]
        count = time_savings._cluster_xy_points(points, 1.0)
        self.assertEqual(count, 2)

    def test_room_override_for_sockets_general(self):
        old_override = os.environ.get('EOM_ROOM_COUNT_OVERRIDE_SOCKETS_GENERAL')
        try:
            os.environ['EOM_ROOM_COUNT_OVERRIDE_SOCKETS_GENERAL'] = '3'
            minutes = time_savings.calculate_time_saved('sockets_general', 100)
            self.assertEqual(minutes, 18.0)
        finally:
            if old_override is None:
                os.environ.pop('EOM_ROOM_COUNT_OVERRIDE_SOCKETS_GENERAL', None)
            else:
                os.environ['EOM_ROOM_COUNT_OVERRIDE_SOCKETS_GENERAL'] = old_override

    def test_room_override_for_ac_sockets(self):
        old_override = os.environ.get('EOM_ROOM_COUNT_OVERRIDE_AC_SOCKETS')
        try:
            os.environ['EOM_ROOM_COUNT_OVERRIDE_AC_SOCKETS'] = '2'
            minutes = time_savings.calculate_time_saved('ac_sockets', 50)
            self.assertEqual(minutes, 4.0)
        finally:
            if old_override is None:
                os.environ.pop('EOM_ROOM_COUNT_OVERRIDE_AC_SOCKETS', None)
            else:
                os.environ['EOM_ROOM_COUNT_OVERRIDE_AC_SOCKETS'] = old_override

    def test_make_room_key(self):
        self.assertEqual(time_savings._make_room_key(None, 12), 'H:12')
        self.assertEqual(time_savings._make_room_key(7, 34), 'L7:34')


if __name__ == '__main__':
    unittest.main()
