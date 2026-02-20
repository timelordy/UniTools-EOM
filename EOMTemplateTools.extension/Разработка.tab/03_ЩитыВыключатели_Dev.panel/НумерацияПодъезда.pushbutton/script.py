# -*- coding: utf-8 -*-
"""
Нумерация подъезда - Размещение распаячных коробок возле входов в блок-секции.

Автоматически находит входы в каждую БС из связанной АР модели и размещает 
распаячные коробки для организации системы нумерации подъездов.

Стандарт: СП 256.1325800.2016 - высота установки щитков и коробок наружных сетей.
"""

from pyrevit import DB, revit, script

import config_loader
import link_reader
import placement_engine
import entrance_numbering_utils as entrance_utils

from utils_revit import alert, ensure_symbol_active, tx, set_comments, set_mark
from utils_units import mm_to_ft
from time_savings import report_time_saved


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()
logger = script.get_logger()


# Константы для размещения по ГОСТу
COMMENT_TAG = u"AUTO_EOM:ENTRANCE_NUMBERING"
TIME_PER_ENTRANCE_MIN = 10  # Норматив времени на один вход


def _get_user_config():
    """Получить сохраненную конфигурацию пользователя."""
    try:
        return script.get_config()
    except Exception:
        return None


def _save_user_config():
    """Сохранить конфигурацию пользователя."""
    try:
        script.save_config()
        return True
    except Exception:
        return False


def _load_symbol_from_saved_unique_id(doc, cfg, key):
    """Загрузить FamilySymbol из сохраненного UniqueId."""
    if doc is None or cfg is None:
        return None
    try:
        uid = getattr(cfg, key, None)
        if not uid:
            return None
        e = doc.GetElement(str(uid))
        if e and isinstance(e, DB.FamilySymbol):
            return e
    except Exception:
        return None
    return None


def _store_symbol_unique_id(cfg, key, symbol):
    """Сохранить UniqueId символа в конфигурацию."""
    if cfg is None or symbol is None:
        return
    try:
        setattr(cfg, key, str(symbol.UniqueId))
    except Exception:
        pass


def _pick_box_symbol_interactive(doc):
    """
    Интерактивный выбор типа распаячной коробки.
    
    Сначала пытается найти по правилам из config, потом предлагает выбрать вручную.
    """
    cfg = config_loader.load_rules()
    box_type_candidates = cfg.get('family_type_names', {}).get('entrance_numbering_box', [])
    
    # Преобразуем в список если это строка
    if isinstance(box_type_candidates, basestring):
        box_type_candidates = [box_type_candidates]
    
    # Пытаемся найти по названию из конфига
    for candidate in box_type_candidates:
        found = placement_engine.find_symbol_by_formatted_name(doc, candidate)
        if found:
            output.print_md(u"✓ Найден тип коробки: **{}**".format(
                placement_engine.format_family_type(found)
            ))
            return found
    
    # Не нашли - предлагаем выбрать
    output.print_md(u"⚠ Не найден тип распаячной коробки из конфигурации.")
    output.print_md(u"Ожидаемые названия: {}".format(u", ".join(box_type_candidates)))
    output.print_md(u"\n**Выберите существующий экземпляр распаячной коробки в модели...**")
    
    try:
        from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
        
        class ElectricalEquipmentFilter(ISelectionFilter):
            def AllowElement(self, elem):
                try:
                    return elem.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_ElectricalEquipment)
                except Exception:
                    return False
            def AllowReference(self, ref, pt):
                return False
        
        ref = uidoc.Selection.PickObject(
            ObjectType.Element,
            ElectricalEquipmentFilter(),
            u"Выберите экземпляр распаячной коробки"
        )
        if ref:
            elem = doc.GetElement(ref)
            return elem.Symbol if elem else None
    except Exception as e:
        logger.warning(u"Ошибка выбора: {}".format(e))
        return None


