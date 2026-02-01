# -*- coding: utf-8 -*-
"""
Unit-тесты для entrance_numbering_utils.py
"""

import unittest
import sys
import os

# Добавляем путь к lib для импорта модуля
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'EOMTemplateTools.extension', 'lib'))

import entrance_numbering_utils as utils


class TestExtractBSNumber(unittest.TestCase):
    """Тесты для функции extract_bs_number"""
    
    def test_simple_bs_number(self):
        """Тест извлечения простого номера БС"""
        self.assertEqual(utils.extract_bs_number(u"Внеквартирный коридор 1.234"), 1)
        self.assertEqual(utils.extract_bs_number(u"Лифтовой холл 2.112"), 2)
        self.assertEqual(utils.extract_bs_number(u"Прихожая 3.001"), 3)
    
    def test_multi_digit_bs_number(self):
        """Тест многозначных номеров БС"""
        self.assertEqual(utils.extract_bs_number(u"Коридор 10.234"), 10)
        self.assertEqual(utils.extract_bs_number(u"Помещение 15.001"), 15)
    
    def test_no_bs_number(self):
        """Тест отсутствия номера БС"""
        self.assertIsNone(utils.extract_bs_number(u"Помещение без номера"))
        self.assertIsNone(utils.extract_bs_number(u"Коридор"))
        self.assertIsNone(utils.extract_bs_number(u""))
        self.assertIsNone(utils.extract_bs_number(None))
    
    def test_with_additional_text(self):
        """Тест с дополнительным текстом в названии"""
        self.assertEqual(utils.extract_bs_number(u"Помещение общего пользования 1.234 кв"), 1)
        self.assertEqual(utils.extract_bs_number(u"2.117 Прихожая квартиры"), 2)
    
    def test_multiple_numbers(self):
        """Тест с несколькими числами - берется первое подходящее"""
        # Формат "БС.ЭТАЖ.НОМЕР" - берем первую группу
        result = utils.extract_bs_number(u"Помещение 1.234")
        self.assertEqual(result, 1)


class TestIsCorridorRoom(unittest.TestCase):
    """Тесты для функции _is_corridor_room"""
    
    def test_corridor_keywords(self):
        """Тест распознавания коридоров"""
        self.assertTrue(utils._is_corridor_room(u"Внеквартирный коридор 1.234"))
        self.assertTrue(utils._is_corridor_room(u"Лифтовой холл"))
        self.assertTrue(utils._is_corridor_room(u"Лестничная клетка"))
        self.assertTrue(utils._is_corridor_room(u"Тамбур"))
        self.assertTrue(utils._is_corridor_room(u"Вестибюль"))
        self.assertTrue(utils._is_corridor_room(u"Подъезд"))
    
    def test_not_corridor(self):
        """Тест НЕ-коридоров"""
        self.assertFalse(utils._is_corridor_room(u"Прихожая"))
        self.assertFalse(utils._is_corridor_room(u"Кухня"))
        self.assertFalse(utils._is_corridor_room(u"Спальная"))
        self.assertFalse(utils._is_corridor_room(u""))
    
    def test_case_insensitive(self):
        """Тест регистронезависимости"""
        self.assertTrue(utils._is_corridor_room(u"ВНЕКВАРТИРНЫЙ КОРИДОР"))
        self.assertTrue(utils._is_corridor_room(u"ВнЕкВаРтИрНыЙ кОрИдОр"))


class TestIsEntranceDoorType(unittest.TestCase):
    """Тесты для функции _is_entrance_door_type"""
    
    def test_entrance_door_types(self):
        """Тест входных типов дверей"""
        self.assertTrue(utils._is_entrance_door_type(
            u"103_Дверь_Витражная_Двупольная_Алюминиевая", 
            u"ДМ_Ост_Витражная_Лв"
        ))
        self.assertTrue(utils._is_entrance_door_type(
            u"100_Дверь_Стальная_Двупольная",
            u"ДМ_Гл_1360х2080_Рп"
        ))
        self.assertTrue(utils._is_entrance_door_type(
            u"Входная дверь",
            u"Стальная"
        ))
    
    def test_excluded_door_types(self):
        """Тест исключенных типов дверей"""
        self.assertFalse(utils._is_entrance_door_type(
            u"100_Дверь_Деревянная_Однопольная",
            u"ДД_Гл_810х2080_Пр"
        ))
        self.assertFalse(utils._is_entrance_door_type(
            u"Дверь квартирная",
            u"Деревянная однопольная"
        ))
    
    def test_case_insensitive(self):
        """Тест регистронезависимости"""
        self.assertTrue(utils._is_entrance_door_type(
            u"ВИТРАЖНАЯ ДВЕРЬ",
            u"ДВУПОЛЬНАЯ"
        ))


class TestGroupEntrancesByBS(unittest.TestCase):
    """Тесты для функции group_entrances_by_bs"""
    
    def test_grouping(self):
        """Тест группировки входов по БС"""
        entrances = [
            {'bs_number': 1, 'door_type': 'A', 'level_name': 'Уровень 1'},
            {'bs_number': 1, 'door_type': 'B', 'level_name': 'Уровень 2'},
            {'bs_number': 2, 'door_type': 'C', 'level_name': 'Уровень 1'},
            {'bs_number': 3, 'door_type': 'D', 'level_name': 'Уровень 1'},
            {'bs_number': 2, 'door_type': 'E', 'level_name': 'Уровень 3'},
        ]
        
        grouped = utils.group_entrances_by_bs(entrances)
        
        self.assertEqual(len(grouped), 3)  # 3 разных БС
        self.assertEqual(len(grouped[1]), 2)  # БС1 - 2 входа
        self.assertEqual(len(grouped[2]), 2)  # БС2 - 2 входа
        self.assertEqual(len(grouped[3]), 1)  # БС3 - 1 вход
    
    def test_empty_list(self):
        """Тест пустого списка"""
        grouped = utils.group_entrances_by_bs([])
        self.assertEqual(len(grouped), 0)


class TestSelectMainEntrancePerLevel(unittest.TestCase):
    """Тесты для функции select_main_entrance_per_level"""
    
    def test_one_entrance_per_level(self):
        """Тест когда на каждом уровне один вход"""
        entrances = [
            {'bs_number': 1, 'door_type': 'Витражная', 'level_name': 'Уровень 1'},
            {'bs_number': 1, 'door_type': 'Стальная', 'level_name': 'Уровень 2'},
        ]
        
        main = utils.select_main_entrance_per_level(entrances)
        self.assertEqual(len(main), 2)
    
    def test_multiple_entrances_prefer_vitrazh(self):
        """Тест выбора витражной двери при множественных входах"""
        entrances = [
            {'bs_number': 1, 'door_type': 'Стальная', 'level_name': 'Уровень 1'},
            {'bs_number': 1, 'door_type': 'Витражная двупольная', 'level_name': 'Уровень 1'},
            {'bs_number': 1, 'door_type': 'Обычная', 'level_name': 'Уровень 1'},
        ]
        
        main = utils.select_main_entrance_per_level(entrances)
        self.assertEqual(len(main), 1)
        self.assertIn(u'витраж', main[0]['door_type'].lower())
    
    def test_empty_list(self):
        """Тест пустого списка"""
        main = utils.select_main_entrance_per_level([])
        self.assertEqual(len(main), 0)


if __name__ == '__main__':
    unittest.main()
