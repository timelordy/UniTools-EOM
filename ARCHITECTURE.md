# EOMTemplateTools Architecture

## 📋 Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Architectural Layers](#architectural-layers)
- [Key Design Patterns](#key-design-patterns)
- [Shared Kernel (lib/)](#shared-kernel-lib)
- [Configuration System](#configuration-system)
- [Tool Development Guide](#tool-development-guide)
- [Testing Strategy](#testing-strategy)
- [Key Design Decisions](#key-design-decisions)

---

## Overview

**EOMTemplateTools** - это enterprise-уровень pyRevit расширение для автоматизации размещения электрооборудования в Autodesk Revit.

### Масштаб проекта
- **11,326 LOC** в extension
- **59 тестов** с моками Revit API
- **20+ переиспользуемых модулей** в `lib/`
- **7 панелей инструментов** (освещение, розетки, щиты, выключатели)

### Архитектурный подход
Проект следует принципам **Clean Architecture** и **Domain-Driven Design**:
- Бизнес-логика изолирована от Revit API
- Слоеное разделение ответственности (domain → adapters → orchestrator → script)
- Shared Kernel для переиспользования кода

---

## Project Structure

```
EOMTemplateTools/
├── EOMTemplateTools.extension/
│   ├── EOM.tab/                          # Основная вкладка в Revit
│   │   ├── 00_Хаб.panel/                 # Управляющий хаб
│   │   ├── 02_Освещение.panel/           # Инструменты освещения
│   │   ├── 03_ЩитыВыключатели.panel/     # Щиты и выключатели
│   │   ├── 04_Розетки.panel/             # Розетки
│   │   └── 10_АвтоРазмещение.panel/      # Авто-размещение
│   │
│   ├── Разработка.tab/                   # Dev-инструменты (отладка)
│   │
│   ├── lib/                              # Shared Kernel (переиспользуемые модули)
│   │   ├── placement_engine.py           # Ядро размещения элементов
│   │   ├── socket_utils.py               # Утилиты для розеток
│   │   ├── link_reader.py                # Чтение связанных моделей
│   │   ├── config_loader.py              # Загрузка конфигураций
│   │   ├── utils_revit.py                # Хелперы Revit API
│   │   ├── utils_units.py                # Конвертация единиц
│   │   ├── floor_panel_niches.py         # Логика ниш для щитов
│   │   ├── entrance_numbering_utils.py   # Нумерация подъездов
│   │   ├── time_savings.py               # Трекинг экономии времени
│   │   └── ...
│   │
│   └── config/
│       └── rules.default.json            # Дефолтные настройки
│
├── tests/                                # Тесты (pytest)
│   ├── conftest.py                       # Fixtures + моки Revit API
│   ├── mocks/revit_api.py                # Stub для DB.* классов
│   └── test_*.py                         # 59 тестов
│
├── tools/                                # Внешние утилиты (TeslaBIM)
├── pyproject.toml                        # Dev зависимости (pytest, black, mypy)
└── ARCHITECTURE.md                       # Этот файл
```

---

## Architectural Layers

### 1️⃣ **Domain Layer** (Бизнес-логика)
**Цель:** Чистая логика, независимая от Revit API.

**Пример:** `СветВЛифтах/domain.py`
```python
# Геометрические расчёты, независимые от Revit
def solid_centroid(elem) -> Optional[DB.XYZ]:
    """Вычисление центроида солида (volume-weighted)."""
    ...

def segment_ranges(levels, shaft_min_z, shaft_max_z):
    """Разбить шахту на сегменты по уровням."""
    ...

def bbox_intersects(bmin, bmax, omin, omax, eps=1e-6) -> bool:
    """Проверка пересечения bounding box."""
    ...
```

**Характеристики:**
- ✅ Нет прямых вызовов Revit API (только data structures)
- ✅ Легко тестируется (без Revit)
- ✅ Переиспользуется в других инструментах

---

### 2️⃣ **Adapters Layer** (Интеграция с Revit API)
**Цель:** Адаптеры для чтения/записи в Revit.

**Пример:** `СветВЛифтах/adapters.py`
```python
def pick_light_symbol(doc, cfg, type_names):
    """Выбрать символ светильника из документа или через UI."""
    # 1. Попытка найти по сохранённому ID
    # 2. Поиск по имени семейства
    # 3. UI-диалог выбора
    ...

def check_symbol_compatibility(symbol) -> bool:
    """Проверить совместимость типа размещения (wall-hosted vs point)."""
    ...

def store_symbol_id(cfg, key, symbol):
    """Сохранить ID выбранного символа в конфиг."""
    ...
```

**Характеристики:**
- ✅ Инкапсулирует Revit API calls
- ✅ Обработка ошибок (try/except)
- ✅ Конвертация единиц (mm → feet)

---

### 3️⃣ **Orchestrator Layer** (Координация workflow)
**Цель:** Связать domain + adapters + user interaction.

**Пример:** `СветВЛифтах/orchestrator.py` (1029 LOC)
```python
def run_placement(doc, output, script_module):
    """Основной workflow размещения светильников в шахтах лифта."""

    # 1. Загрузка конфигурации
    rules = config_loader.load_rules()

    # 2. Выбор типа светильника (через адаптер)
    symbol = pick_light_symbol(doc, cfg, type_names)

    # 3. Выбор связанной модели АР (или автопоиск)
    link_inst = socket_utils._select_link_instance_ru(doc, 'Выберите связь АР')
    link_doc = link_reader.get_link_doc(link_inst)

    # 4. Сбор шахт лифта (domain-логика)
    shafts = collect_shafts_from_families(link_doc, ...)

    # 5. Генерация точек размещения (domain)
    points = []
    for shaft in shafts:
        segments = segment_ranges(levels, shaft_min, shaft_max)
        for seg_min, seg_max in segments:
            z_mid = seg_min + (seg_max - seg_min) * 0.5
            points.append((pt, level, bbox_min, bbox_max))

    # 6. Размещение элементов (batch transactions)
    with forms.ProgressBar(...) as pb:
        for batch in chunks(points, batch_size=25):
            with tx('ЭОМ: Светильники шахты лифта', doc=doc):
                for pt, lvl, ... in batch:
                    inst = place_wall_hosted(doc, symbol, wall, pt, lvl)
                    set_comments(inst, comment_value)

    # 7. Отчёт и метрики
    output.print_md('Размещено светильников: **{0}**'.format(created_count))
    return {'placed': created_count, 'shafts': len(shafts)}
```

**Характеристики:**
- ✅ Progress bars для UX
- ✅ Batch processing (25 элементов/транзакция)
- ✅ Dedupe (пространственный индекс)
- ✅ Rollback-безопасность

---

### 4️⃣ **Script Layer** (Entry Point)
**Цель:** Тонкий слой для вызова из pyRevit.

**Пример:** `СветВЛифтах/script.py` (42 LOC)
```python
from pyrevit import revit, script
from utils_revit import alert, log_exception
import orchestrator

def main():
    doc = revit.doc
    output = script.get_output()
    res = orchestrator.run_placement(doc, output, script)

    # Метрики экономии времени
    report_time_saved(output, 'lights_elevator', res['placed'])

    # Глобальная переменная для Hub
    global EOM_HUB_RESULT
    EOM_HUB_RESULT = {'stats': {...}, 'time_saved_minutes': minutes}

try:
    main()
except Exception:
    log_exception('Place lift shaft lights failed')
    alert('Инструмент завершился с ошибкой. Проверьте pyRevit Output.')
```

**Характеристики:**
- ✅ Минимальная логика (< 50 LOC)
- ✅ Error handling на верхнем уровне
- ✅ Интеграция с Hub через глобальные переменные

---

## Key Design Patterns

### 🎯 Pattern 1: **Domain-Driven Design (DDD)**

Каждый инструмент структурирован по DDD-слоям:

```
Tool.pushbutton/
├── domain.py         # Чистая бизнес-логика
├── adapters.py       # Revit API адаптеры
├── orchestrator.py   # Координация workflow
├── script.py         # Entry point (pyRevit)
└── constants.py      # Константы (опционально)
```

**Пример инструмента:** `02_Освещение.panel/СветВЛифтах.pushbutton/`

---

### 🔄 Pattern 2: **Repository Pattern** (Shared Kernel)

Переиспользуемая логика вынесена в `lib/`:

| Модуль | Ответственность |
|--------|----------------|
| `placement_engine.py` | Ядро размещения: поиск семейств, активация символов, точечное/hosted размещение |
| `link_reader.py` | Чтение связанных моделей (в т.ч. nested links) |
| `socket_utils.py` | Розетки: dedupe, spatial indexing, room analysis |
| `config_loader.py` | Загрузка `rules.default.json` с дефолтами |
| `utils_revit.py` | Транзакции, nearest level, error logging |
| `utils_units.py` | `mm_to_ft()`, `ft_to_mm()` |
| `floor_panel_niches.py` | Поиск ниш для щитов (regex, fuzzy matching) |

**Пример использования:**
```python
from utils_revit import tx, alert, find_nearest_level
from utils_units import mm_to_ft
import placement_engine

# В любом инструменте:
with tx('Создание розеток', doc=doc):
    symbol = placement_engine.find_family_symbol(doc, 'РозеткаДвойная')
    placement_engine.ensure_symbol_active(doc, symbol)
    inst = placement_engine.place_point_family_instance(doc, symbol, pt)
```

---

### 🔐 Pattern 3: **Defensive Programming**

Код устойчив к edge-cases:

```python
def solid_centroid(elem):
    if elem is None:
        return None  # Early return

    try:
        opt = DB.Options()
        try:
            opt.DetailLevel = DB.ViewDetailLevel.Fine
        except Exception:
            pass  # Swallow attribute errors
        geom = elem.get_Geometry(opt)
    except Exception:
        geom = None

    if geom is None:
        return None

    # Volume-weighted averaging
    total_vol = 0.0
    for solid in iter_solids(geom):
        try:
            c = solid.ComputeCentroid()
            v = float(solid.Volume)
        except Exception:
            continue  # Skip invalid solids

        if v <= 1e-9:
            continue
        ...
```

**Характеристики:**
- ✅ None-checks everywhere
- ✅ Try/except на каждом Revit API call
- ✅ Fallback-стратегии (например, fuzzy search после точного поиска)

---

### 📦 Pattern 4: **Batch Processing**

Revit требует транзакций, которые дороги по памяти. Решение: **batch commits**.

```python
batches = list(chunks(points, batch_size=25))  # 25 элементов/транзакция

with forms.ProgressBar(title='Размещение', cancellable=True) as pb:
    for i, batch in enumerate(batches):
        pb.update_progress(i + 1, len(batches))
        if pb.cancelled:
            break  # Пользователь может отменить

        with tx('ЭОМ: Светильники', doc=doc, swallow_warnings=True):
            for pt, lvl, ... in batch:
                inst = place_instance(...)
                created_elems.append(inst)
```

**Польза:**
- ✅ Меньше транзакций = меньше памяти
- ✅ Progress bar с возможностью отмены
- ✅ Rollback при ошибке только текущего batch (остальное сохраняется)

---

### 🗺️ Pattern 5: **Spatial Indexing** (Deduplication)

Для предотвращения дублирования используется пространственный индекс:

```python
# socket_utils._XYZIndex
class _XYZIndex:
    """Grid-based spatial index for fast near-neighbor queries."""
    def __init__(self, cell_ft=5.0):
        self.cell_ft = float(cell_ft)
        self.grid = {}  # {(cx, cy, cz): [points]}

    def add(self, x, y, z):
        cx, cy, cz = self._cell_key(x, y, z)
        self.grid.setdefault((cx, cy, cz), []).append((x, y, z))

    def has_near(self, x, y, z, radius_ft):
        # Check only adjacent cells (O(1) amortized)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    cell_key = (cx+dx, cy+dy, cz+dz)
                    for px, py, pz in self.grid.get(cell_key, []):
                        if distance(x, y, z, px, py, pz) < radius_ft:
                            return True
        return False
```

**Использование:**
```python
idx = socket_utils._XYZIndex(cell_ft=5.0)
for pt in candidate_points:
    if idx.has_near(pt.X, pt.Y, pt.Z, dedupe_radius_ft):
        skipped_dedupe += 1
    else:
        idx.add(pt.X, pt.Y, pt.Z)
        points.append(pt)
```

---

## Shared Kernel (lib/)

### Core Modules

#### `placement_engine.py`
**Роль:** Ядро размещения элементов.

**Ключевые функции:**
```python
find_family_symbol(doc, name, category_bic=None, limit=None)
    # Поиск символа семейства (с fuzzy fallback)

ensure_symbol_active(doc, symbol)
    # Активировать тип (если был неактивен)

place_point_family_instance(doc, symbol, pt, prefer_level=None)
    # Размещение point-based инстанса

get_symbol_placement_type(symbol) -> (FamilyPlacementType, str)
    # OneLevelBased / FaceBased / TwoLevelsBased

format_family_type(symbol) -> str
    # "Семейство : Тип" для UI
```

**Особенности:**
- Fuzzy search (mojibake-tolerant)
- Debug logging (`EOM_FAMILY_DEBUG=1`)
- Codepoint analysis для отладки encoding

---

#### `socket_utils.py`
**Роль:** Утилиты для розеток (и любых electrical fixtures).

**Ключевые функции:**
```python
_XYZIndex(cell_ft=5.0)
    # Пространственный индекс для dedupe

_select_link_instance_ru(doc, prompt)
    # UI выбора связанной модели

get_room_apartment_number(room) -> Optional[str]
    # Извлечение номера квартиры (3 fallback-стратегии)

_compile_patterns(patterns) -> List[re.Pattern]
    # Компиляция regex для фильтрации

_match_any(rx_list, text) -> bool
    # Проверка совпадения с любым паттерном

_norm_type_key(s) -> str
    # Нормализация имён типов (Cyrillic→Latin, whitespace, dashes)
```

---

#### `link_reader.py`
**Роль:** Работа со связанными моделями (в т.ч. nested links).

```python
list_link_instances(doc) -> List[RevitLinkInstance]
    # Список всех link instances

is_link_loaded(link_inst) -> bool
    # Проверка загрузки

get_link_doc(link_inst) -> Document
    # Получить документ связи

get_total_transform(link_inst) -> Transform
    # Трансформация (для вложенных связей рекурсивно)

iter_elements_by_category(doc, bic, limit=None, level_id=None)
    # Итератор элементов по категории
```

---

#### `config_loader.py`
**Роль:** Загрузка конфигураций с дефолтами.

```python
load_rules(path=None) -> dict
    # Загрузка config/rules.default.json
    # Дефолты для 50+ параметров:
    #   - comment_tag: 'AUTO_EOM'
    #   - batch_size: 25
    #   - max_place_count: 200
    #   - dedupe_radius_mm: 500
    #   - family_type_names: {...}
    #   - lift_shaft_min_height_mm: 2000
    #   и т.д.
```

---

#### `utils_revit.py`
**Роль:** Хелперы для Revit API.

```python
@contextmanager
def tx(name, doc=None, swallow_warnings=False):
    # Контекст-менеджер для транзакций
    # Автоматический rollback при исключении

alert(msg, title=None)
    # TaskDialog с обработкой mojibake

log_exception(msg, exc_info=True)
    # Логирование в pyRevit Output

find_nearest_level(doc, z_ft) -> Level
    # Поиск ближайшего уровня по Z

set_comments(elem, value)
    # Запись в параметр "Примечания"
```

---

#### `floor_panel_niches.py`
**Роль:** Логика поиска ниш для щитов.

```python
find_niches_in_link(link_doc, niche_patterns, ...)
    # Поиск помещений-ниш по regex

normalize_type_names(value) -> List[str]
    # Нормализация списков типов

match_niche_pattern(room_name, patterns) -> bool
    # Проверка совпадения с паттернами ниш
```

---

### Utility Modules

| Модуль | Назначение |
|--------|-----------|
| `utils_units.py` | `mm_to_ft()`, `ft_to_mm()` |
| `entrance_numbering_utils.py` | Нумерация подъездов (extract_number) |
| `time_savings.py` | Трекинг экономии времени (`report_time_saved()`) |
| `text_utils.py` | Обработка текста (mojibake, normalization) |
| `hub_command_parser.py` | Парсинг команд для Hub (`run:tool_id:job_id`) |
| `rollback_utils.py` | Utilities для rollback элементов |
| `room_name_utils.py` | Анализ имён помещений |

---

## Configuration System

### `config/rules.default.json`

Централизованная конфигурация всех инструментов:

```json
{
  "comment_tag": "AUTO_EOM",
  "batch_size": 25,
  "max_place_count": 200,
  "dedupe_radius_mm": 500,

  "family_type_names": {
    "light_ceiling_point": ["Светильник Центр : Точка", "Light Center : Point"],
    "light_lift_shaft": ["Светильник Лифт : Точка"],
    "switch_single": ["Выключатель 1кл : Тип1"],
    "socket_double": ["Розетка 2х : РЗТ-2-О-IP20"]
  },

  "floor_panel_niche_patterns": ["ниша", "niche", "эом", "шахт"],
  "floor_panel_height_mm": 1700,

  "lift_shaft_family_names": ["Лифт", "Elevator"],
  "lift_shaft_min_height_mm": 2000,
  "lift_shaft_edge_offset_mm": 500,

  "socket_spacing_mm": 3000,
  "socket_height_mm": 300,
  "avoid_door_mm": 300,
  "avoid_radiator_mm": 500
}
```

**Загрузка:**
```python
import config_loader
rules = config_loader.load_rules()

batch_size = int(rules.get('batch_size', 25))
type_names = rules.get('family_type_names', {}).get('light_lift_shaft')
```

---

## Tool Development Guide

### Как создать новый инструмент?

#### 1. Создать структуру
```
EOM.tab/ВашаПанель.panel/ВашИнструмент.pushbutton/
├── domain.py        # Бизнес-логика
├── adapters.py      # Revit API адаптеры
├── orchestrator.py  # Workflow
├── script.py        # Entry point
└── constants.py     # Константы (опционально)
```

#### 2. Domain Layer
```python
# domain.py
def calculate_placement_points(room_bbox, spacing_mm):
    """Pure domain logic, no Revit API."""
    points = []
    # ... расчёты геометрии
    return points

def filter_by_distance(points, min_distance_ft):
    """Filter points by minimum spacing."""
    ...
```

#### 3. Adapters Layer
```python
# adapters.py
from pyrevit import DB
import placement_engine

def pick_symbol(doc, cfg, type_names):
    """Adapter: выбор символа из Revit."""
    symbol = placement_engine.find_family_symbol(doc, type_names[0])
    if not symbol:
        # UI fallback
        symbol = placement_engine.user_pick_family_symbol(doc, categories=[...])
    return symbol

def create_instances(doc, symbol, points, level):
    """Adapter: создание инстансов."""
    instances = []
    for pt in points:
        inst = placement_engine.place_point_family_instance(doc, symbol, pt, level)
        instances.append(inst)
    return instances
```

#### 4. Orchestrator
```python
# orchestrator.py
from pyrevit import forms
from utils_revit import tx
import config_loader
from domain import calculate_placement_points
from adapters import pick_symbol, create_instances

def run_placement(doc, output, script):
    rules = config_loader.load_rules()

    # 1. Выбор параметров
    symbol = pick_symbol(doc, cfg, type_names)
    rooms = collect_rooms(doc)

    # 2. Domain: расчёт точек
    all_points = []
    for room in rooms:
        pts = calculate_placement_points(room.bbox, spacing_mm)
        all_points.extend(pts)

    # 3. Размещение (batches)
    created = 0
    for batch in chunks(all_points, batch_size=25):
        with tx('ВашИнструмент', doc=doc):
            instances = create_instances(doc, symbol, batch, level)
            created += len(instances)

    output.print_md('Создано: **{0}**'.format(created))
    return {'placed': created}
```

#### 5. Script (Entry Point)
```python
# script.py
from pyrevit import revit, script
from utils_revit import alert, log_exception
import orchestrator

try:
    doc = revit.doc
    output = script.get_output()
    result = orchestrator.run_placement(doc, output, script)
except Exception:
    log_exception('ВашИнструмент failed')
    alert('Ошибка. Смотрите pyRevit Output.')
```

---

## Testing Strategy

### Структура тестов
```
tests/
├── conftest.py                 # Fixtures + Revit API моки
├── mocks/
│   ├── revit_api.py            # Stub для DB.* классов
│   └── __init__.py
├── test_config_loader.py       # Тесты загрузки конфига
├── test_hub_command_parser.py  # Парсинг команд Hub
├── test_floor_panel_niches.py  # Логика ниш
└── test_entrance_numbering_utils.py
```

### Fixtures (conftest.py)
```python
@pytest.fixture
def temp_config_file():
    """Создаёт временный JSON config для теста."""
    ...

@pytest.fixture
def sample_room_names_cyrillic():
    return ["Кухня", "Гостиная", "Спальня", ...]

@pytest.fixture
def hydrant_keywords():
    return {
        "include": ["пожарн", "пк", "hydrant"],
        "exclude": ["пкс", "перекрест"]
    }
```

### Пример теста
```python
def test_parse_run_command():
    data = parse_command("run:lights_center:job123")
    assert data["action"] == "run"
    assert data["tool_id"] == "lights_center"
    assert data["job_id"] == "job123"

def test_load_rules_with_defaults(temp_config_file):
    path = temp_config_file({"comment_tag": "CUSTOM"})
    rules = load_rules(path)
    assert rules["comment_tag"] == "CUSTOM"
    assert rules["batch_size"] == 25  # default
```

### Запуск тестов
```bash
# Все тесты
pytest tests/

# С coverage
pytest tests/ --cov=EOMTemplateTools.extension/lib --cov-report=html

# Конкретный тест
pytest tests/test_hub_command_parser.py -v
```

---

## Key Design Decisions

### 1. **Почему функции, а не классы?**

**Вопрос:** Почему `lib/` содержит мало классов (всего 4) и в основном функции?

**Ответ:**
- Revit API **не thread-safe** и не требует состояния между вызовами
- **Stateless functions** проще тестировать и дебажить
- Исторически pyRevit-скрипты работают в IronPython 2.7 (ограничения по ООП)
- Функциональный подход снижает риск memory leaks (Revit держит ссылки на объекты)

**Исключения (где используются классы):**
- `_XYZIndex` - spatial indexing требует состояния (grid)
- Transaction contexts (`tx()`) - используют context managers

---

### 2. **Почему mojibake handling везде?**

**Проблема:**
```python
# Русские имена семейств в Revit могут быть:
"Светильник"          # UTF-8
"Ð¡Ð²ÐµÑ‚Ð¸Ð»ÑŒÐ½Ð¸Ðº"  # UTF-8 декодированный как cp1251
"РЎРІРµС‚РёР»СЊРЅРёРє"  # Двойной mojibake
```

**Решение:**
```python
def _demojibake(value):
    """Best-effort fix for UTF-8 text misdecoded as cp1251."""
    current = txt
    for _ in range(8):  # Max 8 iterations
        fixed = current.encode('cp1251').decode('utf-8')
        if fixed == current:
            break  # Converged
        if _score(fixed) < _score(current):
            current = fixed
        else:
            break
    return current
```

**Почему важно:**
- Revit хранит имена в разных кодировках (legacy файлы)
- Поиск по точному совпадению не работает
- Fuzzy matching + mojibake tolerance = устойчивость

---

### 3. **Почему batch transactions?**

**Проблема:** Revit жрёт память при частых транзакциях.

**Решение:**
```python
# Плохо:
for pt in points:  # 1000 точек = 1000 транзакций
    with Transaction(doc, "Place"):
        inst = doc.Create.NewFamilyInstance(...)

# Хорошо:
for batch in chunks(points, 25):  # 1000 точек = 40 транзакций
    with Transaction(doc, "Place batch"):
        for pt in batch:
            inst = doc.Create.NewFamilyInstance(...)
```

**Польза:**
- 40× меньше транзакций
- Progress bar с детализацией
- Rollback только текущего batch при ошибке

---

### 4. **Почему Shared Kernel вместо inheritance?**

**Вопрос:** Почему `lib/` (общие модули), а не базовые классы?

**Ответ:**
- **Composition over Inheritance** - инструменты независимы
- Проще переиспользовать функции: `from socket_utils import _XYZIndex`
- Нет сложных иерархий наследования (KISS)
- pyRevit-скрипты загружаются динамически, inheritance усложнит reload

---

### 5. **Почему `del sys.modules['placement_engine']`?**

**Проблема:** pyRevit кеширует модули между запусками скрипта.

**Симптомы:**
- Изменения в `lib/placement_engine.py` не применяются
- Нужно перезапускать Revit для обновления кода

**Workaround:**
```python
# В начале script.py
import sys
if 'placement_engine' in sys.modules:
    del sys.modules['placement_engine']
if 'floor_panel_niches' in sys.modules:
    del sys.modules['floor_panel_niches']

# Теперь import загрузит свежую версию
import placement_engine
```

**Почему не решено "правильно":**
- pyRevit reload hooks работают нестабильно в IronPython
- Этот workaround гарантирует свежий код при каждом запуске

---

### 6. **Почему Link search depth = 4?**

**Проблема:** Вложенные связи (nested links) могут быть на разных уровнях:
```
HostDoc
 └─ Link_AR.rvt
     └─ Link_KR.rvt
         └─ Link_VK.rvt  <-- Лифты могут быть здесь
```

**Решение:**
```python
def iter_loaded_link_docs(doc, max_depth=2, visited=None, depth=0):
    """Yield (link_inst, link_doc, transform, is_nested)."""
    if depth > max_depth:
        return

    for ln in list_link_instances(doc):
        ld = get_link_doc(ln)
        yield ln, ld, transform, (depth > 0)

        # Рекурсия для вложенных связей
        for sub in iter_loaded_link_docs(ld, max_depth, visited, depth+1):
            yield sub
```

**Настройка:**
```python
# rules.default.json
"lift_shaft_link_search_depth": 4  # Поиск до 4 уровней вложенности
```

---

## Performance Considerations

### Лимиты и защиты

```python
# rules.default.json
"max_place_count": 200          # Максимум элементов за запуск
"scan_limit_rooms": 500         # Лимит сканирования помещений
"batch_size": 25                # Размер batch-транзакции
"dedupe_radius_mm": 500         # Радиус дедупликации
```

### Spatial Indexing

- **O(1) amortized** поиск ближайших элементов
- Grid-based (cell_ft = 5.0)
- Вместо O(n²) перебора

### Lazy Evaluation

```python
# Не загружаем все элементы сразу
for elem in link_reader.iter_elements_by_category(doc, bic, limit=500):
    # Обработка по одному
    ...
```

---

## Future Improvements

### 1. Рефакторинг монолитных скриптов
- [ ] `ЩЭВНишах/script.py` (3977 LOC) → split на domain/adapters/orchestrator
- [ ] Каждый модуль < 500 LOC

### 2. Усиление типизации
```python
# Включить strict mypy
[tool.mypy]
disallow_untyped_defs = true
```

### 3. Документация API
- [ ] Sphinx documentation для `lib/`
- [ ] Examples для каждого модуля

### 4. CI/CD
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -e .[dev]
      - run: pytest tests/ --cov
```

---

## Контакты и поддержка

**Автор:** anton
**Репозиторий:** `c:\Users\anton\EOMTemplateTools`
**Версия:** 0.2.0

**Для вопросов:**
- Читайте этот `ARCHITECTURE.md`
- Изучите примеры в `02_Освещение.panel/СветВЛифтах.pushbutton/`
- Смотрите тесты в `tests/`

---

**Последнее обновление:** 2026-02-09
**Документ поддерживается:** ✅ Актуально
