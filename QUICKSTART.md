# EOMTemplateTools - Quick Start Guide

## 🚀 Для новых разработчиков

### За 5 минут поймёте структуру проекта

---

## 📂 Что где находится?

```
EOMTemplateTools/
├── ARCHITECTURE.md              ← Подробная архитектура (читай первым!)
├── QUICKSTART.md                ← Этот файл (quick reference)
├── pyproject.toml               ← Dev зависимости
│
├── EOMTemplateTools.extension/
│   ├── EOM.tab/                 ← Основные инструменты для пользователей
│   │   ├── 02_Освещение.panel/
│   │   │   └── СветВЛифтах.pushbutton/  ← Пример хорошо структурированного инструмента
│   │   ├── 03_ЩитыВыключатели.panel/
│   │   └── 04_Розетки.panel/
│   │
│   ├── lib/                     ← Переиспользуемый код (импортируй отсюда!)
│   │   ├── placement_engine.py  ← Размещение элементов
│   │   ├── socket_utils.py      ← Розетки, spatial index
│   │   ├── config_loader.py     ← Загрузка конфигов
│   │   └── utils_revit.py       ← Транзакции, error handling
│   │
│   └── config/
│       └── rules.default.json   ← Все настройки инструментов
│
└── tests/                       ← Тесты (pytest)
    └── conftest.py              ← Моки Revit API
```

---

## 🎯 Типичные задачи

### 1. Создать новый инструмент

```bash
# Структура:
EOM.tab/ВашаПанель.panel/ВашИнструмент.pushbutton/
├── domain.py         # Чистая логика (без Revit API)
├── adapters.py       # Работа с Revit API
├── orchestrator.py   # Координация workflow
└── script.py         # Entry point (<50 LOC)
```

**Шаблон script.py:**
```python
from pyrevit import revit, script
from utils_revit import alert, log_exception
import orchestrator

try:
    doc = revit.doc
    output = script.get_output()
    result = orchestrator.run_placement(doc, output, script)
    output.print_md('Готово: **{0}** элементов'.format(result['placed']))
except Exception:
    log_exception('Инструмент завершился с ошибкой')
    alert('Ошибка. Смотрите pyRevit Output.')
```

---

### 2. Использовать Shared Kernel (lib/)

```python
# Транзакции и error handling
from utils_revit import tx, alert, find_nearest_level

with tx('Создание элементов', doc=doc):
    inst = doc.Create.NewFamilyInstance(...)

# Поиск и размещение семейств
import placement_engine

symbol = placement_engine.find_family_symbol(doc, 'Светильник : Точка')
placement_engine.ensure_symbol_active(doc, symbol)
inst = placement_engine.place_point_family_instance(doc, symbol, pt, level)

# Конвертация единиц
from utils_units import mm_to_ft, ft_to_mm

height_ft = mm_to_ft(2700)  # 2700mm → feet

# Загрузка конфига
import config_loader

rules = config_loader.load_rules()
batch_size = rules.get('batch_size', 25)
type_names = rules['family_type_names']['light_ceiling_point']

# Spatial indexing (dedupe)
import socket_utils

idx = socket_utils._XYZIndex(cell_ft=5.0)
for pt in candidate_points:
    if not idx.has_near(pt.X, pt.Y, pt.Z, dedupe_radius_ft):
        idx.add(pt.X, pt.Y, pt.Z)
        valid_points.append(pt)
```

---

### 3. Работа со связанными моделями

```python
import link_reader

# Выбор связи через UI
link_inst = socket_utils._select_link_instance_ru(doc, 'Выберите связь АР')

# Проверка загрузки
if not link_reader.is_link_loaded(link_inst):
    alert('Связь не загружена')
    return

# Получить документ связи
link_doc = link_reader.get_link_doc(link_inst)

# Трансформация координат
transform = link_reader.get_total_transform(link_inst)
host_pt = transform.OfPoint(link_pt)

# Итерация по элементам связи
for room in link_reader.iter_elements_by_category(
    link_doc,
    DB.BuiltInCategory.OST_Rooms,
    limit=500
):
    # Обработка помещений
    ...
```

---

### 4. Batch processing с Progress Bar

```python
from pyrevit import forms
from utils_revit import tx

def chunks(seq, n):
    """Split sequence into chunks of size n."""
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

# Размещение в батчах
batches = list(chunks(points, batch_size=25))

with forms.ProgressBar(title='Размещение элементов', cancellable=True) as pb:
    pb.max_value = len(batches)

    for i, batch in enumerate(batches):
        pb.update_progress(i + 1, pb.max_value)

        if pb.cancelled:
            break  # Пользователь отменил

        with tx('Batch {0}'.format(i+1), doc=doc, swallow_warnings=True):
            for pt in batch:
                inst = placement_engine.place_point_family_instance(...)
                created_elems.append(inst)
```

---

### 5. Добавить параметр в конфиг

**1. Открыть `config/rules.default.json`:**
```json
{
  "your_new_param": 300,
  "your_array_param": ["значение1", "значение2"]
}
```

**2. Использовать в коде:**
```python
import config_loader

rules = config_loader.load_rules()
your_value = rules.get('your_new_param', 300)  # default=300
```

**Важно:** `config_loader` всегда возвращает дефолты, если ключ отсутствует.

---

### 6. Написать тест

```python
# tests/test_your_module.py
import pytest
from your_module import your_function

def test_basic_case():
    result = your_function(input_data)
    assert result == expected_output

def test_with_fixture(temp_config_file):
    # Создать временный config
    path = temp_config_file({"param": "value"})

    rules = load_rules(path)
    assert rules["param"] == "value"
```

