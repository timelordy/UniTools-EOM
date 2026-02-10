# -*- coding: utf-8 -*-

"""ЩЭ в нишах (entrypoint for pyRevit/IronPython)."""

from utils_revit import alert, log_exception


def main():
    import script_impl
    script_impl.main()


def _dump_traceback_to_output(tb_text):
    try:
        from pyrevit import script as _pyrevit_script
        out = _pyrevit_script.get_output()
        out.print_md('## TRACEBACK')
        out.print_md('```')
        try:
            out.print_md(tb_text)
        except Exception:
            out.print_md(repr(tb_text))
        out.print_md('```')
    except Exception:
        pass


def _dump_traceback_to_tempfile(tb_text):
    try:
        import os
        import tempfile
        path = os.path.join(tempfile.gettempdir(), 'EOMTemplateTools-shhe-niches-error.txt')
        with open(path, 'wb') as handle:
            try:
                handle.write((tb_text or '').encode('utf-8', 'replace'))
            except Exception:
                handle.write(repr(tb_text).encode('utf-8', 'replace'))
        return path
    except Exception:
        return None


try:
    main()
except Exception:
    tb = '<traceback unavailable>'
    try:
        import traceback
        tb = traceback.format_exc()
    except Exception:
        pass

    _dump_traceback_to_output(tb)
    trace_path = _dump_traceback_to_tempfile(tb)

    log_exception('Error in SHHE niches script')
    if trace_path:
        alert(u'Ошибка. Подробности в pyRevit Output.\nTRACE: {}'.format(trace_path))
    else:
        alert(u'Ошибка. Подробности в pyRevit Output.')

