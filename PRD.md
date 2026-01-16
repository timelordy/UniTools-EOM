# PRD: EOM Template Tools (pyRevit)

---

# 🎯 PRIORITIZED PRD: PRODUCTION READINESS CHECKLIST

**Status**: Pre-production | **Version**: 0.2 | **Updated**: 2026-01-17

---

## Executive Summary

This document outlines what MUST be done to bring EOMTemplateTools to production readiness. The project has significant code written but critical gaps in testing, code organization, and feature completion.

**Current State**:
- 6 of 16 backlog items at 95% (ready for polish)
- 5 items at 10-20% (code exists, needs work)
- 5 items not started
- Only 1 test file exists (critical gap!)
- socket_utils.py is 90KB/2364+ lines (needs refactoring)

---

## 🔴 CRITICAL / BLOCKERS (Must fix before any production use)

### C1. Missing Test Coverage
**Priority**: P0 - BLOCKER
**Current State**: Only `test_pk_indicator_rules.py` exists (52 lines)
**Impact**: Cannot verify code works correctly, regressions will go unnoticed

**Required Actions**:
| Test File | Target Module | Estimated Effort |
|-----------|---------------|------------------|
| test_link_reader.py | link_reader.py (33KB) | 4h |
| test_socket_utils.py | socket_utils.py (90KB) | 8h |
| test_placement_engine.py | placement_engine.py | 3h |
| test_config_loader.py | config_loader.py | 2h |
| test_utils_units.py | utils_units.py | 1h |

**Acceptance Criteria**:
- [ ] Unit tests for all pure functions (no Revit API mocking needed)
- [ ] Integration tests runnable in pyRevit console
- [ ] Coverage for room matching patterns, coordinate transforms, deduplication logic

---

### C2. Code Organization - socket_utils.py Monolith
**Priority**: P0 - BLOCKER
**Current State**: 90KB, 2364+ lines in a single file
**Impact**: Unmaintainable, high cognitive load, merge conflicts likely

**Required Actions**:
Split into logical modules:
```
lib/
├── socket_utils/
│   ├── __init__.py          # Re-exports for backward compat
│   ├── room_matching.py     # Room name patterns, classification
│   ├── wall_geometry.py     # Wall finding, face references
│   ├── socket_placement.py  # Core placement logic
│   ├── deduplication.py     # XYZIndex, point deduplication
│   └── ui_helpers.py        # Symbol pickers, link selectors
```

**Acceptance Criteria**:
- [ ] No file exceeds 500 lines
- [ ] Existing import paths work via `__init__.py` re-exports
- [ ] All existing scripts still function

---

### C3. Error Handling Standardization
**Priority**: P0 - BLOCKER
**Current State**: Bare `except:` blocks throughout codebase
**Impact**: Silent failures, impossible to debug in production

**Required Actions**:
- Audit all `except:` blocks (estimated 100+ occurrences)
- Replace with specific exceptions or at minimum `except Exception as e`
- Add logging for caught exceptions
- Create `lib/exceptions.py` with custom exception classes

---

## 🟠 HIGH PRIORITY (Features at 10-20% needing completion)

### H1. AC Sockets (04_AC) - 10% Ready
**Current State**: 4867 lines of code, complex but incomplete
**Gap Analysis**:
- [x] Basket detection from AR link
- [x] Wall finding near basket
- [x] Height placement (300mm from ceiling)
- [ ] Exterior wall exclusion logic incomplete
- [ ] Corner offset (200mm from wall) not implemented
- [ ] Room-basket association unreliable
- [ ] No tests

**Effort**: 8h development + 4h testing

---

### H2. Low Voltage Sockets (06_Low_Voltage) - 20% Ready
**Current State**: Script exists but logic incomplete
**Gap Analysis**:
- [x] Intercom keyword detection
- [x] Router/cabinet detection
- [ ] Door handle side detection for intercom placement
- [ ] Height rules (1400mm intercom, 300mm router)
- [ ] Fallback when markers not found in AR
- [ ] No tests

**Effort**: 6h development + 2h testing

---

