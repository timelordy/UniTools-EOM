# -*- coding: utf-8 -*-
"""Бизнес-логика размещения щитов ШК над входными дверями квартир.

Domain Layer (чистая бизнес-логика без зависимостей от Revit API):
- Нормализация и валидация данных
- Скоринг и правила определения квартирных дверей
- Логика вариантов модулей щитов
"""

import re


# ====================================================================
# КОНСТАНТЫ DOMAIN-УРОВНЯ
# ====================================================================

# Ключевые слова для определения квартирных дверей
KEYWORDS = [u'кв', u'apartment', u'вход']
HALL_KEYWORD = u'прихож'
STEEL_FAMILY_KEYWORDS = [u'сталь', u'стал', u'стальное', u'steel']

# Определение стороны квартиры (для "inside" размещения)
APARTMENT_ROOM_KEYWORDS = [
    u'прихож', u'квартир', u'квар', u'студия',
    u'кухня-столовая', u'studio'
]
OUTSIDE_ROOM_KEYWORDS = [
    u'внекварт', u'корид', u'моп', u'лестн',
    u'тамбур', u'улиц', u'наруж', u'холл',
    u'шахт', u'подъезд'
]

# Автоматический выбор щита (эвристика по именам семейств)
PANEL_STRONG_KEYWORDS = [u'щк', u'shk', u'шк']
PANEL_APT_KEYWORDS = [u'квартир', u'apartment', u'apt']
PANEL_GENERIC_KEYWORDS = [u'щит', u'panel']
PANEL_WEAK_KEYWORDS = [u'щр', u'board']
PANEL_NEGATIVE_KEYWORDS = [u'вру', u'грщ', u'main', u'уго', u'аннотац']

# Параметры квартиры (по умолчанию)
APT_PARAM_NAMES_DEFAULT = [
    u'Квартира',
    u'Номер квартиры',
    u'ADSK_Номер квартиры',
    u'ADSK_Номер_квартиры',
    u'Apartment',
    u'Flat'
]


# ====================================================================
# НОРМАЛИЗАЦИЯ И ОЧИСТКА ДАННЫХ
# ====================================================================

def norm(s):
    """Нормализовать строку: strip + lowercase."""
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def norm_type_key(s):
    """Нормализация строк для уменьшения ошибок сопоставления (Cyrillic/Latin look-alike).

    - Нормализует дефисы (–, —, ‑, −) → '-'
    - Заменяет кириллические буквы на латинские аналоги (а→a, в→b, и т.д.)
    - Убирает лишние пробелы
    - Нормализует двоеточия (': ' → ':')
    """
    t = norm(s)
    if not t:
        return t

    # Нормализация дефисов
    try:
        for ch in (u'–', u'—', u'‑', u'−'):
            t = t.replace(ch, u'-')
    except Exception:
        pass

    # Cyrillic → Latin mapping (для похожих символов)
    try:
        repl = {
            u'а': u'a',
            u'в': u'b',
            u'е': u'e',
            u'к': u'k',
            u'м': u'm',
            u'н': u'h',
            u'о': u'o',
            u'р': u'p',
            u'с': u'c',
            u'т': u't',
            u'у': u'y',
            u'х': u'x',
        }
        for k, v in repl.items():
            t = t.replace(k, v)
    except Exception:
        pass

    # Убираем лишние пробелы
    try:
        t = u' '.join(t.split())
    except Exception:
        pass

    # Нормализуем двоеточия
    try:
        t = t.replace(u' : ', u':').replace(u' :', u':').replace(u': ', u':')
    except Exception:
        pass

    return t


def clean_apt_number(val):
    """Очистить номер квартиры от префиксов (кв., apt., квартира)."""
    if not val:
        return u''
    try:
        v = val.strip()
    except Exception:
        v = val

    # Убираем префиксы вида "кв. 123", "apt. 45"
    try:
        v = re.sub(r'^(кв\.?|apt\.?|квартира)\s*', '', v, flags=re.IGNORECASE)
    except Exception:
        pass

    try:
        return v.upper()
    except Exception:
        return v


# ====================================================================
# ВАЛИДАЦИЯ НОМЕРОВ КВАРТИР
# ====================================================================

def is_valid_apt_value(val):
    """Проверить, является ли значение валидным номером квартиры.

    Правила:
    - Не пустое
    - Не generic слова ('квартира', 'apartment', 'моп' и т.д.)
    - Должно содержать цифры
    - Цифры должны быть > 0
    """
    if not val:
        return False

    try:
        v = val.strip().lower()
    except Exception:
        v = val

    if not v:
        return False

    # Исключаем generic/placeholder значения
    if v in [u'квартира', u'apartment', u'flat', u'room', u'моп']:
        return False

    # Должно содержать цифры
    try:
        if not any(ch.isdigit() for ch in v):
            return False

        digits = u''.join([ch for ch in v if ch.isdigit()])
        if digits:
            try:
                if int(digits) <= 0:
                    return False
            except Exception:
                pass
        return True
    except Exception:
        return False


# ====================================================================
# СКОРИНГ И ЭВРИСТИКА
# ====================================================================

def has_any_keyword(text, keywords):
    """Проверить, содержит ли текст хотя бы одно из ключевых слов."""
    t = norm(text)
    for k in keywords or []:
        if norm(k) and norm(k) in t:
            return True
    return False


