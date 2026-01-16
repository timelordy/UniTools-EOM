# EOM Template Tools (pyRevit)

Набор простых инструментов для Revit + pyRevit:

* **EOM (host/active document)** — активный документ, куда мы **размещаем** элементы.
* **AR (linked document)** — архитектурная модель, подключенная как **Revit Link**, откуда мы **читаем** элементы (например, Rooms).

Важный принцип: **linked model не изменяем** — только чтение.

## Структура репозитория

```
EOMTemplateTools/
  EOMTemplateTools.extension/          <- pyRevit extension (подключается в pyRevit)
    EOM.tab/
      Setup.panel/
        Diagnostics.pushbutton/
          script.py
          bundle.yaml
        PlaceLightsFromRooms.pushbutton/
          script.py
          bundle.yaml
    lib/
      __init__.py
      utils_units.py
      utils_revit.py
      link_reader.py
      placement_engine.py
      config_loader.py
    config/
      rules.default.json
  README.md
  .gitignore
```

## Установка в pyRevit

pyRevit ищет расширения в папке:

* `%APPDATA%\pyRevit\Extensions`
  (обычно `C:\Users\<you>\AppData\Roaming\pyRevit\Extensions`)

### Вариант A (простой): копирование

1. Скопируй папку `EOMTemplateTools.extension` в `%APPDATA%\pyRevit\Extensions`.
2. Перезапусти Revit (или Reload в pyRevit, если используешь).

### Вариант B (dev-режим): junction/симлинк (рекомендуется)

Так можно хранить исходники в одном месте, а в pyRevit будет ссылка.

В этой заготовке уже создан junction:

* `C:\Users\anton\EOMTemplateTools\EOMTemplateTools.extension`
  → `%APPDATA%\pyRevit\Extensions\EOMTemplateTools.extension`

Если нужно сделать вручную:

```bat
mklink /J "%APPDATA%\pyRevit\Extensions\EOMTemplateTools.extension" "C:\path\to\repo\EOMTemplateTools.extension"
```

## Подготовка модели (Revit)

1. Открой **EOM** (шаблон/рабочий файл), в который будем размещать элементы.
2. Подключи **AR** как Revit Link:
   * `Insert` → `Link Revit`
   * Дождись загрузки линка.
3. Убедись, что в AR есть **Rooms** (помещения) и они реально размещены.

## Почему важны `doc`, `link_doc` и `Transform`

* `doc` — активный документ (EOM). В него создаются новые элементы.
* `link_doc` — документ связанной модели (AR). Его можно читать, но **нельзя менять**.

Координаты элементов в `link_doc` находятся в системе координат линка.
Чтобы разместить что-то в host-документе по точкам из линка, обязательно применяем трансформацию:

* `transform = link_instance.GetTotalTransform()`
* `host_point = transform.OfPoint(link_point)`

## Единицы измерения

* Внутренние единицы Revit: **feet**.
* В конфиге правила храним в **mm**.
* Утилиты: `mm_to_ft()` и `ft_to_mm()` в `lib/utils_units.py`.

## Кнопки

### 1) Diagnostics: List AR Links

Путь:

* `EOM` tab → `Setup` panel → `Diagnostics: List AR Links`

Что делает:

* выводит список `RevitLinkInstance` в активном документе
* показывает: имя, путь (если доступен), загружен ли, и **Transform (link → host)**

Используй это, чтобы проверить:

* линк реально подгружен
* трансформация не Identity (если есть смещения/углы)

### 2) Place: Light at Linked Room Centers (demo)

Путь:

* `EOM` tab → `Setup` panel → `Place: Light at Linked Room Centers (demo)`

Алгоритм:

1. Предлагает выбрать один линк (если их несколько).
2. Читает все `Rooms` из `link_doc`.
3. Для каждого Room берёт центр (bbox/LocationPoint), преобразует в координаты host (`transform.OfPoint`).
4. Добавляет Z-смещение из правила `light_center_room_height_mm`.
5. Размещает точечный светильник **в активном документе**.
6. Пишет в `Comments`: `AUTO_EOM:LIGHT_FROM_LINK` (тег настраивается в JSON).

#### Требования

* В **EOM** должен быть загружен тип семейства светильника.
  По умолчанию ожидается имя типа из `config/rules.default.json`:

  `EOM_Light_Ceiling_Point : Type 01`

Если тип не найден — инструмент покажет понятную ошибку и попросит загрузить семейство вручную.

## Настройка правил (JSON)

Файл:

* `EOMTemplateTools.extension/config/rules.default.json`

Пример:

```json
{
  "comment_tag": "AUTO_EOM",
  "light_center_room_height_mm": 2700,
  "family_type_names": {
    "light_ceiling_point": "EOM_Light_Ceiling_Point : Type 01"
  }
}
```

Пояснения:

* `comment_tag` — префикс для Comments (по умолчанию `AUTO_EOM`).
* `light_center_room_height_mm` — добавочный Z-offset (мм) к центру комнаты.
* `family_type_names.light_ceiling_point` — строка `Family : Type` для поиска FamilySymbol.

## Troubleshooting

### Линк не найден / пустой список

* Проверь, что AR действительно подключён как Revit Link в текущем EOM документе.
* Запусти **Diagnostics: List AR Links**.

### Линк есть, но `Loaded = NO`

* Manage Links → Reload.
* После загрузки повтори запуск.

### Rooms не видны / Rooms = 0

* В AR должны быть реально размещённые Rooms.
* Иногда Rooms могут быть в другом Phase/Design Option — это уже особенности проекта.

### Смещение/поворот при размещении

* Это почти всегда вопрос координат (Project Base Point / Shared Coordinates).
* Смотри Transform в Diagnostics: `Origin` и `Basis*`.
* Если Transform не тот — проверь настройки позиционирования линка (Shared / Origin-to-Origin / etc.).

### Светильник не ставится (ошибка типа)

* Убедись, что в EOM загружено семейство и существует нужный **тип**.
* Проверь совпадение имени в `rules.default.json`.

### Разная высота (Levels)

* В демо-инструменте Z формируется как `room_center.Z + offset_mm`.
* Если нужно «по уровню помещения» или «до потолка» — это следующий шаг развития правил.

## Безопасность

* Скрипты работают только в активном документе.
* Связанный документ (`link_doc`) **не редактируется**.