### H3. Switches (Place_Switches_ByDoors) - 10% Ready
**Current State**: 3542 lines of code, complex multi-room logic
**Gap Analysis**:
- [x] Door detection from AR
- [x] Room association (FromRoom/ToRoom)
- [x] Handle side detection
- [ ] Wet room outside placement incomplete
- [ ] 2-gang vs 1-gang selection logic
- [ ] Natural light room detection
- [ ] Wall-hosted placement failing on some models
- [ ] No tests

**Effort**: 12h development + 4h testing

---

### H4. Room Lights (08_Lights) - 10% Ready
**Current State**: Only room center placement exists
**Gap Analysis**:
- [x] Basic room center placement (demo)
- [ ] Kitchen pattern (center + above sink)
- [ ] Bathroom pattern (above mirror)
- [ ] WC pattern (above door)
- [ ] Bedroom/living room socket selection
- [ ] Room type classification

**Effort**: 12h development + 4h testing

---

### H5. Lift Shaft Lights - 10% Ready
**Current State**: Complex script, working but edge cases
**Gap Analysis**:
- [x] Shaft detection from ShaftOpening
- [x] Level-based segmentation
- [x] Edge lights (top/bottom)
- [ ] 500mm rule from top/bottom not enforced correctly
- [ ] Wall-hosted placement sometimes fails
- [ ] Debug view creation

**Effort**: 6h development + 2h testing

---

### H6. Entrance Door Lights - 10% Ready
**Current State**: Script exists but incomplete
**Gap Analysis**:
- [x] Entrance door detection
- [ ] Exterior placement logic
- [ ] Roof exit detection
- [ ] Height above door

**Effort**: 4h development + 2h testing

---

### H7. PK Indicators - In Progress
**Current State**: Script complete, needs validation
**Gap Analysis**:
- [x] Hydrant keyword detection
- [x] Exclude keyword logic
- [x] View-based placement
- [x] Unit tests exist (only tested module!)
- [ ] Real-world validation on sample projects

**Effort**: 2h validation + 2h bug fixes

---

## 🟡 MEDIUM PRIORITY (Features at 95% needing polish)

### M1. General Sockets (01_General) - 95% Ready
**Needs**:
- [ ] Edge case testing (rooms < 10m²)
- [ ] Window/door exclusion zone verification
- [ ] Integration tests

**Effort**: 4h testing/polish

---

### M2. Kitchen Unit Sockets (02_Kitchen_Unit) - 95% Ready
**Needs**:
- [ ] Sink/stove offset verification (600mm rule)
- [ ] Total count cap (4 per kitchen)
- [ ] Integration tests

**Effort**: 4h testing/polish

---

### M3. Kitchen General Sockets (03_Kitchen_General) - 95% Ready
**Needs**:
- [ ] Fridge area detection
- [ ] Opposite wall logic verification
- [ ] Integration tests

**Effort**: 3h testing/polish

---

### M4. Wet Room Sockets (05_Wet) - 95% Ready
**Needs**:
- [ ] Washing machine area detection
- [ ] Electric towel warmer position
- [ ] 600mm from sink/tub rule
- [ ] Integration tests

**Effort**: 4h testing/polish

---

### M5. SHDUP (07_ShDUP) - 95% Ready
**Needs**:
- [ ] Sink-to-tub positioning logic
- [ ] Height verification (300mm)
- [ ] Integration tests

**Effort**: 3h testing/polish

---

### M6. Apartment Panels (Place_Panel_ShK_AboveApartmentDoor) - 95% Ready
**Needs**:
- [ ] Door lintel height detection
- [ ] Panel type selection based on apartment
- [ ] Integration tests

**Effort**: 4h testing/polish

---

## 🟢 LOW PRIORITY (Not started features)

### L1. Floor Panels in Common Areas (ЩЭ)
**Backlog Item**: #13
**Description**: Panel placement in common area niches based on apartment count per floor
**Dependencies**: Level detection, apartment counting, niche finding in AR
**Effort**: 16h development

---

### L2. Storage Room Equipment
**Backlog Item**: #14
**Description**: Panel (1700mm), switch (900mm), light per storage room
**Dependencies**: Storage room detection from AR (name patterns)
**Effort**: 12h development

---

### L3. Entrance Numbering
**Backlog Item**: #16
**Description**: Junction boxes at building entrances per AR drawings
**Dependencies**: Entrance detection, numbering rules
**Effort**: 8h development

