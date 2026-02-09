# EOMTemplateTools

> **Enterprise-уровень pyRevit расширение для автоматизации размещения электрооборудования в Autodesk Revit**

[![Python](https://img.shields.io/badge/Python-2.7%20%7C%203.8+-blue.svg)](https://www.python.org/)
[![pyRevit](https://img.shields.io/badge/pyRevit-4.8+-orange.svg)](https://www.notion.so/pyRevit-bd907d6292ed4ce997c46e84b6ef67a0)
[![Tests](https://img.shields.io/badge/tests-59%20passing-brightgreen.svg)](tests/)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 📋 Содержание

- [О проекте](#о-проекте)
- [Возможности](#возможности)
- [Быстрый старт](#быстрый-старт)
- [Архитектура](#архитектура)
- [Установка для разработчиков](#установка-для-разработчиков)
- [Документация](#документация)
- [Тестирование](#тестирование)
- [Вклад в проект](#вклад-в-проект)
- [Roadmap](#roadmap)

---

## О проекте

**EOMTemplateTools** - это набор инструментов для автоматизации проектирования электрических систем в Revit, специально разработанный для шаблонов ЭОМ (электрооборудование общедомовое).

### Масштаб

- **11,326 строк кода** в extension
- **20+ переиспользуемых модулей** в Shared Kernel
- **59 автотестов** с моками Revit API
- **7 панелей инструментов**: Освещение, Розетки, Щиты, Выключатели, Хаб

### Технологический стек

- **Язык:** Python 2.7/3.8+ (IronPython совместимость)
- **Framework:** pyRevit 4.8+
- **API:** Autodesk Revit API 2019+
- **Тестирование:** pytest, unittest.mock
- **Code Quality:** black, flake8, isort, mypy, pre-commit

---

## Возможности

### 💡 Освещение

- **Светильники в шахтах лифта**
  - Автоматическое размещение по центру шахты
  - Поддержка вложенных связей (nested links до 4 уровней)
  - Размещение на каждом уровне + края шахты
  - Wall-hosted и point-based светильники

- **Светильники по центру помещения**
  - Размещение по геометрическому центру или centroid
  - Поддержка вытянутых помещений (2 светильника)
  - Фильтрация по типу помещения (исключение ниш, балконов)

### 🔌 Розетки

- **Автоматическое размещение розеток**
  - Расстановка по периметру помещения (шаг 3000 мм)
  - Избегание дверей и радиаторов
  - Специальные правила для кухонь (розетки под холодильник)
  - Dedupe через spatial indexing (O(1) амортизированная сложность)

### ⚡ Щиты и выключатели

- **Щиты в нишах**
  - Поиск ниш по паттернам в именах помещений
  - Выбор типа щита в зависимости от этажа
  - Размещение с автоматическим определением высоты

- **Выключатели у дверей**
  - Размещение на расстоянии 300 мм от двери
  - Автоматическое определение стороны размещения
  - Поддержка linked walls

### 🎯 Управляющий хаб

- Централизованный запуск всех инструментов
- Трекинг экономии времени
- Статистика по размещённым элементам
- Command-based интерфейс

---

## Быстрый старт

### Для пользователей

1. **Установите pyRevit** (если ещё не установлен):
   ```
   https://github.com/eirannejad/pyRevit/releases
   ```

2. **Скопируйте расширение** в папку pyRevit extensions:
   ```
   %APPDATA%\pyRevit\Extensions\
   ```

3. **Перезапустите Revit** или выполните Reload в pyRevit

4. **Откройте вкладку "EOM"** в Revit ribbon

5. **Выберите инструмент** и следуйте подсказкам

### Для разработчиков

См. раздел [Установка для разработчиков](#установка-для-разработчиков)

---

## Архитектура

Проект следует принципам **Clean Architecture** и **Domain-Driven Design (DDD)**.

```
┌─────────────────────────────────────────────────────────┐
│                    Script Layer                         │
│              (Entry Points - script.py)                 │
│              • Тонкий слой (<50 LOC)                   │
│              • Error handling                           │
│              • Integration с Hub                        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                Orchestrator Layer                       │
│          (Координация Workflow - orchestrator.py)      │
│          • Progress bars                                │
│          • Batch processing                             │
│          • Transaction management                       │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼─────────┐       ┌─────────▼─────────┐
│  Adapters Layer │       │   Domain Layer    │
│  (adapters.py)  │       │   (domain.py)     │
│  • Revit API    │       │  • Pure logic     │
│  • UI dialogs   │       │  • Geometry calc  │
│  • Conversions  │       │  • No Revit API   │
└─────────────────┘       └───────────────────┘
        │                           │
        └─────────────┬─────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              Shared Kernel (lib/)                       │
│  • placement_engine.py   • link_reader.py              │
│  • socket_utils.py       • config_loader.py            │
│  • utils_revit.py        • floor_panel_niches.py       │
└─────────────────────────────────────────────────────────┘
```

### Ключевые принципы

1. **Слоеная архитектура**: domain → adapters → orchestrator → script
2. **Dependency Inversion**: domain не зависит от Revit API
3. **Shared Kernel**: переиспользуемые модули в `lib/`
4. **Defensive Programming**: обработка всех edge cases
5. **Batch Processing**: транзакции по 25 элементов

📖 **Подробнее:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Установка для разработчиков

### 1. Клонировать репозиторий

```bash
git clone <repository-url>
cd EOMTemplateTools
```

### 2. Установить dev зависимости

```bash
# Создать виртуальное окружение (опционально)
python -m venv venv
venv\Scripts\activate

# Установить зависимости
pip install -e .[dev]
```

Это установит:
- pytest, pytest-cov
- black, isort, flake8
- mypy
- pre-commit

### 3. Настроить pre-commit hooks

```bash
pre-commit install
```

Hooks автоматически проверят:
- Форматирование (black, isort)
- Линтинг (flake8)
- Типы (mypy - частично)

### 4. Запустить тесты

```bash
# Все тесты
pytest tests/

# С coverage
pytest tests/ --cov=EOMTemplateTools.extension/lib --cov-report=html

# Конкретный тест
pytest tests/test_hub_command_parser.py -v
```

### 5. Форматирование кода

```bash
# Автоформат
black EOMTemplateTools.extension/lib/your_module.py
isort EOMTemplateTools.extension/lib/your_module.py

# Проверка всех правил
make lint  # или вручную: flake8, black --check, isort --check
```

---

## Документация

### Для разработчиков

| Документ | Описание | Когда читать |
|----------|----------|--------------|
| [README.md](README.md) | Этот файл - обзор проекта | Первым делом |
| [QUICKSTART.md](QUICKSTART.md) | Quick reference, примеры кода | Хочу быстро начать |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Подробная архитектура, паттерны | Хочу понять "почему так" |
| [docs/ADR/](docs/ADR/) | Architectural Decision Records | Хочу узнать историю решений |

### Architectural Decision Records (ADR)

Мы документируем важные архитектурные решения в формате ADR:

- [ADR-001: Слоеная архитектура (Clean Architecture)](docs/ADR/001-layered-architecture.md)
- [ADR-002: Функции вместо классов](docs/ADR/002-functions-over-classes.md)
- [ADR-003: Batch processing транзакций](docs/ADR/003-batch-transactions.md)
- [ADR-004: Spatial indexing для dedupe](docs/ADR/004-spatial-indexing.md)
- [ADR-005: Mojibake tolerance](docs/ADR/005-mojibake-handling.md)

### Примеры кода

```python
# Пример 1: Использование Shared Kernel
from utils_revit import tx, find_nearest_level
from utils_units import mm_to_ft
import placement_engine

with tx('Создание светильников', doc=doc):
    symbol = placement_engine.find_family_symbol(doc, 'Светильник : Точка')
    placement_engine.ensure_symbol_active(doc, symbol)
    inst = placement_engine.place_point_family_instance(doc, symbol, pt, level)

# Пример 2: Batch processing
from pyrevit import forms

def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

batches = list(chunks(points, batch_size=25))
with forms.ProgressBar(title='Размещение', cancellable=True) as pb:
    pb.max_value = len(batches)
    for i, batch in enumerate(batches):
        pb.update_progress(i + 1, pb.max_value)
        if pb.cancelled:
            break
        with tx('Batch {0}'.format(i+1), doc=doc):
            for pt in batch:
                inst = create_instance(pt)

# Пример 3: Spatial indexing (dedupe)
import socket_utils

idx = socket_utils._XYZIndex(cell_ft=5.0)
for pt in candidate_points:
    if not idx.has_near(pt.X, pt.Y, pt.Z, dedupe_radius_ft):
        idx.add(pt.X, pt.Y, pt.Z)
        valid_points.append(pt)
```

📖 **Больше примеров:** [QUICKSTART.md](QUICKSTART.md)

---

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest tests/

# Конкретный модуль
pytest tests/test_hub_command_parser.py

# С подробным выводом
pytest tests/ -v

# Coverage report
pytest tests/ --cov=EOMTemplateTools.extension/lib --cov-report=html
open htmlcov/index.html
```

### Структура тестов

```
tests/
├── conftest.py                     # Fixtures + моки Revit API
├── mocks/
│   └── revit_api.py                # Stub для DB.* классов
├── test_config_loader.py           # Загрузка конфигов
├── test_hub_command_parser.py      # Парсинг команд Hub
├── test_floor_panel_niches.py      # Логика поиска ниш
└── test_entrance_numbering_utils.py
```

### Моки Revit API

Revit API недоступен вне Revit, поэтому используются моки:

```python
# tests/conftest.py
if "pyrevit" not in sys.modules:
    pyrevit_stub = types.ModuleType("pyrevit")
    from mocks.revit_api import DB as MockDB
    pyrevit_stub.DB = MockDB
    pyrevit_stub.forms = MagicMock()
    sys.modules["pyrevit"] = pyrevit_stub
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
    assert rules["batch_size"] == 25  # default применён
```

---

## Вклад в проект

### Workflow для новых фич

1. **Создать ветку**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Написать код** (следуя Clean Architecture)
   ```
   Tool.pushbutton/
   ├── domain.py         # Чистая логика
   ├── adapters.py       # Revit API
   ├── orchestrator.py   # Workflow
   └── script.py         # Entry point (<50 LOC)
   ```

3. **Добавить тесты**
   ```bash
   pytest tests/test_your_feature.py
   ```

4. **Запустить линтеры**
   ```bash
   black your_module.py
   isort your_module.py
   flake8 your_module.py
   ```

5. **Создать Pull Request**

### Code Style

- **Форматирование:** black (line-length=120)
- **Import sorting:** isort (profile=black)
- **Линтинг:** flake8
- **Типизация:** mypy (частично)

### Правила

- ✅ Каждый файл < 500 LOC (кроме legacy code)
- ✅ Тесты для domain-логики
- ✅ Docstrings для публичных API
- ✅ Error handling (try/except + log_exception)
- ✅ Batch processing для > 10 элементов
- ✅ Progress bars для долгих операций

---

## Roadmap

### ✅ Версия 0.2.0 (Текущая)

- [x] Clean Architecture рефакторинг
- [x] 59 автотестов
- [x] Документация (README, ARCHITECTURE, QUICKSTART, ADRs)
- [x] Pre-commit hooks

### 🚧 Версия 0.3.0 (Планируется)

- [ ] Рефакторинг монолитного `ЩЭВНишах/script.py` (3977 LOC → 4×500 LOC)
- [ ] Strict typing (mypy `disallow_untyped_defs = true`)
- [ ] CI/CD (GitHub Actions для автотестов)
- [ ] Coverage > 80%

### 🔮 Версия 0.4.0 (Будущее)

- [ ] Sphinx documentation
- [ ] Performance profiling (pyRevit performance panel)
- [ ] Плагин-система для кастомных правил
- [ ] WebUI для настройки конфигов

---

## Лицензия

Proprietary - все права защищены.

---

## Контакты

**Автор:** anton
**Репозиторий:** `c:\Users\anton\EOMTemplateTools`
**Версия:** 0.2.0

---

## Благодарности

- **pyRevit Team** за отличный framework
- **Autodesk** за Revit API
- **Community** за best practices и паттерны

---

**Последнее обновление:** 2026-02-09
