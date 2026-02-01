# -*- coding: utf-8 -*-
from pyrevit import forms

import config_loader
import link_reader
import placement_engine

from utils_revit import alert, trace, tx
from utils_units import mm_to_ft

try:
    import socket_utils as su
except ImportError:
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'lib'))
    import socket_utils as su

from adapters import (
    load_symbol_from_saved_id,
    load_symbol_from_saved_unique_id,
    store_symbol_id,
    store_symbol_unique_id,
)
from domain import get_user_config, save_user_config
from domain_points import dedupe_points, enforce_min_spacing
from domain_selection import norm
from domain_debug import points_debug_stats
from domain_revit import count_tagged_instances, collect_existing_tagged_points


def _room_text(room):
    try:
        return room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
    except Exception:
        return ''


def _chunks(seq, n):
    if not seq:
        return
    n = max(int(n or 1), 1)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def run_placement(doc, output, script_module):
    trace('PlaceLightsFromRooms: start')
    output.print_md('# Place: Light at Linked Room Centers (demo)')
    output.print_md('Host (EOM) document: `{0}`'.format(doc.Title))

    trace('Select link UI')
    link_inst = link_reader.select_link_instance_auto(doc)
    if link_inst is None:
        trace('No link found')
        output.print_md('**No link found.**')
        return

    trace('Selected link: {0}'.format(getattr(link_inst, 'Name', '<no name>')))
    if not link_reader.is_link_loaded(link_inst):
        alert('Selected link is not loaded. Load it in Manage Links and retry.')
        return

    trace('Get link_doc')
    link_doc = link_reader.get_link_doc(link_inst)
    if link_doc is None:
        alert('Could not access link document. Is the link loaded?')
        return

    output.print_md('Selected link: `{0}`'.format(link_inst.Name))

    trace('Load rules')
    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    height_mm = rules.get('light_center_room_height_mm', 2700)
    dedupe_mm = rules.get('dedupe_radius_mm', 500)
    max_place = int(rules.get('max_place_count', 200) or 200)
    batch_size = int(rules.get('batch_size', 25) or 25)
    scan_limit_rooms = int(rules.get('scan_limit_rooms', 500) or 500)
    enable_existing_dedupe = bool(rules.get('enable_existing_dedupe', False))
    # debug_section_half_height_mm = rules.get('debug_section_half_height_mm', 1500)
    exclude_room_name_keywords = rules.get('exclude_room_name_keywords', []) or []
    min_light_spacing_mm = rules.get('min_light_spacing_mm', 0) or 0
    min_light_wall_clearance_mm = rules.get('min_light_wall_clearance_mm', 300) or 300
    fam_fullname = (rules.get('family_type_names', {}) or {}).get('light_ceiling_point') or ''

    trace('Rules loaded: fam_fullname="{0}" max_place={1}'.format(fam_fullname, max_place))

    if fam_fullname:
        output.print_md('Configured target type (optional): `{0}`'.format(fam_fullname))

    # Select family type
    cfg = get_user_config(script_module)
    symbol = None

    trace('Try load symbol from saved unique id')
    symbol = load_symbol_from_saved_unique_id(doc, cfg, 'last_light_symbol_uid')
    if symbol is None:
        trace('Try load symbol from saved id')
        symbol = load_symbol_from_saved_id(doc, cfg, 'last_light_symbol_id')
    if symbol is not None:
        try:
            output.print_md('Using cached light type: `{0}`'.format(placement_engine.format_family_type(symbol)))
        except Exception:
            pass

    if symbol is None:
        # Need implementation of auto-pick or manual pick here
        # For now, simplistic fallback or alert
        alert('Не удалось автоматически выбрать тип светильника. Загрузите подходящее семейство.')
        return

    # Cache for next run
    try:
        store_symbol_id(cfg, 'last_light_symbol_id', symbol)
        store_symbol_unique_id(cfg, 'last_light_symbol_uid', symbol)
        save_user_config(script_module)
    except Exception:
        pass

    trace('Symbol selected: {0}'.format(placement_engine.format_family_type(symbol)))

    _report_symbol_geometry(symbol, output)

    trace('Collect rooms')
    # Auto-select all levels
    lvl = None
    level_id = None

    # Pick / infer host level to avoid placing on the wrong story (common cause of "nothing appears")
    host_level = None
    if lvl is not None:
        try:
            # match by name
            lname = (lvl.Name or '').strip().lower()
            for hl in link_reader.list_levels(doc):
                try:
                    if (hl.Name or '').strip().lower() == lname:
                        host_level = hl
                        break
                except Exception:
                    continue
        except Exception:
            host_level = None

    if host_level is None:
        host_level = link_reader.select_level(doc, title='Select HOST Level (where to place lights)', allow_none=True)

    if host_level is not None:
        output.print_md('Host level for placement: `{0}`'.format(host_level.Name))

    t = link_reader.get_total_transform(link_inst)
    z_off = mm_to_ft(height_mm) or 0.0
    dedupe_ft = mm_to_ft(dedupe_mm) or 0.0
    debug_hh_ft = mm_to_ft(rules.get('debug_section_half_height_mm', 1500)) or 0.0
    min_spacing_ft = mm_to_ft(min_light_spacing_mm) or 0.0
    min_wall_clear_ft = mm_to_ft(min_light_wall_clearance_mm) or 0.0

    trace('Compute points from rooms')
    points = []
    skipped_no_center = 0
    skipped_unplaced = 0
    skipped_excluded = 0
    c_boundary = 0
    c_location = 0
    c_bbox = 0
    processed = 0
    truncated = False
    pb_max = scan_limit_rooms if scan_limit_rooms > 0 else 500
    host_level_z = None
    try:
        host_level_z = float(host_level.Elevation) if host_level is not None else None
    except Exception:
        host_level_z = None

    placement_z = (host_level_z + z_off) if host_level_z is not None else None

    with forms.ProgressBar(title='EOM: Reading room centers', cancellable=True, step=1) as pb:
        pb.max_value = pb_max
        for r in link_reader.iter_rooms(link_doc, limit=scan_limit_rooms, level_id=level_id):
            processed += 1
            pb.update_progress(min(processed, pb_max), pb_max)
            if pb.cancelled:
                trace('Cancelled while computing room points')
                return

            # Skip unplaced / not-enclosed rooms
            try:
                if hasattr(r, 'Area') and float(r.Area) <= 0.0:
                    skipped_unplaced += 1
                    continue
            except Exception:
                pass

            # Skip niches/balconies/etc by room name keywords
            try:
                rt = norm(_room_text(r))
                excluded = False
                for kw in exclude_room_name_keywords:
                    nkw = norm(kw)
                    if nkw and (nkw in rt):
                        excluded = True
                        break
                if excluded:
                    skipped_excluded += 1
                    continue
            except Exception:
                pass

            c, m = link_reader.get_room_center_ex_safe(r, min_wall_clear_ft, return_method=True)
            if c is None:
                skipped_no_center += 1
                continue

            if m == 'boundary':
                c_boundary += 1
            elif m == 'location':
                c_location += 1
            elif m == 'bbox':
                c_bbox += 1

            host_c = t.OfPoint(c)
            z = (host_level_z + z_off) if host_level_z is not None else (host_c.Z + z_off)
            points.append(DB.XYZ(host_c.X, host_c.Y, z))

            # Hard cap to avoid freezing on huge models
            if max_place > 0 and len(points) >= max_place:
                truncated = True
                break

    if not points:
        alert('No valid room centers found.\n\nSkipped: unplaced={0}, no_center={1}'.format(skipped_unplaced, skipped_no_center))
        return

    comment_value = '{0}:LIGHT_FROM_LINK'.format(comment_tag)

    output.print_md('---')
    output.print_md('Rooms processed: **{0}**{1}'.format(processed, ' (level-filtered)' if lvl else ''))
    if skipped_unplaced:
        output.print_md('Skipped (unplaced/Area=0): **{0}**'.format(skipped_unplaced))
    if skipped_excluded:
        output.print_md('Skipped (excluded by name keywords): **{0}**'.format(skipped_excluded))
    if skipped_no_center:
        output.print_md('Skipped (no center): **{0}**'.format(skipped_no_center))
    output.print_md('Candidate placements: **{0}**'.format(len(points)))
    output.print_md('Center method counts: boundary={0}, location={1}, bbox={2}'.format(c_boundary, c_location, c_bbox))
    if truncated:
        output.print_md('**Note:** Reached max_place_count limit ({0}). Rerun tool for next batch or narrow the level.'.format(max_place))

    # Dedupe vs already placed AUTO_EOM lights
    existing_pts = []
    dedupe_mode = 'radius'

    try:
        existing_count = count_tagged_instances(doc, comment_value)
    except Exception:
        existing_count = 0

    if existing_count and (not enable_existing_dedupe):
        try:
            go = forms.alert(
                'Detected {0} existing placed lights with tag `{1}`.\n\n'
                'If you run again without dedupe, Revit will create duplicates.\n\n'
                'Enable safe dedupe for this run?'.format(existing_count, comment_value),
                title='EOM: Prevent duplicates',
                warn_icon=True,
                yes=True,
                no=True
            )
        except Exception:
            go = True

        if go:
            enable_existing_dedupe = True
            dedupe_mode = 'exact'
        else:
            dedupe_mode = 'radius'

    if enable_existing_dedupe:
        trace('Collect existing points for dedupe (count={0}, mode={1})'.format(existing_count, dedupe_mode))
        existing_pts = collect_existing_tagged_points(doc, comment_value)

    filtered_points, skipped_dedupe = dedupe_points(
        points,
        existing_pts,
        dedupe_ft,
        mode=dedupe_mode,
        key_step_mm=5
    )

    skipped_spacing = 0
    if min_spacing_ft > 0.0:
        filtered_points, skipped_spacing = enforce_min_spacing(filtered_points, min_spacing_ft)

    output.print_md('After dedupe ({0}mm): **{1}** to place, skipped **{2}**'.format(
        dedupe_mm, len(filtered_points), skipped_dedupe
    ))
    if min_spacing_ft > 0.0:
        output.print_md('Min spacing filter ({0}mm): kept **{1}**, skipped **{2}**'.format(
            int(min_light_spacing_mm), len(filtered_points), skipped_spacing
        ))
    if not filtered_points:
        output.print_md('Nothing to place.')
        return

    # Debug stats
    try:
        st = points_debug_stats(filtered_points)
        if st:
            min_pt = st['min']
            max_pt = st['max']
            range_x = max_pt[0] - min_pt[0]
            range_y = max_pt[1] - min_pt[1]
            output.print_md('Points bbox(ft): min=({0:.2f},{1:.2f},{2:.2f}) max=({3:.2f},{4:.2f},{5:.2f}) range_xy=({6:.2f},{7:.2f})'.format(
                min_pt[0], min_pt[1], min_pt[2],
                max_pt[0], max_pt[1], max_pt[2],
                range_x, range_y
            ))
            if range_x < 1.0 and range_y < 1.0:
                output.print_md('**Warning:** placement points are almost identical in XY.')
    except Exception:
        pass

    # Batch placement
    created_count = 0
    first_created_id = None
    created_ids = []
    batch_size = max(batch_size, 1)
    trace('Start placement batches: total={0}'.format(len(filtered_points)))
    batches = list(_chunks(filtered_points, batch_size))
    
    with forms.ProgressBar(title='EOM: Placing lights', cancellable=True, step=1) as pb2:
        pb2.max_value = len(batches)
        bi = 0
        for batch in batches:
            bi += 1
            pb2.update_progress(bi, pb2.max_value)
            if pb2.cancelled:
                trace('Cancelled during placement batches')
                break

            with tx('EOM: Place lights from linked rooms (demo)', doc=doc, swallow_warnings=True):
                created = placement_engine.place_lights_at_points(
                    doc,
                    symbol,
                    batch,
                    comment_value=comment_value,
                    view=doc.ActiveView,
                    prefer_level=host_level,
                    continue_on_error=True
                )
                created_count += len(created)
                if first_created_id is None and created:
                    try:
                        first_created_id = created[0].Id
                    except Exception:
                        first_created_id = None
                if created:
                    try:
                        for ci in created:
                            if len(created_ids) >= 500:
                                break
                            created_ids.append(ci.Id)
                    except Exception:
                        pass

            trace('Batch done: placed={0}'.format(created_count))

    output.print_md('---')
    output.print_md('Placed **{0}** light(s).'.format(created_count))


def _report_symbol_geometry(symbol, output):
    if symbol is None:
        return
    try:
        opts = DB.Options()
        try:
            opts.DetailLevel = DB.ViewDetailLevel.Fine
        except Exception:
            pass
        geom = symbol.get_Geometry(opts)
        if geom is None:
            output.print_md('Symbol geometry: **None** (may be invisible in 3D/plan)')
            return

        solids = 0
        meshes = 0
        curves = 0
        for g in geom:
            try:
                if isinstance(g, DB.Solid) and g.Volume > 0:
                    solids += 1
                elif isinstance(g, DB.Mesh):
                    meshes += 1
                elif isinstance(g, DB.Curve):
                    curves += 1
            except Exception:
                continue
        output.print_md('Symbol geometry summary: solids={0}, meshes={1}, curves={2}'.format(solids, meshes, curves))
        if solids == 0 and meshes == 0 and curves == 0:
            output.print_md('**Warning:** selected family type seems to have no geometry.')
    except Exception:
        pass
