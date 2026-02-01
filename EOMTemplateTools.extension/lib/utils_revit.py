# -*- coding: utf-8 -*-

import traceback

from pyrevit import DB
from pyrevit import forms
from pyrevit import revit
from pyrevit import script


def get_output():
    return script.get_output()


def get_logger():
    return script.get_logger()


def _safe_log(logger_method, msg):
    try:
        logger_method(msg)
    except UnicodeEncodeError:
        try:
            # Fallback to repr which escapes non-ascii
            logger_method(repr(msg))
        except Exception:
            logger_method("<Log message encoding failed>")
    except Exception:
        pass


def alert(msg, title='EOM Template Tools', warn_icon=True):
    try:
        forms.alert(msg, title=title, warn_icon=warn_icon)
    except Exception:
        # As a last resort if UI is unavailable
        _safe_log(get_logger().warning, msg)


def log_exception(prefix='Error'):
    logger = get_logger()
    _safe_log(logger.error, prefix)
    _safe_log(logger.error, traceback.format_exc())


def trace(msg, filename='EOMTemplateTools.trace.log'):
    """Write breadcrumb to a local file.

    Use this when Revit crashes hard before pyRevit output is flushed.
    """
    return


def safe_str(obj):
    try:
        return str(obj)
    except Exception:
        try:
            return repr(obj)
        except Exception:
            return '<unprintable>'


def find_nearest_level(doc, z_ft):
    """Return nearest Level by elevation to given Z (feet)."""
    from pyrevit import DB

    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements())
    if not levels:
        return None
    best = None
    best_d = None
    for lvl in levels:
        try:
            d = abs(float(lvl.Elevation) - float(z_ft))
            if best is None or d < best_d:
                best = lvl
                best_d = d
        except Exception:
            continue
    return best


def ensure_symbol_active(doc, family_symbol):
    if family_symbol is None:
        return
    try:
        if not family_symbol.IsActive:
            family_symbol.Activate()
            doc.Regenerate()
    except Exception:
        # Some types don't expose IsActive/Activate reliably
        pass


def get_param(elem, name):
    if elem is None or not name:
        return None
    try:
        return elem.LookupParameter(name)
    except Exception:
        return None


def set_string_param(elem, param_name, value):
    p = get_param(elem, param_name)
    if p is None:
        return False
    try:
        if p.IsReadOnly:
            return False
        p.Set(str(value) if value is not None else '')
        return True
    except Exception:
        return False


def set_comments(elem, value):
    from pyrevit import DB

    if elem is None:
        return False

    # Prefer built-in parameter if available
    try:
        p = elem.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if p and (not p.IsReadOnly):
            p.Set(str(value) if value is not None else '')
            return True
    except Exception:
        pass

    # Fallback by name
    if set_string_param(elem, 'Comments', value):
        return True
    if set_string_param(elem, u'\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0438', value):
        return True
    return set_mark(elem, value)


def set_mark(elem, value):
    from pyrevit import DB

    if elem is None:
        return False

    try:
        p = elem.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if p and (not p.IsReadOnly):
            p.Set(str(value) if value is not None else '')
            return True
    except Exception:
        pass

    return set_string_param(elem, 'Mark', value)


def tx(name, doc=None, swallow_warnings=False):
    """Transaction context manager.

    Usage:
        with tx('My Tool'):
            ...
    """
    doc = doc or revit.doc
    t = DB.Transaction(doc, name)

    preproc = None
    if swallow_warnings:
        try:
            class _WarningsPreprocessor(DB.IFailuresPreprocessor):
                def PreprocessFailures(self, failuresAccessor):
                    try:
                        msgs = failuresAccessor.GetFailureMessages()
                        for m in msgs:
                            try:
                                if m.GetSeverity() == DB.FailureSeverity.Warning:
                                    failuresAccessor.DeleteWarning(m)
                            except Exception:
                                continue
                    except Exception:
                        pass
                    return DB.FailureProcessingResult.Continue

            preproc = _WarningsPreprocessor()
        except Exception:
            preproc = None

    class _Tx(object):
        def __enter__(self):
            t.Start()
            if preproc is not None:
                try:
                    opts = t.GetFailureHandlingOptions()
                    opts = opts.SetFailuresPreprocessor(preproc)
                    try:
                        opts = opts.SetClearAfterRollback(True)
                    except Exception:
                        pass
                    t.SetFailureHandlingOptions(opts)
                except Exception:
                    pass
            return t

        def __exit__(self, exc_type, exc, tb):
            if exc_type:
                rb = getattr(t, 'Rollback', None) or getattr(t, 'RollBack', None)
                if rb:
                    try:
                        rb()
                    except Exception:
                        pass
                return False

            try:
                t.Commit()
            except Exception:
                # Last resort rollback
                rb = getattr(t, 'Rollback', None) or getattr(t, 'RollBack', None)
                if rb:
                    try:
                        rb()
                    except Exception:
                        pass
                raise
            return False

    return _Tx()