**Запуск:**
```bash
pytest tests/test_your_module.py -v
```

---

### 7. Форматировать код

```bash
# Установить dev зависимости (один раз)
pip install -e .[dev]

# Автоформат
black EOMTemplateTools.extension/lib/your_module.py
isort EOMTemplateTools.extension/lib/your_module.py

# Линтер
flake8 EOMTemplateTools.extension/lib/your_module.py

# Типы (опционально)
mypy EOMTemplateTools.extension/lib/your_module.py
```

---

## 🔍 Где найти примеры?

### Лучшие примеры инструментов:

| Инструмент | Что показывает |
|-----------|----------------|
| `СветВЛифтах` | ✅ Идеальная структура (domain/adapters/orchestrator) |
| | ✅ Работа со связями (nested links) |
| | ✅ Batch processing + Progress Bar |
| | ✅ Spatial indexing (dedupe) |
| `ВыключателиУДверей` | ✅ Поиск элементов по связям |
| | ✅ Proximity search (nearest door) |

### Примеры использования lib/:

```python
# Пример 1: Поиск семейства (fuzzy + mojibake tolerant)
symbol = placement_engine.find_family_symbol(
    doc,
    'Светильник',  # Даже если в Revit "РЎРІРµС‚РёР»СЊРЅРёРє"
    category_bic=DB.BuiltInCategory.OST_LightingFixtures
)

# Пример 2: Dedupe через spatial index
idx = socket_utils._XYZIndex(cell_ft=5.0)
for pt in all_points:
    if not idx.has_near(pt.X, pt.Y, pt.Z, radius_ft=mm_to_ft(500)):
        idx.add(pt.X, pt.Y, pt.Z)
        filtered_points.append(pt)

# Пример 3: Транзакция с rollback
from utils_revit import tx

try:
    with tx('Создание элементов', doc=doc):
        inst1 = doc.Create.NewFamilyInstance(...)
        inst2 = doc.Create.NewFamilyInstance(...)
        # Если ошибка - rollback автоматически
except Exception as e:
    alert('Ошибка: {0}'.format(e))
```

---

## 📚 Дальнейшее изучение

1. **ARCHITECTURE.md** - подробная архитектура (patterns, decisions)
2. **tests/** - примеры тестов и моков
3. **СветВЛифтах/** - reference implementation
4. **lib/** - изучите API каждого модуля (docstrings)

---

## ⚠️ Типичные ошибки новичков

### ❌ Не делайте так:

```python
# 1. НЕ создавать транзакции в цикле (медленно!)
for pt in points:  # 1000 точек = 1000 транзакций ❌
    with Transaction(doc, "Place"):
        inst = doc.Create.NewFamilyInstance(...)

# 2. НЕ использовать точное совпадение имён (mojibake!)
symbol = next(s for s in symbols if s.FamilyName == "Светильник")  # ❌

# 3. НЕ забывать об обработке None
level = find_nearest_level(doc, z)
inst = doc.Create.NewFamilyInstance(pt, symbol, level)  # ❌ level может быть None!
```

### ✅ Правильно:

```python
# 1. Batch transactions
for batch in chunks(points, 25):  # 1000 точек = 40 транзакций ✅
    with tx('Batch', doc=doc):
        for pt in batch:
            inst = placement_engine.place_point_family_instance(...)

# 2. Fuzzy search
symbol = placement_engine.find_family_symbol(doc, "Светильник")  # ✅ Tolerant

# 3. Defensive programming
level = find_nearest_level(doc, z)
if level is None:
    output.print_md('⚠️ Уровень не найден для Z={0}'.format(z))
    continue
inst = placement_engine.place_point_family_instance(doc, symbol, pt, level)
```

---

## 🛠️ Debug Tips

### Включить debug логи

```bash
# Windows (PowerShell)
$env:EOM_FAMILY_DEBUG = "1"

# Теперь placement_engine.py пишет логи в:
# %TEMP%/EOMTemplateTools_family_symbol_debug.log
```

### Использовать pyRevit Output

```python
from pyrevit import script

output = script.get_output()

# Markdown formatting
output.print_md('# Заголовок')
output.print_md('**Жирный текст**')
output.print_md('Размещено: **{0}** элементов'.format(count))

# HTML tables
output.print_table(
    table_data=[
        ['Инструмент', 'Размещено', 'Пропущено'],
        ['Светильники', 42, 3],
        ['Розетки', 128, 7],
    ],
    title='Статистика',
    columns=['Тип', 'Создано', 'Skipped']
)
```

### Логирование ошибок

```python
from utils_revit import log_exception

try:
    # ... ваш код
except Exception:
    log_exception('Описание проблемы', exc_info=True)
    # Stacktrace появится в pyRevit Output
```

---

## 🎓 Проверь себя

После изучения попробуй ответить:

1. ✅ Где должна быть чистая бизнес-логика? (Ответ: `domain.py`)
2. ✅ Как загрузить конфиг? (Ответ: `config_loader.load_rules()`)
3. ✅ Сколько элементов в одной транзакции? (Ответ: 25, см. `batch_size`)
4. ✅ Как избежать дубликатов? (Ответ: `socket_utils._XYZIndex`)
5. ✅ Где найти пример хорошего инструмента? (Ответ: `СветВЛифтах/`)

Если ответил правильно - ты готов создавать инструменты! 🚀

---

**Вопросы?**
- Читай [ARCHITECTURE.md](ARCHITECTURE.md) для глубокого понимания
- Смотри примеры в `tests/`
- Изучай `lib/` (хорошие docstrings)

**Последнее обновление:** 2026-02-09
