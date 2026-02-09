# ADR-003: Batch Processing транзакций

**Статус:** ✅ Принято

**Дата:** 2024-Q3

**Контекст:** Revit жрёт память при создании элементов. Как оптимизировать?

---

## Проблема

При размещении большого количества элементов (100+ светильников, розеток) наивный подход вызывает проблемы:

```python
# ❌ Плохо: транзакция на каждый элемент
for pt in points:  # 500 точек
    with Transaction(doc, "Place light"):
        t.Start()
        inst = doc.Create.NewFamilyInstance(pt, symbol, level)
        t.Commit()

# Проблемы:
# - 500 транзакций = 500 Undo записей в памяти
# - Revit тормозит (UI freeze)
# - Memory leak риск
# - Невозможно показать прогресс (каждая транзакция = UI block)
```

**Симптомы:**
- Revit висит при размещении 200+ элементов
- Память растёт до 4GB+
- Пользователь не видит прогресс (нет feedback)
- Нельзя отменить (Cancel) операцию

---

## Решение

**Batch processing:** группировать элементы в батчи по 25 штук.

```python
# ✅ Хорошо: batch transactions
def chunks(seq, n):
    """Split sequence into chunks of size n."""
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

batches = list(chunks(points, batch_size=25))  # 500 точек = 20 батчей

with forms.ProgressBar(title='Размещение', cancellable=True) as pb:
    pb.max_value = len(batches)

    for i, batch in enumerate(batches):
        pb.update_progress(i + 1, pb.max_value)

        if pb.cancelled:
            break  # Пользователь отменил

        with tx('Batch {0}'.format(i+1), doc=doc, swallow_warnings=True):
            for pt in batch:  # 25 элементов в одной транзакции
                inst = placement_engine.place_point_family_instance(
                    doc, symbol, pt, level
                )
                created_elems.append(inst)
```

**Результат:**
- 500 точек = **20 транзакций** вместо 500
- Progress bar с детализацией (каждый батч = 1 шаг)
- Можно отменить (Cancel между батчами)
- Memory usage стабилен

---

## Детали реализации

### 1. Размер батча

```python
# config/rules.default.json
{
  "batch_size": 25,  # Оптимальное значение
  "max_place_count": 200  # Лимит элементов за запуск
}
```

**Почему 25?**
- Экспериментально: balance между performance и UX
- < 10: слишком много транзакций (overhead)
- > 50: долгий UI freeze между updates

### 2. Progress Bar

```python
from pyrevit import forms

with forms.ProgressBar(title='Размещение', cancellable=True, step=1) as pb:
    pb.max_value = len(batches)

    for i, batch in enumerate(batches):
        pb.update_progress(i + 1, pb.max_value)  # UI update

        if pb.cancelled:
            output.print_md('**Отменено пользователем.**')
            break
```

**Преимущества:**
- Пользователь видит прогресс: "15 / 20 батчей"
- Можно отменить в любой момент
- Нет UI freeze (обновление между батчами)

### 3. Rollback безопасность

```python
# utils_revit.py
@contextmanager
def tx(name, doc=None, swallow_warnings=False):
    """Context manager для транзакций с rollback."""
    t = Transaction(doc or revit.doc, name)
    t.Start()
    try:
        yield t
        t.Commit()
    except Exception:
        t.RollBack()  # Откат при ошибке
        raise
```

**Поведение при ошибке:**
- Батч #5 упал → rollback только батча #5
- Батчи #1-4 сохранены ✅
- Батчи #6-20 не выполняются (прерывание)

---

## Альтернативы

### Альтернатива 1: Одна большая транзакция

```python
# Одна транзакция на все 500 элементов
with Transaction(doc, "Place all"):
    for pt in points:  # 500 элементов
        inst = doc.Create.NewFamilyInstance(...)
```

**Плюсы:** Fastest (1 транзакция)
**Минусы:**
- ❌ Нет прогресса (UI freeze на минуты)
- ❌ Нельзя отменить
- ❌ Один элемент упал → rollback всех 500

### Альтернатива 2: Транзакция на элемент

```python
for pt in points:
    with Transaction(doc, "Place"):
        inst = doc.Create.NewFamilyInstance(...)
```

**Плюсы:** Детальный rollback
**Минусы:**
- ❌ 500 транзакций = memory overhead
- ❌ Медленно (overhead на каждую транзакцию)

### Альтернатива 3: Async/Threading

```python
# Попытка использовать threads
from threading import Thread

def place_batch(batch):
    with Transaction(doc, "Batch"):
        for pt in batch:
            inst = doc.Create.NewFamilyInstance(...)

threads = []
for batch in batches:
    t = Thread(target=place_batch, args=(batch,))
    threads.append(t)
    t.start()
```

**Плюсы:** Parallel execution?
**Минусы:**
- ❌ **Revit API не thread-safe!**
- ❌ Crashes гарантированы

---

## Последствия

### ✅ Плюсы

1. **Performance**: 20× меньше транзакций (500 → 25)
2. **UX**: Progress bar + Cancel
3. **Memory**: стабильное потребление
4. **Robustness**: partial rollback (не всё или ничего)

### ⚠️ Минусы

1. **Complexity**: нужна утилита `chunks()`
2. **Granularity**: rollback батча, а не элемента

### 📊 Метрики

**Тест:** Размещение 500 светильников

| Подход | Транзакций | Время | Memory | UX |
|--------|-----------|-------|---------|-----|
| Naive (1 per elem) | 500 | 45 сек | 3.2 GB | ❌ No progress |
| One big | 1 | 12 сек | 1.8 GB | ❌ UI freeze |
| **Batch (25)** | **20** | **15 сек** | **1.5 GB** | ✅ Progress + Cancel |

---

## Применение в проекте

### Инструменты с batching:

- ✅ `СветВЛифтах` - batch_size=25
- ✅ `СветПоЦентру` - batch_size=25
- ✅ `Розетки` - batch_size=25
- 🚧 `ЩЭВНишах` - рефакторинг в процессе

### Конфигурация

```json
// rules.default.json
{
  "batch_size": 25,           // Размер батча
  "max_place_count": 200,     // Лимит элементов (защита от зависания)
  "scan_limit_rooms": 500     // Лимит сканирования помещений
}
```

---

## Связанные решения

- [ADR-001: Слоеная архитектура](001-layered-architecture.md) - orchestrator управляет batching
- [ADR-004: Spatial indexing](004-spatial-indexing.md) - dedupe перед batching

---

**Автор:** anton
**Дата принятия:** 2024-Q3
**Последнее обновление:** 2026-02-09
