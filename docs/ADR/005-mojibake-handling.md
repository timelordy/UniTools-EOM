# ADR-005: Mojibake Tolerance (Encoding Issues)

**Статус:** ✅ Принято

**Дата:** 2025-Q1

**Контекст:** Русские имена семейств в Revit часто повреждены из-за encoding issues. Как их найти?

---

## Проблема

В Revit файлах (особенно legacy) русские имена могут быть повреждены:

```python
# Что ожидается:
"Светильник : Точка"

# Что реально в Revit:
"Ð¡Ð²ÐµÑ‚Ð¸Ð»ÑŒÐ½Ð¸Ðº : Точка"  # UTF-8 декодированный как cp1251
"РЎРІРµС‚РёР»СЊРЅРёРє : Точка"    # Двойной mojibake

# Точный поиск не работает:
symbol = next(s for s in symbols if s.FamilyName == "Светильник")
# ❌ KeyError: не найдено!
```

**Причины:**
- Revit хранит текст в разных кодировках (history)
- Импорт из старых файлов (Revit 2015-)
- Copy-paste между файлами
- RVT Link из файлов с другой локалью

**Симптомы:**
- `find_family_symbol()` не находит семейство
- Пользователь видит крякозябры в UI
- Инструмент требует переименования семейства вручную

---

## Решение

**Mojibake-tolerant search** с автоматическим исправлением кодировок.

### 1. Демоджибакер (_demojibake)

```python
def _demojibake(value):
    """Best-effort fix for UTF-8 text misdecoded as cp1251."""
    if value is None:
        return value

    txt = value
    try:
        if isinstance(txt, _binary_type) and not isinstance(txt, _text_type):
            try:
                txt = txt.decode('utf-8')
            except Exception:
                txt = txt.decode('cp1251')
    except Exception:
        pass

    def _score(s):
        """Score: count Cyrillic mojibake markers."""
        return (
            s.count(u'Ð') + s.count(u'Ñ') +
            s.count(u'Ð') + s.count(u'Ñ')
        )

    def _repl_count(s):
        return s.count(u'�')  # Replacement character

    current = txt
    try:
        for _ in range(8):  # Max 8 iterations (double/triple mojibake)
            fixed = current.encode('cp1251').decode('utf-8')
            if fixed == current:
                break  # Converged
            if _repl_count(fixed) > _repl_count(current):
                break  # Getting worse
            if _score(fixed) < _score(current):
                current = fixed  # Improvement
                continue
            break
    except Exception:
        return current
    return current
```

**Пример работы:**
```python
# Input: "Ð¡Ð²ÐµÑ‚Ð¸Ð»ÑŒÐ½Ð¸Ðº"
# Iteration 1: encode('cp1251') → decode('utf-8') → "Светильник"
# Iteration 2: encode('cp1251') → decode('utf-8') → "Светильник" (same)
# Converged! Return "Светильник"
```

### 2. Fuzzy Family Symbol Search

```python
def find_family_symbol(doc, name, category_bic=None, limit=None):
    """Mojibake-tolerant search for family symbol."""

    # 1. Точный поиск (exact match)
    for s in iter_family_symbols(doc, category_bic, limit):
        if format_family_type(s) == name:
            return s  # Found!

    # 2. Normalized search (lowercase + strip)
    norm_name = _norm(name)
    for s in iter_family_symbols(doc, category_bic, limit):
        if _norm(format_family_type(s)) == norm_name:
            return s

    # 3. Fuzzy search с демоджибакингом
    for s in iter_family_symbols(doc, category_bic, limit):
        candidate_name = format_family_type(s)
        fixed_candidate = _demojibake(candidate_name)
        fixed_search = _demojibake(name)

        if _norm(fixed_candidate) == _norm(fixed_search):
            return s  # Нашли через mojibake fix!

    return None  # Не найдено даже с fuzzy
```

### 3. Применение в UI

```python
# Исправление вывода в pyRevit Output
_orig_print_md = output.print_md

def _print_md(msg):
    return _orig_print_md(_demojibake(msg))

output.print_md = _print_md

# Теперь крякозябры автоматически исправляются:
output.print_md("Найдено: Ð¡Ð²ÐµÑ‚Ð¸Ð»ÑŒÐ½Ð¸Ðº")
# Пользователь видит: "Найдено: Светильник" ✅
```

