# Strict Typing Migration Plan

## Цель

Постепенно включить strict mypy typing для всей кодовой базы.

## Текущее состояние (2026-02-09)

- ✅ Базовые проверки mypy включены
- ✅ `check_untyped_defs = true` - проверяет типы в нетипизированных функциях
- ⚠️ `disallow_untyped_defs = false` - не требует type hints (пока)
- ⚠️ `ignore_missing_imports = true` - игнорирует Revit API (untyped)

### Статистика

```bash
# Запустить для подсчёта:
find EOMTemplateTools.extension/lib -name "*.py" -exec grep -l "def " {} \; | wc -l
# ~20 модулей в lib/

# Модулей с type hints: ~2-3 (config_loader частично)
# Модулей без type hints: ~17-18
```

---

## Стратегия миграции

### Подход: **Incremental per-module**

1. ✅ Не ломаем существующий код
2. ✅ Добавляем type hints постепенно (модуль за модулем)
3. ✅ Начинаем с простых модулей
4. ✅ Проверяем каждый модуль отдельно через `mypy.overrides`

### Фазы

#### Phase 1: Простые utility модули (легко типизировать)

- [ ] `utils_units.py` - простые функции конвертации
- [ ] `text_utils.py` - обработка строк
- [ ] `entrance_numbering_utils.py` - парсинг номеров

**Критерий:** Функции без Revit API, простые типы (str, int, float, Optional).

#### Phase 2: Configuration и data modules

- [x] `config_loader.py` - уже частично типизирован
- [ ] `hub_command_parser.py` - парсинг команд
- [ ] `time_savings.py` - метрики

**Критерий:** Data processing, dict/list операции.

#### Phase 3: Domain modules

- [ ] `floor_panel_niches.py` - логика ниш
- [ ] `room_name_utils.py` - анализ помещений
- [ ] Новые domain.py модули

**Критерий:** Бизнес-логика без прямых Revit API calls.

#### Phase 4: Adapters и сложные модули

- [ ] `link_reader.py` - работа со связями
- [ ] `socket_utils.py` - spatial indexing
- [ ] `placement_engine.py` - размещение элементов
- [ ] `utils_revit.py` - транзакции, error handling

**Критерий:** Прямое взаимодействие с Revit API (требует type stubs).

---

## Как мигрировать модуль?

### 1. Выбрать модуль из Phase 1-2

```bash
# Пример: utils_units.py
```

### 2. Добавить type hints

```python
# Было:
def mm_to_ft(mm):
    if mm is None:
        return None
    return float(mm) / 304.8

# Стало:
from typing import Optional

def mm_to_ft(mm: Optional[float]) -> Optional[float]:
    """Convert millimeters to feet.

    Args:
        mm: Value in millimeters, or None

    Returns:
        Value in feet, or None if input was None
    """
    if mm is None:
        return None
    return float(mm) / 304.8
```

### 3. Включить strict mode для модуля

```toml
# pyproject.toml
[[tool.mypy.overrides]]
module = "utils_units"
disallow_untyped_defs = true
disallow_incomplete_defs = true
```

### 4. Запустить mypy

```bash
mypy EOMTemplateTools.extension/lib/utils_units.py
```

### 5. Исправить ошибки

```bash
# Если mypy ругается, добавить type: ignore для сложных случаев
inst = doc.Create.NewFamilyInstance(...)  # type: ignore[attr-defined]
```

### 6. Commit

```bash
git add EOMTemplateTools.extension/lib/utils_units.py pyproject.toml
git commit -m "feat: add type hints to utils_units.py"
```

---

## Пример: utils_units.py (типизированный)

```python
# -*- coding: utf-8 -*-
"""Unit conversion utilities with full type annotations."""

from typing import Optional


def mm_to_ft(mm: Optional[float]) -> Optional[float]:
    """Convert millimeters to feet.

    Args:
        mm: Value in millimeters, or None

    Returns:
        Value in feet, or None if input was None
    """
    if mm is None:
        return None
    return float(mm) / 304.8


def ft_to_mm(ft: Optional[float]) -> Optional[float]:
    """Convert feet to millimeters.

    Args:
        ft: Value in feet, or None

    Returns:
        Value in millimeters, or None if input was None
    """
    if ft is None:
        return None
    return float(ft) * 304.8


def inches_to_mm(inches: Optional[float]) -> Optional[float]:
    """Convert inches to millimeters.

    Args:
        inches: Value in inches, or None

    Returns:
        Value in millimeters, or None if input was None
    """
    if inches is None:
        return None
    return float(inches) * 25.4
```

---

## Type Stubs для Revit API

Revit API (DB.*) не имеет type hints. Решения:

### Вариант 1: Type: ignore (quick fix)

```python
from pyrevit import DB

def create_level(doc, name: str, elevation: float):
    level = DB.Level.Create(doc, elevation)  # type: ignore[attr-defined]
    level.Name = name  # type: ignore[attr-defined]
    return level
```

### Вариант 2: Stub файлы (будущее)

```python
# stubs/pyrevit/DB.pyi
class Level:
    @staticmethod
    def Create(doc: Document, elevation: float) -> Level: ...

    @property
    def Name(self) -> str: ...

    @Name.setter
    def Name(self, value: str) -> None: ...
```

**Статус:** Stub-ы для Revit API - это будущая работа (Phase 5).

---

## Метрики прогресса

### Цели

- **Q1 2026:** 5 модулей типизировано (Phase 1)
- **Q2 2026:** 10 модулей типизировано (Phase 1-2)
- **Q3 2026:** 15 модулей типизировано (Phase 1-3)
- **Q4 2026:** Все новые модули пишутся с type hints

### Трекинг

```bash
# Подсчёт типизированных модулей:
grep -l "disallow_untyped_defs = true" pyproject.toml | wc -l

# Или вручную обновлять этот файл:
```

#### Типизированные модули (✅):

1. config_loader.py (частично)

#### В процессе (🚧):

(пока нет)

#### Запланированы (📋):

- utils_units.py
- text_utils.py
- hub_command_parser.py
- time_savings.py
- entrance_numbering_utils.py

---

## Полезные ресурсы

- [mypy documentation](https://mypy.readthedocs.io/)
- [typing module](https://docs.python.org/3/library/typing.html)
- [Type hints cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)

---

**Последнее обновление:** 2026-02-09
**Следующий шаг:** Типизировать `utils_units.py` (Phase 1, легко)
