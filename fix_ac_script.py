# -*- coding: utf-8 -*-
"""Apply fixes to the AC socket placement script."""
import re

SCRIPT_PATH = r"C:\Users\anton\EOMTemplateTools\EOMTemplateTools.extension\EOM.tab\04_Sockets.panel\Sockets.pulldown\04_AC.pushbutton\script.py"

with open(SCRIPT_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace _is_exterior_wall function
old_func = '''def _is_exterior_wall(wall):
    if wall is None or (not isinstance(wall, DB.Wall)):
        return False
    try:
        p = wall.get_Parameter(DB.BuiltInParameter.FUNCTION_PARAM)
        return bool(p and p.AsInteger() == 1)
    except Exception:
        return False'''

new_func = '''def _is_exterior_wall(wall):
    """Check if wall is exterior/facade by Function param or name keywords."""
    if wall is None or (not isinstance(wall, DB.Wall)):
        return False
    try:
        p = wall.get_Parameter(DB.BuiltInParameter.FUNCTION_PARAM)
        if p and p.AsInteger() == 1:
            return True
    except Exception:
        pass
    ext_kw = (u'фасад', u'наружн', u'внешн', u'exterior', u'facade', u'external', u'curtain', u'витраж', u'ограждающ')
    try:
        wt = wall.WallType
        if wt:
            wt_name = (wt.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or u'').lower()
            for kw in ext_kw:
                if kw in wt_name:
                    return True
    except Exception:
        pass
    try:
        w_name = (wall.Name or u'').lower()
        for kw in ext_kw:
            if kw in w_name:
                return True
    except Exception:
        pass
    return False'''

content = content.replace(old_func, new_func)

# Fix 2: Replace _is_facade_wall_for_basket fallback
old_fallback = '''    # If we can't find any room on either side, we can't confidently classify.
    if rr_pos is None and rr_neg is None:
        return False'''

new_fallback = '''    # If we can't find any room on either side, fallback to exterior wall check.
    if rr_pos is None and rr_neg is None:
        return _is_exterior_wall(wall)'''

content = content.replace(old_fallback, new_fallback)

# Fix 3: Change perp_dot_max default from 0.80 to 0.35
content = content.replace(
    "perp_dot_max = float(rules.get('ac_perp_dot_max', 0.80) or 0.80)",
    "perp_dot_max = float(rules.get('ac_perp_dot_max', 0.35) or 0.35)"
)
content = content.replace(
    "perp_dot_max = 0.80",
    "perp_dot_max = 0.35"
)

# Fix 4: Add facade_dir_hint fallback from room center
old_facade_hint = '''            facade_dir_hint = facade_dir
            if facade_dir_hint is None and closest_wall is not None:
                try:
                    facade_dir_hint = _wall_dir_xy(closest_wall)
                except Exception:
                    facade_dir_hint = None

            try:
                if facade_dir_hint is not None:'''

new_facade_hint = '''            facade_dir_hint = facade_dir
            if facade_dir_hint is None and closest_wall is not None:
                try:
                    facade_dir_hint = _wall_dir_xy(closest_wall)
                except Exception:
                    facade_dir_hint = None

            # IMPROVED FALLBACK: Compute facade direction from room center to basket
            if facade_dir_hint is None:
                try:
                    for r in candidate_rooms_lvl_placeable:
                        bb_r = r.get_BoundingBox(None)
                        if bb_r is None:
                            continue
                        room_center = DB.XYZ(
                            (float(bb_r.Min.X) + float(bb_r.Max.X)) * 0.5,
                            (float(bb_r.Min.Y) + float(bb_r.Max.Y)) * 0.5,
                            float(pt_basket.Z)
                        )
                        dir_to_basket = DB.XYZ(
                            float(pt_basket.X) - float(room_center.X),
                            float(pt_basket.Y) - float(room_center.Y),
                            0.0
                        )
                        if dir_to_basket.GetLength() > 1e-6:
                            facade_dir_hint = DB.XYZ(-float(dir_to_basket.Y), float(dir_to_basket.X), 0.0)
                            facade_dir_hint = facade_dir_hint.Normalize()
                            break
                except Exception:
                    pass

            try:
                if facade_dir_hint is not None:'''

content = content.replace(old_facade_hint, new_facade_hint)

# Fix 5: Add synthetic both sides fallback
old_both_sides = '''                        if 1 in best0 and -1 in best0:
                            break

                # Accept this wall if we either need only 1 socket, or we have both sides.'''

new_both_sides = '''                        if 1 in best0 and -1 in best0:
                            break

                # FINAL FALLBACK: Create synthetic entries for missing sides
                if int(max_per_basket) > 1 and ((1 not in best0) or (-1 not in best0)):
                    try:
                        z_synth = float(getattr(anchor0, 'Z', 0.0))
                    except Exception:
                        z_synth = 0.0
                    placeholder_room = None
                    if best0:
                        try:
                            placeholder_room = list(best0.values())[0][2]
                        except Exception:
                            placeholder_room = None
                    if placeholder_room is None and candidate_rooms_lvl_placeable:
                        try:
                            placeholder_room = candidate_rooms_lvl_placeable[0]
                        except Exception:
                            placeholder_room = None
                    if placeholder_room is not None:
                        try:
                            z_synth = _calc_room_target_z(placeholder_room, link_doc, h_ceiling_ft) or z_synth
                        except Exception:
                            pass
                    for missing_sgn in (1, -1):
                        if missing_sgn not in best0:
                            cc_synth = (0.0, wall0, DB.XYZ(float(anchor0.X), float(anchor0.Y), float(z_synth)), wdir0, False, corner0)
                            best0[missing_sgn] = (99, 0.0, placeholder_room, 'synthetic_both_sides', cc_synth)

                # Accept this wall if we either need only 1 socket, or we have both sides.'''

content = content.replace(old_both_sides, new_both_sides)

with open(SCRIPT_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixes applied successfully!")