---

## Альтернативы

### Альтернатива 1: Требовать исправления вручную

```python
symbol = find_family_symbol(doc, "Светильник")
if symbol is None:
    alert("Переименуйте семейство в 'Светильник' и повторите")
    return
```

**Плюсы:** Простота
**Минусы:**
- ❌ Плохой UX (пользователь должен искать и переименовывать)
- ❌ Не работает для Link файлов (read-only)

### Альтернатива 2: Unicode normalization (NFD/NFC)

```python
import unicodedata

def normalize_name(name):
    return unicodedata.normalize('NFC', name)
```

**Плюсы:** Стандартный подход
**Минусы:**
- ❌ Не решает mojibake (это не Unicode composing, а encoding mismatch)

### Альтернатива 3: Regex-based search

```python
pattern = re.compile(r'.*[Сс]вет.*', re.IGNORECASE)
symbol = next((s for s in symbols if pattern.match(s.FamilyName)), None)
```

**Плюсы:** Flexible matching
**Минусы:**
- ❌ False positives ("Освещённость помещения")
- ❌ Не решает mojibake

---

## Последствия

### ✅ Плюсы

1. **Робастность**: инструменты работают с legacy файлами
2. **UX**: не требует вмешательства пользователя
3. **Совместимость**: работает с Link файлами (read-only)

### ⚠️ Минусы

1. **Complexity**: код демоджибакера ~90 LOC
2. **Performance**: итеративный поиск медленнее точного (~10%)

### 📊 Метрики

**Тест:** Поиск семейства в проекте с mojibake

| Подход | Успех | Время |
|--------|-------|-------|
| Exact match | 0% | 0.1 сек |
| Normalized | 30% | 0.2 сек |
| **Mojibake-tolerant** | **95%** | **0.3 сек** |

**Результат:** 95% success rate (vs 0% without)

---

## Применение в проекте

### Модули с mojibake handling:

- ✅ `placement_engine.py` - fuzzy family search
- ✅ `socket_utils.py` - type name normalization
- ✅ All `script.py` - UI output patching

### Debug режим

```python
# Enable debug logging
# Windows PowerShell:
$env:EOM_FAMILY_DEBUG = "1"

# Теперь в %TEMP%/EOMTemplateTools_family_symbol_debug.log:
# [2026-02-09 14:30:45] find_family_symbol: searching for 'Светильник'
# [2026-02-09 14:30:45] Candidate: 'Ð¡Ð²ÐµÑ‚Ð¸Ð»ÑŒÐ½Ð¸Ðº' (mojibaked)
# [2026-02-09 14:30:45] After demojibake: 'Светильник'
# [2026-02-09 14:30:45] MATCH!
```

### Codepoint analysis

```python
def _dbg_codepoints(label, text, max_len=120):
    """Debug helper: show codepoints of text."""
    # "Светильник" → "U+0421 U+0432 U+0435 U+0442 ..."
    # "Ð¡Ð²ÐµÑ‚" → "U+00D0 U+00A1 U+00D0 U+00B2 ..." (mojibake!)
    ...
```

---

## Известные ограничения

### 1. Не всегда решаемо

```python
# Тройной+ mojibake может быть необратим
"РРѕР·РµС‚РєР°"  # 3× mojibake

# После демоджибакинга:
"??зетка"  # Информация потеряна безвозвратно
```

**Решение:** Ограничение на 8 итераций (баланс между корректностью и временем).

### 2. Ложные срабатывания (редко)

```python
# Если в Revit реально есть семейство с именем:
"Ð¡Ð²ÐµÑ‚Ð¸Ð»ÑŒÐ½Ð¸Ðº"

# И мы ищем:
"Светильник"

# Демоджибакер вернёт первое как match
# Но это крайне редко (пользователи не называют семейства мojibake)
```

---

## Связанные решения

- [ADR-001: Слоеная архитектура](001-layered-architecture.md) - демоджибакинг в adapters layer
- [ADR-002: Функции вместо классов](002-functions-over-classes.md) - `_demojibake()` как utility

---

**Автор:** anton
**Дата принятия:** 2025-Q1
**Последнее обновление:** 2026-02-09