---

## 🔧 TECHNICAL DEBT

### T1. Documentation
**Current State**: README exists but outdated
**Required**:
- [ ] API documentation for lib modules
- [ ] User guide with screenshots
- [ ] Configuration reference (rules.default.json)
- [ ] Troubleshooting guide

**Effort**: 8h

---

### T2. Configuration Validation
**Current State**: No schema validation for rules.default.json
**Required**:
- [ ] JSON schema for configuration
- [ ] Validation at load time
- [ ] Clear error messages for missing/invalid keys

**Effort**: 4h

---

### T3. Logging Infrastructure
**Current State**: Inconsistent use of logger, output, trace
**Required**:
- [ ] Standardized logging wrapper
- [ ] Log levels (DEBUG, INFO, WARN, ERROR)
- [ ] Optional file logging for debugging

**Effort**: 4h

---

### T4. Performance Optimization
**Current State**: Some scans are unbounded (can hang on large models)
**Required**:
- [ ] Audit all iter_* functions for limit usage
- [ ] Add configurable scan_cap to all collectors
- [ ] Progress feedback for long operations

**Effort**: 6h

---

### T5. Code Style & Linting
**Current State**: No linting setup
**Required**:
- [ ] Add pyproject.toml or setup.cfg
- [ ] Configure ruff or flake8
- [ ] Pre-commit hooks
- [ ] Type hints for public APIs

**Effort**: 4h

---

## 📊 EFFORT SUMMARY

| Category | Items | Total Effort |
|----------|-------|--------------|
| Critical/Blockers | 3 | 20h |
| High Priority | 7 | 56h |
| Medium Priority | 6 | 22h |
| Low Priority | 3 | 36h |
| Technical Debt | 5 | 26h |
| **TOTAL** | **24** | **160h** |

---

## 🎯 RECOMMENDED IMPLEMENTATION ORDER

### Phase 1: Foundation (Week 1-2)
1. C1: Add test infrastructure and tests for core modules
2. C2: Refactor socket_utils.py into submodules
3. C3: Fix error handling

### Phase 2: Complete High-Value Features (Week 3-4)
4. H3: Finish switches (most complex)
5. H1: Finish AC sockets
6. H2: Finish low voltage

### Phase 3: Polish 95% Features (Week 5)
7. M1-M6: Test and polish all near-complete features

### Phase 4: Validation (Week 6)
8. End-to-end testing on 2-3 real projects
9. Bug fixes from validation
10. Documentation updates

### Phase 5: Expansion (Future)
11. L1-L3: Not started features
12. Advanced features as needed

---

## 📋 ACCEPTANCE CRITERIA FOR PRODUCTION