def _calculate_box_placement_point(entrance_info, rules):
    """
    Рассчитывает точку размещения распаячной коробки относительно входной двери.
    
    Правила размещения:
    - Высота: 2200 мм от уровня (параметр из rules)
    - Справа от двери: 250 мм от проема (параметр из rules)
    
    Args:
        entrance_info (dict): Информация о входе от entrance_utils.is_bs_entrance_door()
        rules (dict): Конфигурация из rules.default.json
    
    Returns:
        DB.XYZ: Точка размещения коробки
    """
    door_location = entrance_info['location']
    
    # Получаем параметры из конфига
    height_mm = rules.get('entrance_numbering_box_height_mm', 2200)
    offset_mm = rules.get('entrance_numbering_box_offset_mm', 250)
    
    # Преобразуем в feet
    height_ft = mm_to_ft(height_mm)
    offset_ft = mm_to_ft(offset_mm)
    
    # Базовая точка - координаты двери + смещение вправо + высота
    # Упрощенная логика: смещаем вправо по X
    placement_point = DB.XYZ(
        door_location.X + offset_ft,
        door_location.Y,
        door_location.Z + height_ft
    )
    
    return placement_point


def _check_existing_box_nearby(doc, point, dedupe_radius_mm):
    """
    Проверяет наличие уже размещенных коробок в радиусе dedupe_radius_mm.
    
    Args:
        doc (DB.Document): Документ Revit
        point (DB.XYZ): Точка для проверки
        dedupe_radius_mm (float): Радиус дедупликации в мм
    
    Returns:
        bool: True если есть коробка рядом, False если нет
    """
    dedupe_ft = mm_to_ft(dedupe_radius_mm)
    
    try:
        collector = DB.FilteredElementCollector(doc)\
            .OfCategory(DB.BuiltInCategory.OST_ElectricalEquipment)\
            .WhereElementIsNotElementType()
        
        for elem in collector:
            # Проверяем Comments на наличие тега
            comments_param = elem.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if comments_param:
                comments = comments_param.AsString() or u''
                if COMMENT_TAG in comments:
                    # Это наша коробка - проверяем расстояние
                    elem_location = elem.Location
                    if isinstance(elem_location, DB.LocationPoint):
                        elem_point = elem_location.Point
                        distance = point.DistanceTo(elem_point)
                        if distance < dedupe_ft:
                            return True
    except Exception:
        pass
    
    return False


def _get_all_levels(doc):
    """Возвращает список уровней документа."""
    try:
        return list(DB.FilteredElementCollector(doc).OfClass(DB.Level))
    except Exception:
        return []


def _resolve_placement_level(doc, entrance_info, fallback_point=None):
    """Определяет уровень для размещения, привязываясь к этажу двери."""
    levels = _get_all_levels(doc)
    if not levels:
        return None

    # 1) Прямое совпадение по level_id, если он известен.
    level_id_value = entrance_info.get('level_id')
    if level_id_value is not None:
        try:
            target_id = int(level_id_value)
        except Exception:
            target_id = None
        if target_id is not None and target_id >= 0:
            for lv in levels:
                try:
                    if int(lv.Id.IntegerValue) == target_id:
                        return lv
                except Exception:
                    continue

    # 2) Совпадение по имени уровня.
    level_name = entrance_info.get('level_name', u'')
    if level_name:
        for lv in levels:
            try:
                if lv.Name == level_name:
                    return lv
            except Exception:
                continue

    # 3) Fallback: ближайший уровень к базовой отметке двери (без +высоты установки).
    base_z = None
    location = entrance_info.get('location')
    if location is not None:
        try:
            base_z = float(location.Z)
        except Exception:
            base_z = None

    if base_z is None:
        level_elevation = entrance_info.get('level_elevation')
        try:
            base_z = float(level_elevation)
        except Exception:
            base_z = None

    if base_z is None and fallback_point is not None:
        try:
            base_z = float(fallback_point.Z)
        except Exception:
            base_z = None

    if base_z is not None:
        try:
            return min(levels, key=lambda lv: abs(float(lv.Elevation) - base_z))
        except Exception:
            pass

    return levels[0]


