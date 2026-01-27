# -*- coding: utf-8 -*-

from pyrevit import revit
from pyrevit import script

import link_reader
from utils_units import ft_to_mm


doc = revit.doc
output = script.get_output()
logger = script.get_logger()


def _fmt_xyz(pt):
    if pt is None:
        return '-'
    return '({0:.3f}, {1:.3f}, {2:.3f}) ft  |  ({3:.0f}, {4:.0f}, {5:.0f}) mm'.format(
        pt.X, pt.Y, pt.Z,
        ft_to_mm(pt.X), ft_to_mm(pt.Y), ft_to_mm(pt.Z)
    )


def _fmt_basis(v):
    if v is None:
        return '-'
    return '({0:.6f}, {1:.6f}, {2:.6f})'.format(v.X, v.Y, v.Z)


links = link_reader.list_link_instances(doc)

output.print_md('# Diagnostics: List AR Links')
output.print_md('Active document: `{0}`'.format(doc.Title))

if not links:
    output.print_md('**No Revit links found in this document.**')
    script.exit()

output.print_md('Found **{0}** link instance(s).'.format(len(links)))

for idx, ln in enumerate(sorted(links, key=lambda x: (x.Name or '').lower())):
    loaded = link_reader.is_link_loaded(ln)
    path = link_reader.try_get_link_path(doc, ln)
    t = link_reader.get_total_transform(ln)
    origin = t.Origin if t else None

    output.print_md('---')
    output.print_md('## {0}. {1}'.format(idx + 1, ln.Name))
    output.print_md('* Loaded: **{0}**'.format('YES' if loaded else 'NO'))
    output.print_md('* Path: `{0}`'.format(path if path else 'N/A'))

    output.print_md('### Transform (link -> host)')
    output.print_md('* Origin: `{0}`'.format(_fmt_xyz(origin)))
    output.print_md('* BasisX: `{0}`'.format(_fmt_basis(t.BasisX)))
    output.print_md('* BasisY: `{0}`'.format(_fmt_basis(t.BasisY)))
    output.print_md('* BasisZ: `{0}`'.format(_fmt_basis(t.BasisZ)))

logger.info('Listed %s link(s)', len(links))
