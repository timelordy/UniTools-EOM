# -*- coding: utf-8 -*-

import re

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script

import config_loader
from utils_revit import alert, log_exception, tx


doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()


def _norm(s):
    try:
        return (s or u'').strip().lower()
    except Exception:
        return u''


def _norm_key(s):
    t = _norm(s)
    if not t:
        return t
    try:
        for ch in (u'–', u'—', u'‑', u'−'):
            t = t.replace(ch, u'-')
    except Exception:
        pass
    try:
        t = u' '.join(t.split())
    except Exception:
        pass
    return t


def _is_module_param_name(pname):
    n = _norm_key(pname)
    if not n:
        return False
    if (u'модул' not in n) and ('module' not in n) and ('modul' not in n):
        return False
    try:
        return re.search(u'(-\s*\d{1,3}\b)|(\b\d{1,3}\b)', n) is not None
    except Exception:
        return True


def _set_only_desired_module_variant(symbol, desired_param_name):
    if symbol is None or not desired_param_name:
        return 0, 0

    desired_key = _norm_key(desired_param_name)
    if not desired_key:
        return 0, 0

    total = 0
    changed = 0
    for p in getattr(symbol, 'Parameters', []) or []:
        try:
            d = getattr(p, 'Definition', None)
            pname = getattr(d, 'Name', None) if d is not None else None
        except Exception:
            pname = None
        if not pname:
            continue
        if not _is_module_param_name(pname):
            continue
        try:
            if p.StorageType != DB.StorageType.Integer:
                continue
        except Exception:
            continue

        total += 1
        try:
            if p.IsReadOnly:
                continue
        except Exception:
            pass

        val = 1 if _norm_key(pname) == desired_key else 0
        try:
            cur = int(p.AsInteger() or 0)
        except Exception:
            cur = None
        if cur is None or cur != int(val):
            try:
                p.Set(int(val))
                changed += 1
            except Exception:
                pass

    return total, changed


def _collect_instances_by_comments_substring(substr):
    if not substr:
        return []

    try:
        provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS))
        evaluator = DB.FilterStringContains()
        try:
            rule = DB.FilterStringRule(provider, evaluator, substr, False)
        except Exception:
            rule = DB.FilterStringRule(provider, evaluator, substr)

        pfilter = DB.ElementParameterFilter(rule)
        col = (DB.FilteredElementCollector(doc)
               .WhereElementIsNotElementType()
               .WherePasses(pfilter))

        res = []
        for e in col:
            try:
                if isinstance(e, DB.FamilyInstance):
                    res.append(e)
            except Exception:
                continue
        return res
    except Exception:
        return []


def _collect_symbols_with_param(param_name, scan_limit=20000):
    if not param_name:
        return {}
    res = {}
    try:
        col = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
        i = 0
        for sym in col:
            i += 1
            if scan_limit and i > int(scan_limit):
                break
            try:
                if sym.LookupParameter(param_name) is not None:
                    res[int(sym.Id.IntegerValue)] = sym
            except Exception:
                continue
    except Exception:
        return {}
    return res


def _pick_any_family_instance():
    from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType

    class InstFilter(ISelectionFilter):
        def AllowElement(self, elem):
            try:
                return isinstance(elem, DB.FamilyInstance)
            except Exception:
                return False

        def AllowReference(self, reference, position):
            return False

    try:
        r = uidoc.Selection.PickObject(ObjectType.Element, InstFilter(), 'Выберите размещённый щит ШК')
    except Exception:
        return None

    try:
        return doc.GetElement(r.ElementId)
    except Exception:
        return None


def main():
    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    comment_value = '{0}:PANEL_SHK'.format(comment_tag)
    desired = (rules.get('panel_shk_variant_param', '') or '').strip()
    if not desired:
        desired = u'Бокс ЩРВ-П-18 модулей навесной пластик IP41 LIGHT IEK'

    output.print_md('# Fix: ShK 18 modules only')
    output.print_md('Документ: `{0}`'.format(doc.Title))
    output.print_md('Целевой параметр: `{0}`'.format(desired))

    # Prefer robust approach: find ALL types that have the desired module parameter.
    # This works even if panels were placed manually (no Comments tag).
    symbols = _collect_symbols_with_param(desired)

    # Fallback: try locate by Comments tag (only affects symbols actually used by EOM tool)
    insts = _collect_instances_by_comments_substring(comment_value)
    for inst in insts or []:
        try:
            sym = getattr(inst, 'Symbol', None)
        except Exception:
            sym = None
        if sym is None:
            continue
        try:
            symbols[int(sym.Id.IntegerValue)] = sym
        except Exception:
            pass

    # Last resort: user picks an instance
    use_selection = False
    if not symbols:
        use_selection = True
        output.print_md('Не удалось найти типы автоматически. Выберите один щит вручную.')
        inst = _pick_any_family_instance()
        if inst is None:
            return
        try:
            sym = getattr(inst, 'Symbol', None)
        except Exception:
            sym = None
        if sym is None:
            alert('Не удалось определить тип семейства для выбранного элемента.')
            return
        try:
            symbols[int(sym.Id.IntegerValue)] = sym
        except Exception:
            pass

    if not symbols:
        alert('Не найдено ни одного типа, который содержит параметр варианта (модулей).')
        return

    try:
        go = forms.alert(
            'Найдено типов для исправления: {0}\n\nСделать только "18 модулей" (а остальные выключить)?'.format(len(symbols)),
            title='Fix: ShK 18 modules only',
            warn_icon=False,
            yes=True,
            no=True
        )
    except Exception:
        go = True
    if not go:
        return

    updated_syms = 0
    total_params = 0
    changed_params = 0
    with tx('ЭОМ: Fix ShK (18 modules only)', doc=doc, swallow_warnings=True):
        for sid, sym in symbols.items():
            tcnt, ccnt = _set_only_desired_module_variant(sym, desired)
            total_params += int(tcnt)
            changed_params += int(ccnt)
            if ccnt:
                updated_syms += 1

        try:
            doc.Regenerate()
        except Exception:
            pass

    output.print_md('---')
    output.print_md('Типов обработано: **{0}**'.format(len(symbols)))
    output.print_md('Типов изменено: **{0}**'.format(updated_syms))
    output.print_md('Параметров "модул*" найдено: **{0}**'.format(total_params))
    output.print_md('Параметров изменено: **{0}**'.format(changed_params))
    if use_selection:
        output.print_md('_Режим: по выбранному щиту (по тегу не нашли)._')

    try:
        forms.alert(
            'Готово.\n\nТипов обработано: {0}\nТипов изменено: {1}\nПараметров изменено: {2}'.format(len(symbols), updated_syms, changed_params),
            title='Fix: ShK 18 modules only',
            warn_icon=False
        )
    except Exception:
        pass


try:
    main()
except Exception:
    log_exception('Ошибка фикса щита ШК')
    alert('Ошибка. Подробности смотрите в выводе pyRevit.')
