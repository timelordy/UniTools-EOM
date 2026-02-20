# -*- coding: utf-8 -*-

"""Entry point for SHHE niches tool."""

from utils_revit import alert, log_exception
import link_reader
import magic_context


def main():
    import script_impl
    from pyrevit import revit, script as pyrevit_script

    doc = revit.doc
    output = pyrevit_script.get_output()
    pairs = link_reader.select_link_level_pairs(
        doc,
        link_title=u'Выберите связь(и) АР',
        level_title=u'Выберите уровни для ЩЭ в нишах',
        default_all_links=True,
        default_all_levels=False,
        loaded_only=True
    )
    if not pairs:
        output.print_md('**Отменено (связи/уровни не выбраны).**')
        return

    old_force = bool(getattr(magic_context, 'FORCE_SELECTION', False))
    old_link = getattr(magic_context, 'SELECTED_LINK', None)
    old_links = list(getattr(magic_context, 'SELECTED_LINKS', []) or [])
    old_levels = list(getattr(magic_context, 'SELECTED_LEVELS', []) or [])
    try:
        for pair in pairs:
            link_inst = pair.get('link_instance')
            levels = list(pair.get('levels') or [])
            if link_inst is None or not levels:
                continue

            try:
                link_name = link_inst.Name
            except Exception:
                link_name = u'<Связь>'
            output.print_md(u'## Обработка связи: `{0}`'.format(link_name))

            magic_context.FORCE_SELECTION = True
            magic_context.SELECTED_LINK = link_inst
            magic_context.SELECTED_LINKS = [link_inst]
            magic_context.SELECTED_LEVELS = levels

            script_impl.main()
    finally:
        magic_context.FORCE_SELECTION = old_force
        magic_context.SELECTED_LINK = old_link
        magic_context.SELECTED_LINKS = old_links
        magic_context.SELECTED_LEVELS = old_levels


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
        alert('Error. Details in pyRevit Output. TRACE: {}'.format(trace_path))
    else:
        alert('Error. Details in pyRevit Output.')