- [ ] All Critical/Blocker items resolved
- [ ] All 95%-ready features tested and validated
- [ ] At least 3 High Priority features completed
- [ ] Test coverage for all lib/* modules
- [ ] No bare `except:` blocks
- [ ] Configuration validation in place
- [ ] Tested on at least 2 different project templates
- [ ] Documentation for end users

---

## 1. Цель
Сократить время и ошибки при подготовке ЭОМ‑шаблонов/моделей за счёт полуавтоматической расстановки типовых элементов (свет, розетки, щиты, выключатели) на основе данных из активного документа (EOM) и связанной архитектурной модели (AR Link), не изменяя linked‑модель.

## 2. Контекст и пользователи
- **Пользователи:** BIM/ЭОМ‑проектировщики, координаторы, инженеры, работающие в Revit с pyRevit.
- **Контекст:** EOM — активный документ, куда создаются элементы; AR — Revit Link, откуда читаются Rooms/геометрия/опорные элементы.
- **Ограничение:** linked‑модель только для чтения; все создаётся в host‑документе.

## 3. Область охвата (Scope)

### In-scope
- Набор pyRevit‑команд (кнопок) для:
  - Диагностики связей/трансформаций.
  - Расстановки светильников по помещениям/точкам.
  - Расстановки розеток по правилам (общие, кухня, мокрые зоны, слаботочка, кондиционирование и др.).
  - Расстановки/обработки щитов/панелей и связанных операций обслуживания.
- Конфигурирование поведения через JSON‑правила.
- Маркировка созданных элементов через Comments‑tag (для идемпотентности/повторных запусков).

### Out-of-scope (на сейчас)
- Полная параметризация под любые стандарты без настройки правил.
- Автозагрузка семейств из внешних источников.
- Изменение AR‑модели или автоматическое создание помещений в host‑документе.

## 4. Пользовательские сценарии (User Stories)
1. **Как инженер**, я хочу выбрать AR Link и увидеть корректный Transform, чтобы убедиться, что размещение будет без смещений.
2. **Как инженер**, я хочу расставить свет по центрам комнат из AR, чтобы быстро получить базовую расстановку.
3. **Как инженер**, я хочу расставить розетки по набору правил (включая кухню/мокрые зоны/AC), чтобы стандартизировать проект и избежать пропусков.
4. **Как координатор**, я хочу повторно запускать инструменты без дублей, чтобы поддерживать идемпотентность при обновлениях модели.

## 5. Функциональные требования

### 5.1 Диагностика линков
- Показ списка `RevitLinkInstance` в активном документе.
- Вывод статуса загрузки и Transform (basis + origin).
- Выбор линка пользователем, если их несколько.

### 5.2 Размещение элементов
- Все операции размещения выполняются **в активном документе**.
- Для координат из AR обязательно применяется `GetTotalTransform()` (link → host).
- Поддержка пакетного размещения (batch) и ограничение количества операций за прогон (cap/limits).

### 5.3 Конфигурация (rules)
- Единицы в конфиге: **мм**, в Revit: **feet** (конвертеры).
- Настраиваемые параметры:
  - Имена типов семейств (Family : Type) или fallback‑подбор.
  - Высоты размещения/смещения.
  - Радиусы дедупликации и минимальные расстояния.
  - Паттерны имён помещений для классификации (кухня/мокрые/холлы и т.д.).

### 5.4 Идемпотентность и дедупликация
- Созданные элементы получают Comments‑тег вида `AUTO_EOM:<TOOL_TAG>` (настраиваемый префикс).
- Повторный запуск не должен создавать дубликаты при неизменной геометрии/правилах.

### 5.5 Обработка ошибок
- Ясные сообщения пользователю при:
  - Отсутствии AR Link/Rooms/подходящих семейств.
  - Некорректных трансформациях/невозможности вычислить точку размещения.
  - Неподдерживаемом типе размещения семейства.
- Логи/трейс в пределах pyRevit (без утечки чувствительных данных).

## 6. Нефункциональные требования
- **Безопасность:** не модифицировать linked‑документы.
- **Производительность:** ограничение сканов (rooms/doors/etc.), кэширование (например, face refs/sketchplanes).
- **Совместимость:** pyRevit + Revit версии команды (указать целевые версии в релиз‑заметках проекта).
- **Надёжность:** graceful‑degradation (fallback‑стратегии при отсутствии геометрии/точек).

## 7. Метрики успеха
- Сокращение времени “типовой расстановки” минимум на X% (определить baseline командой).
- Доля успешных размещений (created/processed) ≥ целевого порога на типовых проектах.
- Количество ручных исправлений после прогона (по чек-листу QA) снижается.

## 8. Риски и зависимости
- Различия в стандартах именования семейств/типов между проектами.
- Несогласованные координаты/Shared Coordinates между AR и EOM.
- Нестабильность геометрических вычислений в отдельных случаях (низкие высоты, сложные стены/семейства).
- Зависимость от наличия нужных семейств в host‑проекте.

## 9. Acceptance Criteria (минимальный набор)
- Инструменты запускаются из pyRevit и не падают на типовых моделях команды.
- При наличии корректного типа семейства из правил — он находится и используется.
- Повторный прогон не создаёт дубликаты (при неизменных исходных данных).
- Linked‑модель не меняется (нет транзакций в link_doc).

## 10. Backlog автоматизации (из таблицы)

| № | Задача | Правило/описание | От кого | Ручные трудозатраты | Готовность |
|---:|---|---|---|---|---:|
| 1 | Расстановка бытовых розеток в квартирах | 300мм от пола, каждые 3м периметра комнат, не ставим на стену с окном, за радиатором отопления и в дверном проеме. В прихожих до 10м² одна розетка, более 10м² — две розетки в противоположных углах прихожей. | ЭОМ | 5-7 минут на комнату | 95% |
| 2 | Расстановка розеток на кухне в зоне гарнитура в квартирах | 1100мм от пола, в зоне кухонного гарнитура. Ставим на расстоянии 600мм от оси раковины, от оси электроплиты. Учесть общее количество розеток на кухне — 4шт с учетом розеток вне зоны гарнитура. | ЭОМ | 5-7 минут на комнату | 95% |
| 3 | Расстановка розеток на кухне вне зоны гарнитура в квартирах | 300мм от пола, в зоне размещения холодильника + на противоположной стене от гарнитура. | ЭОМ | 3-5 минут на комнату | 95% |
| 4 | Расстановка розеток для кондиционеров в квартирах | 300мм от потолка, 200мм от стены, в углу на стене рядом с корзиной для внешнего блока. Не ставим на внешнюю стену. | ЭОМ | 1-3 минуты на комнату | 10% |
| 5 | Расстановка розеток в ванной в квартирах | 1300мм от пола над стиральной машиной или в месте предполагаемого расположения электрополотенцесушителя. Ставим на расстоянии 600мм от оси раковины и 600мм от края ванной. | ЭОМ | 1-3 минуты на комнату | 95% |
| 6 | Расстановка розеток для питания слаботочного оборудования в квартирах | Розетка для домофона на высоте 1400мм рядом с домофоном; розетка для роутера — рядом с квартирным слаботочным щитком или распредкоробкой СС в прихожей. | ЭОМ | 1-3 минуты на комнату | 20% |
| 7 | Расстановка выключателей в квартирах | Высота 900мм, со стороны дверной ручки. В спальне и гостиной — двухклавишный выключатель, в остальных помещениях — одноклавишные. Для санузлов и ванной выключатель устанавливается в прихожей; в остальных комнатах — внутри комнаты. | ЭОМ | 1-3 минуты на комнату | 10% |
| 8 | Расстановка светильников в квартирах | В спальне/гостиной — потолочный патрон с клеммником по центру комнаты. На кухне и в прихожей — потолочный патрон по центру комнаты. В ванной над раковиной светильник на высоте 2м, в санузле над дверью — стенной патрон. | ЭОМ | 1-3 минуты на комнату | 10% |
| 9 | Расстановка ШДУП в ванных | В ванной, между раковиной и ванной, на высоте 300мм. В общем случае зависит от взаимного расположения раковины и ванной. | ЭОМ | 1-3 минуты на ванну | 95% |
| 10 | Расстановка светильников в шахте лифта | По светильнику на каждом этаже + светильники на расстоянии не более 500мм от самой верхней и самой нижней точек шахты. | ЭОМ | 10 минут на 1 шахту | 10% |
| 11 | Расстановка светильников над входами в здание | По светильнику над каждой дверью входа в здание + выходы на кровлю (светильник снаружи). | ЭОМ | 1-3 минуты на дверь | 10% |
| 12 | Расстановка световых указателей "ПК" | Указатель над каждым пожарным краном. | ЭОМ | 1-3 минуты на этаж |  |
| 13 | Расстановка этажных щитов в МОП в нишах | ЩЭ с разделением по типу в зависимости от количества квартир на этаже. | ЭОМ | 5-7 минут на этаж |  |
| 14 | Расстановка оборудования в индивидуальных кладовых | Щиток на высоте 1700мм, выключатель на 900мм, светильник (потолок или стена) для каждой кладовой. | ЭОМ | 15 минут на кладовую |  |
| 15 | Расстановка квартирных щитков ЩК | Установить квартирные щитки над дверной перемычкой. | ЭОМ | 7 минут на квартиру | 95% |
| 16 | Нумерация подъезда | Распаячная коробка возле входов в каждую БС согласно чертежам АР. | ЭОМ | 10 минут на 1 вход |  |

## 11. Открытые вопросы
- Какие именно Revit‑версии поддерживаем (20xx)? **Revit 2022**.
- Какой “золотой” набор семейств/типов обязателен для шаблона EOM? **Берём те, что уже есть в шаблоне**.
- Нужны ли разные профили правил под разные заказчики/объекты (несколько JSON)? **Пока один профиль**.