def score_text(text, plus=None, minus=None):
    """Подсчитать score текста на основе наличия ключевых слов.

    Args:
        text: Текст для скоринга
        plus: Список положительных ключевых слов (+1 за каждое)
        minus: Список отрицательных ключевых слов (-1 за каждое)

    Returns:
        int: Итоговый score
    """
    t = norm(text)
    score = 0

    for k in plus or []:
        kk = norm(k)
        if kk and kk in t:
            score += 1

    for k in minus or []:
        kk = norm(k)
        if kk and kk in t:
            score -= 1

    return score


def score_panel_symbol_label(label):
    """Подсчитать score для семейства щита по его label (Family: Type).

    Эвристика автовыбора щита ШК:
    - +100: Сильное совпадение (ЩК, ShK)
    - +60: Квартирные щиты (Квартирный, apartment)
    - +30: Общие щиты (Щит, panel)
    - +15: Слабые индикаторы (ЩР, board)
    - +10: EOM naming convention
    - -80: Negative keywords (ВРУ, ГРЩ, main, УГО, аннотация)
    """
    t = norm(label)
    score = 0
    if not t:
        return -999

    # Сильное предпочтение для ЩК/ShK
    if has_any_keyword(t, PANEL_STRONG_KEYWORDS):
        score += 100

    # Квартирные щиты
    if has_any_keyword(t, PANEL_APT_KEYWORDS):
        score += 60

    # Общие щиты
    if has_any_keyword(t, PANEL_GENERIC_KEYWORDS):
        score += 30

    # Слабые индикаторы (распределительные щиты)
    if has_any_keyword(t, PANEL_WEAK_KEYWORDS):
        score += 15

    # Небольшое предпочтение для EOM naming
    if 'eom' in t:
        score += 10

    # Штрафуем явно неподходящие варианты
    if has_any_keyword(t, PANEL_NEGATIVE_KEYWORDS):
        score -= 80

    return score


def score_room_apartment(room_name):
    """Подсчитать score для помещения (насколько вероятно, что это квартира).

    Args:
        room_name: Имя помещения (Room.Name)

    Returns:
        int: Score (выше = более вероятно квартира)
    """
    score = 0

    # Положительные индикаторы квартиры
    score += score_text(room_name, plus=APARTMENT_ROOM_KEYWORDS)

    # Отрицательные индикаторы (внеквартирные помещения)
    score += score_text(room_name, minus=OUTSIDE_ROOM_KEYWORDS)

    return score


# ====================================================================
# ЛОГИКА ВАРИАНТОВ МОДУЛЕЙ ЩИТОВ
# ====================================================================

def variant_prefix_key(variant_param_name):
    """Извлечь prefix ключ из имени параметра варианта модуля.

    Примеры:
        'ЩРВ-П-18 модулей' → 'щрв-п-'
        'ShK-12' → 'shk-'

    Используется для группировки связанных вариантов модулей.
    """
    n = norm_type_key(variant_param_name)
    if not n:
        return None

    # Ищем паттерн: <prefix>-<digits>
    try:
        m = re.match(u'^(.*?)-\\s*\\d+\\b', n)
    except Exception:
        m = None

    if not m:
        return None

    try:
        base = (m.group(1) or u'').strip()
    except Exception:
        base = u''

    if not base:
        return None

    return norm_type_key(base + u'-')


def is_panel_module_variant_param_name(pname):
    """Эвристика: определить, является ли имя параметра вариантом модуля щита.

    Некоторые семейства щитов имеют несколько серий (например, ЩРВ-П-* и ЩРВ-П-П-*)
    как отдельные Yes/No параметры, и несколько из них могут быть ON одновременно.

    Мы считаем параметром варианта любой параметр, который:
    - Упоминает модули ('модул', 'module', 'modul')
    - Содержит число

    Args:
        pname: Имя параметра

    Returns:
        bool: True если это параметр варианта модуля
    """
    n = norm(pname)
    if not n:
        return False

    # Проверяем упоминание модулей
    try:
        has_modul = re.search(u'(модул|module|modul)', n, flags=re.IGNORECASE) is not None
    except Exception:
        has_modul = (u'модул' in n) or ('module' in n) or ('modul' in n)

    if not has_modul:
        return False

    # Проверяем наличие числа
    try:
        has_num = re.search(u'\\d+', n) is not None
    except Exception:
        has_num = any(ch.isdigit() for ch in n)

    return bool(has_modul and has_num)


def make_variant_type_name(base_type_name, desired_param_name):
    """Сгенерировать имя нового типа для варианта модуля.

    Args:
        base_type_name: Базовое имя типа (например, 'Щит ШК')
        desired_param_name: Имя параметра варианта (например, 'ЩРВ-П-18 модулей')

    Returns:
        str: Новое имя типа (например, 'Щит ШК-18' или 'Щит ШК (VAR)')
    """
    if not base_type_name:
        base_type_name = u'Panel'

    # Пытаемся извлечь число из имени параметра
    num = None
    try:
        m = re.search(u'-(\\d+)\\b', (desired_param_name or u''))
        if m:
            num = m.group(1)
    except Exception:
        num = None

    if num:
        name = u'{0}-{1}'.format(base_type_name, num)
    else:
        name = u'{0} (VAR)'.format(base_type_name)

    return name
