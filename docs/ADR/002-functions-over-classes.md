# ADR-002: Функции вместо классов в Shared Kernel

**Статус:** ✅ Принято

**Дата:** 2024-2026 (эволюция проекта)

**Контекст:** Почему `lib/` содержит мало классов (всего 4) и в основном функции?

---

## Проблема

В `lib/` модулях (Shared Kernel) нужно решить:
- **Классы** (ООП подход) vs **Функции** (функциональный подход)

Традиционно ООП учит: "Всё должно быть объектом".

Но в pyRevit/Revit API контексте это не всегда оптимально.

---

## Решение

**Использовать функции как основной подход** в Shared Kernel.

```python
# lib/placement_engine.py - функции, а не классы

def find_family_symbol(doc, name, category_bic=None):
    """Найти символ семейства по имени."""
    ...

def ensure_symbol_active(doc, symbol):
    """Активировать тип семейства."""
    ...

def place_point_family_instance(doc, symbol, pt, prefer_level=None):
    """Разместить point-based инстанс."""
    ...
```

### Исключения (когда используем классы):

```python
# socket_utils.py - класс для spatial indexing
class _XYZIndex:
    """Grid-based spatial index. Требует состояния (grid)."""
    def __init__(self, cell_ft=5.0):
        self.cell_ft = float(cell_ft)
        self.grid = {}  # Состояние!

    def add(self, x, y, z):
        ...

    def has_near(self, x, y, z, radius):
        ...
```

---

## Обоснование

### Почему функции лучше для Revit API?

#### 1. **Revit API не thread-safe**

Revit API **stateful** и работает только в main thread. Классы с состоянием усложняют управление:

```python
# ❌ Плохо: класс с состоянием
class LightPlacer:
    def __init__(self, doc):
        self.doc = doc
        self.symbol = None  # Состояние!
        self.created_count = 0

    def set_symbol(self, symbol):
        self.symbol = symbol

    def place(self, pt):
        inst = self.doc.Create.NewFamilyInstance(pt, self.symbol, ...)
        self.created_count += 1
        return inst

# Проблема: если symbol стал invalid (doc closed), класс сломается
placer = LightPlacer(doc)
placer.set_symbol(symbol)
# ... doc закрыли ...
placer.place(pt)  # CRASH! symbol invalid
```

```python
# ✅ Хорошо: stateless функция
def place_light(doc, symbol, pt):
    """Stateless - все параметры явно."""
    return doc.Create.NewFamilyInstance(pt, symbol, ...)

# Использование:
inst = place_light(doc, symbol, pt)  # Явно передаём всё
```

#### 2. **IronPython 2.7 ограничения**

pyRevit работает на **IronPython 2.7** (legacy Python):
- Нет `@dataclass`
- Нет `typing.Protocol`
- Слабая поддержка метаклассов

Функции работают одинаково в Python 2.7 и 3.8+.

#### 3. **Проще тестировать**

```python
# Функции проще мокировать
def test_place_light():
    mock_doc = MagicMock()
    mock_symbol = MagicMock()
    pt = DB.XYZ(0, 0, 0)

    inst = place_light(mock_doc, mock_symbol, pt)

    mock_doc.Create.NewFamilyInstance.assert_called_once()
```

```python
# Классы требуют setup/teardown
def test_light_placer():
    mock_doc = MagicMock()
    placer = LightPlacer(mock_doc)  # Setup
    placer.set_symbol(mock_symbol)
    inst = placer.place(pt)
    # Teardown?
```

#### 4. **Нет memory leaks**

Revit держит ссылки на C++ объекты. Классы с состоянием могут создавать циклические ссылки:

```python
# ❌ Риск memory leak
class ElementProcessor:
    def __init__(self, doc):
        self.doc = doc
        self.elements = []  # Держим ссылки на Revit элементы

    def process(self):
        for e in self.elements:
            # ...
            pass
        # elements никогда не очищается → leak
```

```python
# ✅ Нет утечек
def process_elements(doc, elements):
    for e in elements:
        # ...
        pass
    # elements уходит из scope → GC очищает
```

#### 5. **Явные зависимости**

```python
# Функции: все зависимости в параметрах (явно)
def find_nearest_level(doc, z_ft):
    levels = list_levels(doc)  # Явно передаём doc
    ...

# Классы: скрытые зависимости в self
class LevelFinder:
    def __init__(self, doc):
        self.doc = doc  # Скрытая зависимость

    def find_nearest(self, z_ft):
        levels = list_levels(self.doc)  # Откуда doc? Из self
        ...
```

---

## Когда использовать классы?

### ✅ Используй классы когда:

1. **Требуется состояние** (например, spatial index)
   ```python
   class _XYZIndex:
       def __init__(self):
           self.grid = {}  # Состояние
   ```

2. **Context managers**
   ```python
   @contextmanager
   def tx(name, doc=None):
       t = Transaction(doc, name)
       t.Start()
       try:
           yield t
       except:
           t.RollBack()
       else:
           t.Commit()
   ```

3. **Callbacks/Handlers**
   ```python
   class _UseDestinationTypesHandler(DB.IDuplicateTypeNamesHandler):
       def OnDuplicateTypeNamesFound(self, args):
           return DB.DuplicateTypeAction.UseDestinationTypes
   ```

### ❌ НЕ используй классы для:

- Группировки утилит (используй модули: `utils_revit.py`)
- Namespace (используй префиксы: `_internal_func`)
- "Правильного ООП" (если нет состояния)

---

## Альтернативы

### Альтернатива 1: Всё в классах (ООП)
**Плюсы:** Привычно для Java/C# разработчиков
**Минусы:** Overkill для stateless операций, risk of leaks

### Альтернатива 2: Functional programming (чистый FP)
**Плюсы:** Immutability, composability
**Минусы:** Revit API императивен (не FP-friendly)

---

## Последствия

### ✅ Плюсы

1. **Простота**: меньше boilerplate
2. **Тестируемость**: легко мокировать
3. **Performance**: нет overhead на создание объектов
4. **Читаемость**: явные зависимости

### ⚠️ Минусы

1. **Нет namespace isolation** (решается префиксами `_private`)
2. **Нет polymorphism** (но Revit API его и не требует)

---

## Статистика проекта

```python
# lib/ (20 модулей)
Всего классов: 4
  - _XYZIndex (spatial indexing - требует состояние)
  - _UseDestinationTypesHandler (callback)
  - 2 других context managers

Всего функций: ~150+

Соотношение: 1 класс на 37 функций
```

---

## Связанные решения

- [ADR-001: Слоеная архитектура](001-layered-architecture.md)
- [ADR-004: Spatial indexing](004-spatial-indexing.md)

---

**Автор:** anton
**Дата принятия:** 2024-Q2 (эволюционно)
**Последнее обновление:** 2026-02-09
