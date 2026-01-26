# -*- coding: utf-8 -*-


def pt_key_mm(p, step_mm=5):
    try:
        x = round(p.X * 304.8 / step_mm) * step_mm
        y = round(p.Y * 304.8 / step_mm) * step_mm
        z = round(p.Z * 304.8 / step_mm) * step_mm
        return (int(x), int(y), int(z))
    except Exception:
        return None


def is_near_existing(pt, existing_pts, radius_ft):
    if not existing_pts:
        return False
    try:
        r = float(radius_ft)
        for ex in existing_pts:
            try:
                if pt.DistanceTo(ex) < r:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def dedupe_points(points_xyz, existing_xyz, radius_ft, mode='radius', key_step_mm=5):
    """Filter out points that are too close to existing ones."""
    pts = points_xyz or []
    ex = existing_xyz or []
    out = []
    skipped = 0

    if not ex:
        return list(pts), 0

    if mode == 'exact':
        keys = set()
        for p in ex:
            k = pt_key_mm(p, step_mm=key_step_mm)
            if k is not None:
                keys.add(k)
        for p in pts:
            k = pt_key_mm(p, step_mm=key_step_mm)
            if k is not None and k in keys:
                skipped += 1
                continue
            out.append(p)
        return out, skipped

    # default: radius-based
    r = float(radius_ft or 0.0)
    for p in pts:
        if r > 0 and is_near_existing(p, ex, r):
            skipped += 1
            continue
        out.append(p)
    return out, skipped


def enforce_min_spacing(points_xyz, min_dist_ft):
    """Filter points so that no two accepted points are closer than min_dist_ft."""
    pts = points_xyz or []
    try:
        d = float(min_dist_ft or 0.0)
    except Exception:
        d = 0.0
    if d <= 0.0 or len(pts) < 2:
        return list(pts), 0

    cell = d
    grid = {}
    kept = []
    skipped = 0

    def _cell_key(p):
        return (int(p.X / cell), int(p.Y / cell))

    for p in pts:
        k = _cell_key(p)
        ok = True
        # check neighbor cells
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                kk = (k[0] + dx, k[1] + dy)
                arr = grid.get(kk)
                if not arr:
                    continue
                for q in arr:
                    try:
                        if p.DistanceTo(q) < d:
                            ok = False
                            break
                    except Exception:
                        continue
                if not ok:
                    break
            if not ok:
                break

        if not ok:
            skipped += 1
            continue

        kept.append(p)
        grid.setdefault(k, []).append(p)

    return kept, skipped