def _set_instance_target_elevation(doc, instance, target_z_ft):
    """
    Явно задает отметку экземпляра от уровня.

    В некоторых семействах OneLevelBased API может игнорировать Z точки при создании.
    """
    if instance is None or target_z_ft is None:
        return

    try:
        level_id = getattr(instance, 'LevelId', None)
        if not level_id or level_id == DB.ElementId.InvalidElementId:
            return
        level = doc.GetElement(level_id)
        if level is None:
            return
        level_z_ft = float(level.Elevation)
    except Exception:
        return

    try:
        offset_ft = float(target_z_ft) - float(level_z_ft)
    except Exception:
        return

    set_ok = False

    # Стандартный встроенный параметр.
    try:
        p = instance.get_Parameter(DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM)
        if p and (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
            p.Set(offset_ft)
            set_ok = True
    except Exception:
        set_ok = False

    # Локализованные/типовые имена параметра.
    if not set_ok:
        for param_name in (
            u'Отметка от уровня',
            u'Смещение от уровня',
            u'Elevation from Level',
            u'Offset from Level',
        ):
            try:
                p = instance.LookupParameter(param_name)
                if p and (not p.IsReadOnly) and p.StorageType == DB.StorageType.Double:
                    p.Set(offset_ft)
                    set_ok = True
                    break
            except Exception:
                continue

    # Последний fallback: двигаем элемент по Z.
    if not set_ok:
        try:
            location = instance.Location
            if isinstance(location, DB.LocationPoint):
                current_z = float(location.Point.Z)
                dz = float(target_z_ft) - current_z
                if abs(dz) > 1e-6:
                    DB.ElementTransformUtils.MoveElement(doc, instance.Id, DB.XYZ(0.0, 0.0, dz))
        except Exception:
            pass


def _place_box_at_entrance(doc, box_symbol, entrance_info, rules):
    """
    Размещает распаячную коробку у входа в БС.
    
    Args:
        doc (DB.Document): Документ Revit
        box_symbol (DB.FamilySymbol): Тип распаячной коробки
        entrance_info (dict): Информация о входе
        rules (dict): Конфигурация
    
    Returns:
        DB.FamilyInstance or None: Размещенный экземпляр или None при ошибке
    """
    try:
        # Рассчитываем точку размещения
        placement_point = _calculate_box_placement_point(entrance_info, rules)
        
        # Проверяем дедупликацию
        dedupe_mm = rules.get('entrance_numbering_box_dedupe_mm', 500)
        if _check_existing_box_nearby(doc, placement_point, dedupe_mm):
            logger.info(u"Пропуск: коробка уже есть рядом с входом БС{}".format(
                entrance_info['bs_number']
            ))
            return None
        
        # Убедимся что символ активен
        ensure_symbol_active(box_symbol)
        
        # Размещаем коробку:
        # выбираем уровень по этажу двери, а не по точке с +2200 мм.
        level = _resolve_placement_level(doc, entrance_info, fallback_point=placement_point)
        if not level:
            logger.error(u"Не найден уровень для размещения коробки")
            return None
        
        # Создаем экземпляр
        instance = doc.Create.NewFamilyInstance(
            placement_point,
            box_symbol,
            level,
            DB.Structure.StructuralType.NonStructural
        )
        
        if instance:
            # Явно выставляем целевую отметку относительно выбранного уровня.
            _set_instance_target_elevation(doc, instance, placement_point.Z)

            # Записываем параметры
            bs_number = entrance_info['bs_number']
            comment_text = u"{} БС{}".format(COMMENT_TAG, bs_number)
            set_comments(instance, comment_text)
            
            # Пытаемся записать Mark
            try:
                set_mark(instance, u"БС{}".format(bs_number))
            except Exception:
                pass  # Mark может быть недоступен
            
            return instance
            
    except Exception as e:
        logger.error(u"Ошибка размещения коробки: {}".format(e))
        return None


def main():
    """Главная функция скрипта."""
    
    output.print_md('# Нумерация подъезда - Распаячные коробки')
    output.print_md('---')
    
    # Загружаем правила
    try:
        rules = config_loader.load_rules()
    except Exception as e:
        alert(u"Ошибка загрузки конфигурации: {}".format(e))
        return
    
    # Шаг 1: Выбор связанных АР моделей + уровней
    output.print_md('## Шаг 1: Выбор связей и уровней')
    try:
        selected_pairs = link_reader.select_link_level_pairs(
            doc,
            link_title=u'Выберите связь(и) АР',
            level_title=u'Выберите уровни для обработки',
            default_all_links=True,
            default_all_levels=False,
            loaded_only=True
        )
        if not selected_pairs:
            output.print_md(u"⚠ **Отменено: не выбраны связи/уровни**")
            return
    except Exception as e:
        alert(u"Ошибка при выборе связей/уровней: {}".format(e))
        logger.exception(e)
        return

    # Шаг 2: Поиск входов в БС
    output.print_md('## Шаг 2: Поиск входов в блок-секции')
    main_entrances = []
    try:
        for pair in selected_pairs:
            link_inst = pair.get('link_instance')
            link_doc = pair.get('link_doc')
            link_transform = pair.get('transform')
            levels = list(pair.get('levels') or [])
            if link_inst is None or link_doc is None or not levels:
                continue

            try:
                link_name = link_inst.Name
            except Exception:
                link_name = u'<Связь>'

            selected_level_ids = set()
            for lvl in levels:
                try:
                    selected_level_ids.add(int(lvl.Id.IntegerValue))
                except Exception:
                    continue
            if not selected_level_ids:
                continue

            output.print_md(u"\n### Связь: **{}**".format(link_name))
            entrances = entrance_utils.find_bs_entrance_doors(link_doc, link_transform)
            if not entrances:
                output.print_md(u"⚠ В этой связи входы в БС не найдены")
                continue

            filtered_entrances = []
            for entrance in entrances:
                try:
                    level_id = entrance.get('level_id')
                    if level_id is None:
                        continue
                    if int(level_id) not in selected_level_ids:
                        continue
                except Exception:
                    continue
                filtered_entrances.append(entrance)

            if not filtered_entrances:
                output.print_md(u"⚠ На выбранных уровнях входы не найдены")
                continue

            output.print_md(u"✓ Найдено входов на выбранных уровнях: **{}**".format(len(filtered_entrances)))

            grouped = entrance_utils.group_entrances_by_bs(filtered_entrances)
            output.print_md(u"Распределение по блок-секциям:")
            for bs_num in sorted(grouped.keys()):
                bs_entrances = grouped[bs_num]
                output.print_md(u"- **БС{}**: {} вход(ов)".format(bs_num, len(bs_entrances)))

            for bs_num in sorted(grouped.keys()):
                bs_entrances = grouped[bs_num]
                main = entrance_utils.select_main_entrance_per_level(bs_entrances)
                main_entrances.extend(main)

        if not main_entrances:
            output.print_md(u"⚠ **Не найдено входов на выбранных связях/уровнях**")
            return

        output.print_md(u"\n✓ Отобрано основных входов для размещения: **{}**".format(len(main_entrances)))
    except Exception as e:
        alert(u"Ошибка поиска входов в БС: {}".format(e))
        logger.exception(e)
        return
    
    # Шаг 3: Выбор типа распаячной коробки
    output.print_md('## Шаг 3: Выбор типа распаячной коробки')
    
    user_cfg = _get_user_config()
    box_symbol = _load_symbol_from_saved_unique_id(doc, user_cfg, 'entrance_box_symbol_uid')
    
    if not box_symbol:
        box_symbol = _pick_box_symbol_interactive(doc)
        if not box_symbol:
            alert(u"Не выбран тип распаячной коробки!\n\n"
                  u"Пожалуйста, загрузите семейство распаячной коробки в проект.")
            return
        
        # Сохраняем выбор
        if user_cfg is None:
            user_cfg = script.get_config()
        _store_symbol_unique_id(user_cfg, 'entrance_box_symbol_uid', box_symbol)
        _save_user_config()
    else:
        output.print_md(u"✓ Используется сохраненный тип: **{}**".format(
            placement_engine.format_family_type(box_symbol)
        ))
    
    # Шаг 4: Превью и подтверждение
    output.print_md('## Шаг 4: Превью размещения')
    output.print_md(u"\nБудет размещено коробок: **{}**".format(len(main_entrances)))
    output.print_md(u"\nПараметры размещения:")
    output.print_md(u"- Высота: **{} мм** от уровня".format(
        rules.get('entrance_numbering_box_height_mm', 2200)
    ))
    output.print_md(u"- Смещение от двери: **{} мм**".format(
        rules.get('entrance_numbering_box_offset_mm', 250)
    ))
    output.print_md(u"- Радиус дедупликации: **{} мм**".format(
        rules.get('entrance_numbering_box_dedupe_mm', 500)
    ))
    
    output.print_md(u"\n### Список входов для размещения:")
    for entrance in main_entrances:
        output.print_md(u"- **БС{}** на уровне *{}*: {} ({} ↔ {})".format(
            entrance['bs_number'],
            entrance['level_name'],
            entrance['door_type'],
            entrance.get('from_room', u'?'),
            entrance.get('to_room', u'?')
        ))
    
    # Шаг 5: Размещение
    output.print_md('## Шаг 5: Размещение коробок')
    
    placed_count = 0
    skipped_count = 0
    error_count = 0
    
    placed_details = []
    skipped_details = []
    
    try:
        with tx('ЭОМ: Разместить распаячные коробки для нумерации подъездов', doc=doc, swallow_warnings=True):
            for entrance in main_entrances:
                result = _place_box_at_entrance(doc, box_symbol, entrance, rules)
                
                if result:
                    placed_count += 1
                    placed_details.append({
                        'bs': entrance['bs_number'],
                        'level': entrance['level_name'],
                        'door_type': entrance['door_type']
                    })
                else:
                    # Проверяем причину
                    placement_point = _calculate_box_placement_point(entrance, rules)
                    dedupe_mm = rules.get('entrance_numbering_box_dedupe_mm', 500)
                    
                    if _check_existing_box_nearby(doc, placement_point, dedupe_mm):
                        skipped_count += 1
                        skipped_details.append({
                            'bs': entrance['bs_number'],
                            'level': entrance['level_name'],
                            'reason': u'Уже есть коробка рядом'
                        })
                    else:
                        error_count += 1
                        skipped_details.append({
                            'bs': entrance['bs_number'],
                            'level': entrance['level_name'],
                            'reason': u'Ошибка размещения'
                        })
        
        output.print_md(u"\n---")
        output.print_md(u"## ✅ Результаты")
        output.print_md(u"- **Размещено коробок:** {}".format(placed_count))
        output.print_md(u"- **Пропущено (дубликаты):** {}".format(skipped_count))
        output.print_md(u"- **Ошибки:** {}".format(error_count))
        
        if placed_details:
            output.print_md(u"\n### Размещенные коробки:")
            for detail in placed_details:
                output.print_md(u"- БС{} на {} ({})".format(
                    detail['bs'], detail['level'], detail['door_type']
                ))
        
        if skipped_details:
            output.print_md(u"\n### Пропущенные:")
            for detail in skipped_details:
                output.print_md(u"- БС{} на {}: {}".format(
                    detail['bs'], detail['level'], detail['reason']
                ))
        
        # Отчет об экономии времени
        if placed_count > 0:
            output.print_md(u"\n---")
            report_time_saved(
                count=placed_count,
                minutes_per_item=TIME_PER_ENTRANCE_MIN,
                task_name=u"размещение распаячных коробок для нумерации подъездов"
            )

        try:
            total_time = placed_count * TIME_PER_ENTRANCE_MIN
            global EOM_HUB_RESULT
            EOM_HUB_RESULT = {
                'stats': {'total': placed_count, 'processed': placed_count, 'failed': error_count, 'skipped': skipped_count},
                'time_saved_minutes': total_time,
                'placed': placed_count
            }
        except Exception:
            pass
        
    except Exception as e:
        alert(u"Ошибка при размещении коробок: {}".format(e))
        logger.exception(e)
        return


if __name__ == '__main__':
    main()
