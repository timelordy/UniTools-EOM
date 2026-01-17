# -*- coding: utf-8 -*-
import gc
import math
import re
import os
import time

from pyrevit import DB, forms, revit, script

import System

_HAS_DRAWING = False
_HAS_DRAWING_MARK = False
Bitmap = None
Graphics = None
Pen = None
Color = None
SolidBrush = None
Font = None
ImageFormat = None
try:
    import clr  # pyRevit CPython (pythonnet)
    try:
        clr.AddReference('System.Drawing')
    except Exception:
        pass
    try:
        clr.AddReference('System.Drawing')
    except Exception:
        pass
    try:
        clr.AddReference('System.Drawing.Common')
    except Exception:
        pass
    from System.Drawing import Bitmap, Graphics, Pen, Color, SolidBrush, Font  # noqa: F401
    try:
        from System.Drawing.Imaging import ImageFormat  # noqa: F401
    except Exception:
        ImageFormat = None
    _HAS_DRAWING = Bitmap is not None
    _HAS_DRAWING_MARK = _HAS_DRAWING and (Graphics is not None) and (Pen is not None) and (Color is not None)
except Exception:
    Bitmap = None
    _HAS_DRAWING = False
    _HAS_DRAWING_MARK = False

import config_loader
import link_reader
import placement_engine
from utils_revit import alert, log_exception
from utils_units import mm_to_ft, ft_to_mm
import socket_utils as su

doc = revit.doc
output = script.get_output()
logger = script.get_logger()

XY_TOL = 1e-6


_SCREEN_PIXEL_SIZE = 1600
_SCREEN_GRID_STEP_PX = 4
_SCREEN_PAD_MM = 600
_INK_RGB_SUM_THRESHOLD = 740  # < 740 => non-white-ish


def _get_temp_screens_folder():
    try:
        base = System.IO.Path.GetTempPath()
    except Exception:
        base = os.environ.get('TEMP') or os.environ.get('TMP') or 'C:\\Temp'
    folder = os.path.join(base, 'EOMTemplateTools_WetScreens')
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
    except Exception:
        pass
    return folder


def _nearest_level_by_elev(host_doc, z_ft):
    if host_doc is None:
        return None
    try:
        z = float(z_ft or 0.0)
    except Exception:
        z = 0.0
    best = None
    best_d = None
    try:
        for lvl in DB.FilteredElementCollector(host_doc).OfClass(DB.Level):
            try:
                d = abs(float(lvl.Elevation) - z)
                if best is None or d < best_d:
                    best, best_d = lvl, d
            except Exception:
                continue
    except Exception:
        return None
    return best


def _get_or_create_floor_plan_view(host_doc, level, name, view_cache=None):
    if host_doc is None or level is None:
        return None
    try:
        if view_cache is not None:
            k = int(level.Id.IntegerValue)
            v = view_cache.get(k)
            if v is not None:
                return v
    except Exception:
        pass

    # Reuse existing by exact name
    try:
        for v in DB.FilteredElementCollector(host_doc).OfClass(DB.ViewPlan):
            try:
                if v and (not v.IsTemplate) and v.Name == name:
                    if view_cache is not None:
                        view_cache[int(level.Id.IntegerValue)] = v
                    return v
            except Exception:
                continue
    except Exception:
        pass

    # Create new floor plan view
    vft_id = None
    try:
        for vft in DB.FilteredElementCollector(host_doc).OfClass(DB.ViewFamilyType):
            try:
                if vft.ViewFamily == DB.ViewFamily.FloorPlan:
                    vft_id = vft.Id
                    break
            except Exception:
                continue
    except Exception:
        vft_id = None
    if vft_id is None:
        return None

    try:
        with revit.Transaction('ЭОМ: создать план для скринов (05_Wet)'):
            v = DB.ViewPlan.Create(host_doc, vft_id, level.Id)
            try:
                v.Name = name
            except Exception:
                pass
    except Exception:
        return None

    if view_cache is not None:
        try:
            view_cache[int(level.Id.IntegerValue)] = v
        except Exception:
            pass
    return v


def _setup_view_for_screenshot(host_doc, view):
    if host_doc is None or view is None:
        return

    try:
        with revit.Transaction('ЭОМ: подготовить вид для скринов (05_Wet)'):
            try:
                if hasattr(view, 'ViewTemplateId'):
                    view.ViewTemplateId = DB.ElementId.InvalidElementId
            except Exception:
                pass

            try:
                view.CropBoxActive = True
                view.CropBoxVisible = True
            except Exception:
                pass

            # Reduce noise for pixel scoring
            hide_bics = [
                DB.BuiltInCategory.OST_Dimensions,
                DB.BuiltInCategory.OST_TextNotes,
                DB.BuiltInCategory.OST_GenericAnnotation,
                DB.BuiltInCategory.OST_Tags,
                DB.BuiltInCategory.OST_RoomTags,
                DB.BuiltInCategory.OST_Levels,
                DB.BuiltInCategory.OST_Grids,
                DB.BuiltInCategory.OST_SpotElevations,
                DB.BuiltInCategory.OST_SpotCoordinates,
                DB.BuiltInCategory.OST_SpotSlopes,
            ]
            for bic in hide_bics:
                try:
                    cat = host_doc.Settings.Categories.get_Item(bic)
                    if cat:
                        view.SetCategoryHidden(cat.Id, True)
                except Exception:
                    continue

            # Ensure links are visible
            try:
                cat_links = host_doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_RvtLinks)
                if cat_links:
                    view.SetCategoryHidden(cat_links.Id, False)
            except Exception:
                pass
    except Exception:
        pass


def _set_view_crop_to_host_rect(view, host_min_xy, host_max_xy, pad_ft):
    if view is None or host_min_xy is None or host_max_xy is None:
        return False

    try:
        pad = float(pad_ft or 0.0)
    except Exception:
        pad = 0.0

    try:
        bb = view.CropBox
        if bb is None:
            return False
        tr = bb.Transform
        inv = tr.Inverse
    except Exception:
        return False

    try:
        p0 = inv.OfPoint(host_min_xy)
        p1 = inv.OfPoint(host_max_xy)
        minx = min(float(p0.X), float(p1.X)) - pad
        miny = min(float(p0.Y), float(p1.Y)) - pad
        maxx = max(float(p0.X), float(p1.X)) + pad
        maxy = max(float(p0.Y), float(p1.Y)) + pad

        bb2 = DB.BoundingBoxXYZ()
        bb2.Transform = tr
        bb2.Min = DB.XYZ(minx, miny, bb.Min.Z)
        bb2.Max = DB.XYZ(maxx, maxy, bb.Max.Z)

        with revit.Transaction('ЭОМ: crop для скрина (05_Wet)'):
            view.CropBox = bb2
            try:
                view.CropBoxActive = True
                view.CropBoxVisible = True
            except Exception:
                pass
        return True
    except Exception:
        return False


def _export_view_png(host_doc, view, base_path_no_ext, pixel_size):
    if host_doc is None or view is None:
        return None

    try:
        px = int(pixel_size or _SCREEN_PIXEL_SIZE)
    except Exception:
        px = _SCREEN_PIXEL_SIZE
    px = max(px, 600)

    try:
        out_dir = os.path.dirname(base_path_no_ext)
        if out_dir and (not os.path.exists(out_dir)):
            os.makedirs(out_dir)
    except Exception:
        pass

    try:
        opts = DB.ImageExportOptions()
        opts.ExportRange = DB.ExportRange.SetOfViews
        try:
            from System.Collections.Generic import List
            lst = List[DB.ElementId]()
            lst.Add(view.Id)
            opts.SetViewsAndSheets(lst)
        except Exception:
            return None
        opts.FilePath = base_path_no_ext
        opts.HLRandWFViewsFileType = DB.ImageFileType.PNG
        opts.ImageResolution = DB.ImageResolution.DPI_150
        opts.ZoomType = DB.ZoomFitType.FitToPage
        opts.PixelSize = px
        host_doc.ExportImage(opts)
    except Exception:
        return None

    # Revit may append view name; pick the newest PNG that starts with our base name.
    try:
        folder = os.path.dirname(base_path_no_ext)
        prefix = os.path.basename(base_path_no_ext)
        if (not folder) or (not os.path.exists(folder)):
            return None
        pl = (prefix or '').lower()
        for _ in range(25):
            best = None
            best_mtime = None
            for fn in os.listdir(folder):
                try:
                    fl = (fn or '').lower()
                    if not fl.endswith('.png'):
                        continue
                    if pl and (not fl.startswith(pl)):
                        continue
                    p = os.path.join(folder, fn)
                    try:
                        if os.path.getsize(p) <= 0:
                            continue
                    except Exception:
                        pass
                    mt = os.path.getmtime(p)
                    if best is None or mt > best_mtime:
                        best, best_mtime = p, mt
                except Exception:
                    continue
            if best:
                return best
            try:
                time.sleep(0.12)
            except Exception:
                pass
    except Exception:
        return None

    return None


def _path_to_file_uri(path):
    if not path:
        return None
    try:
        # Handles spaces and other escaping correctly
        return System.Uri(str(path)).AbsoluteUri
    except Exception:
        pass
    try:
        p = str(path)
    except Exception:
        return None
    try:
        p = p.replace('\\', '/')
    except Exception:
        pass
    if p.startswith('file:///'):
        return p
    if re.match(r'^[A-Za-z]:/', p):
        return 'file:///' + p
    return p


def _output_show_png(out, png_path, title=None):
    if out is None or not png_path:
        return
    try:
        if title:
            out.print_md('### {0}'.format(title))
    except Exception:
        pass

    # Base64 preview first (works even if file:// is blocked in the output webview).
    try:
        import base64
        uri = None
        try:
            uri = _path_to_file_uri(png_path)
        except Exception:
            uri = None
        data = None
        for _ in range(8):
            try:
                with open(png_path, 'rb') as fp:
                    data = fp.read()
                break
            except Exception:
                data = None
                try:
                    time.sleep(0.12)
                except Exception:
                    pass
        if data and len(data) > 0:
            # Avoid insane output sizes; keep file link as fallback.
            try:
                if len(data) > (4 * 1024 * 1024):
                    data = None
            except Exception:
                pass

        if data:
            b64 = base64.b64encode(data)
            try:
                b64s = b64.decode('ascii')
            except Exception:
                b64s = str(b64)
            src = 'data:image/png;base64,{0}'.format(b64s)
            href = uri or src
            out.print_html(
                '<div style="max-width: 100%; text-align: center;">'
                '<a href="{0}" target="_blank" style="text-decoration:none;">'
                '<img loading="lazy" style="max-width: 100%; max-height: 75vh; height: auto; width: auto; object-fit: contain; border: 1px solid #bbb;" src="{1}">'
                '</a>'
                '</div>'.format(href, src)
            )
            return
    except Exception:
        pass

    # Fallback: try local file URI
    try:
        uri = _path_to_file_uri(png_path)
        if uri:
            out.print_html(
                '<div style="max-width: 100%; text-align: center;">'
                '<a href="{0}" target="_blank" style="text-decoration:none;">'
                '<img loading="lazy" style="max-width: 100%; max-height: 75vh; height: auto; width: auto; object-fit: contain; border: 1px solid #bbb;" src="{0}">'
                '</a>'
                '</div>'.format(uri)
            )
            return
    except Exception:
        pass

    try:
        out.print_md('PNG: `{0}`'.format(png_path))
    except Exception:
        pass


class _InkGrid(object):
    __slots__ = (
        'path', 'w', 'h', 'step', 'gw', 'gh', 'grid',
        'content_min_px', 'content_min_py', 'content_max_px', 'content_max_py'
    )

    def __init__(self, path, w, h, step, gw, gh, grid, bminx, bminy, bmaxx, bmaxy):
        self.path = path
        self.w = w
        self.h = h
        self.step = step
        self.gw = gw
        self.gh = gh
        self.grid = grid
        self.content_min_px = bminx
        self.content_min_py = bminy
        self.content_max_px = bmaxx
        self.content_max_py = bmaxy


def _is_ink_rgb(r, g, b):
    try:
        return (int(r) + int(g) + int(b)) < _INK_RGB_SUM_THRESHOLD
    except Exception:
        return True


def _build_ink_grid(png_path, step_px=_SCREEN_GRID_STEP_PX):
    if (not png_path) or (not _HAS_DRAWING) or (Bitmap is None):
        return None

    try:
        step = max(int(step_px or 4), 1)
    except Exception:
        step = 4

    bmp = None
    try:
        # Revit may keep the file locked for a short moment after ExportImage
        for _ in range(8):
            try:
                bmp = Bitmap(png_path)
                break
            except Exception:
                bmp = None
                try:
                    time.sleep(0.12)
                except Exception:
                    pass
        if bmp is None:
            return None
        w = int(bmp.Width)
        h = int(bmp.Height)
        gw = max(1, int(w // step))
        gh = max(1, int(h // step))

        grid = [[False] * gw for _ in range(gh)]
        minx = gw
        miny = gh
        maxx = -1
        maxy = -1

        for gy in range(gh):
            py = gy * step
            for gx in range(gw):
                px = gx * step
                try:
                    c = bmp.GetPixel(px, py)
                    ink = _is_ink_rgb(c.R, c.G, c.B)
                except Exception:
                    ink = False

                grid[gy][gx] = ink
                if ink:
                    if gx < minx:
                        minx = gx
                    if gy < miny:
                        miny = gy
                    if gx > maxx:
                        maxx = gx
                    if gy > maxy:
                        maxy = gy

        if maxx < 0:
            # empty image
            bminx = 0
            bminy = 0
            bmaxx = w - 1
            bmaxy = h - 1
        else:
            # expand a bit
            pad = 2
            minx = max(minx - pad, 0)
            miny = max(miny - pad, 0)
            maxx = min(maxx + pad, gw - 1)
            maxy = min(maxy + pad, gh - 1)
            bminx = int(minx * step)
            bminy = int(miny * step)
            bmaxx = min(int((maxx + 1) * step), w - 1)
            bmaxy = min(int((maxy + 1) * step), h - 1)

        return _InkGrid(png_path, w, h, step, gw, gh, grid, bminx, bminy, bmaxx, bmaxy)
    except Exception:
        return None
    finally:
        try:
            if bmp is not None:
                bmp.Dispose()
        except Exception:
            pass


def _ink_density_at_link_point(ink_grid, crop_bb, crop_inv_tr, link_pt, link_to_host_tr, radius_ft):
    """Return 0..1 ink density around point (lower is better)."""
    if ink_grid is None or crop_bb is None or crop_inv_tr is None or link_pt is None or link_to_host_tr is None:
        return None

    # link -> host (model)
    try:
        host_pt = link_to_host_tr.OfPoint(link_pt)
    except Exception:
        return None

    # host(model) -> view coords
    try:
        pv = crop_inv_tr.OfPoint(host_pt)
    except Exception:
        return None

    dx = float(crop_bb.Max.X) - float(crop_bb.Min.X)
    dy = float(crop_bb.Max.Y) - float(crop_bb.Min.Y)
    if abs(dx) <= 1e-9 or abs(dy) <= 1e-9:
        return None

    try:
        nx = (float(pv.X) - float(crop_bb.Min.X)) / dx
        ny = (float(crop_bb.Max.Y) - float(pv.Y)) / dy
    except Exception:
        return None

    if nx < -0.05 or nx > 1.05 or ny < -0.05 or ny > 1.05:
        return None

    # Pixel bounds representing the actual crop region content
    bminx = int(ink_grid.content_min_px)
    bminy = int(ink_grid.content_min_py)
    bmaxx = int(ink_grid.content_max_px)
    bmaxy = int(ink_grid.content_max_py)
    bw = max(bmaxx - bminx, 1)
    bh = max(bmaxy - bminy, 1)

    px = int(bminx + nx * bw)
    py = int(bminy + ny * bh)

    # Convert to grid coords
    step = int(ink_grid.step)
    gx = int(px // step)
    gy = int(py // step)
    if gx < 0 or gy < 0 or gx >= ink_grid.gw or gy >= ink_grid.gh:
        return None

    try:
        # radius in grid cells
        # pixel_per_ft approx
        ppf = (float(bw) / dx + float(bh) / dy) * 0.5
        r_px = max(int(float(radius_ft or 0.0) * ppf), 1)
        r_g = max(int(r_px // step), 1)
    except Exception:
        r_g = 6

    ink = 0
    total = 0
    r2 = r_g * r_g
    x0 = max(gx - r_g, 0)
    y0 = max(gy - r_g, 0)
    x1 = min(gx + r_g, ink_grid.gw - 1)
    y1 = min(gy + r_g, ink_grid.gh - 1)

    grid = ink_grid.grid
    for yy in range(y0, y1 + 1):
        dy2 = (yy - gy) * (yy - gy)
        for xx in range(x0, x1 + 1):
            dx2 = (xx - gx) * (xx - gx)
            if dx2 + dy2 > r2:
                continue
            total += 1
            if grid[yy][xx]:
                ink += 1

    if total <= 0:
        return 1.0
    return float(ink) / float(total)


def _screen_pixel_from_link_point(ink_grid, crop_bb, crop_inv_tr, link_pt, link_to_host_tr):
    if ink_grid is None or crop_bb is None or crop_inv_tr is None or link_pt is None or link_to_host_tr is None:
        return None
    try:
        host_pt = link_to_host_tr.OfPoint(link_pt)
        pv = crop_inv_tr.OfPoint(host_pt)
    except Exception:
        return None

    dx = float(crop_bb.Max.X) - float(crop_bb.Min.X)
    dy = float(crop_bb.Max.Y) - float(crop_bb.Min.Y)
    if abs(dx) <= 1e-9 or abs(dy) <= 1e-9:
        return None

    try:
        nx = (float(pv.X) - float(crop_bb.Min.X)) / dx
        ny = (float(crop_bb.Max.Y) - float(pv.Y)) / dy
    except Exception:
        return None

    # content bounds inside image (to compensate Revit margins)
    bminx = int(ink_grid.content_min_px)
    bminy = int(ink_grid.content_min_py)
    bmaxx = int(ink_grid.content_max_px)
    bmaxy = int(ink_grid.content_max_py)
    bw = max(bmaxx - bminx, 1)
    bh = max(bmaxy - bminy, 1)

    px = int(bminx + nx * bw)
    py = int(bminy + ny * bh)

    try:
        px = max(0, min(px, int(ink_grid.w) - 1))
        py = max(0, min(py, int(ink_grid.h) - 1))
    except Exception:
        pass
    return px, py


def _mark_png_socket(png_path, px, py, label=None, out_path=None):
    if (not png_path) or (not _HAS_DRAWING_MARK) or (Bitmap is None) or (Graphics is None) or (Pen is None) or (Color is None):
        return None
    if px is None or py is None:
        return None

    try:
        if out_path is None:
            root, ext = os.path.splitext(png_path)
            out_path = root + '__socket' + ext
    except Exception:
        out_path = None

    bmp = None
    g = None
    try:
        # Revit may keep the file locked briefly
        for _ in range(8):
            try:
                bmp = Bitmap(png_path)
                break
            except Exception:
                bmp = None
                try:
                    time.sleep(0.12)
                except Exception:
                    pass
        if bmp is None:
            return None
        g = Graphics.FromImage(bmp)
        try:
            g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias
        except Exception:
            pass

        r = 14
        try:
            pen = Pen(Color.Red, 3)
        except Exception:
            pen = None
        try:
            pen2 = Pen(Color.White, 1)
        except Exception:
            pen2 = None

        # cross + circle
        if pen:
            g.DrawEllipse(pen, int(px - r), int(py - r), int(r * 2), int(r * 2))
            g.DrawLine(pen, int(px - r), int(py), int(px + r), int(py))
            g.DrawLine(pen, int(px), int(py - r), int(px), int(py + r))
        if pen2:
            rr = r - 3
            g.DrawEllipse(pen2, int(px - rr), int(py - rr), int(rr * 2), int(rr * 2))

        if label:
            try:
                font = Font('Arial', 10)
                brush = SolidBrush(Color.Red)
                g.DrawString(str(label), font, brush, float(px + r + 4), float(py - r - 2))
            except Exception:
                pass

        if out_path:
            try:
                if ImageFormat is not None:
                    bmp.Save(out_path, ImageFormat.Png)
                else:
                    bmp.Save(out_path)
                return out_path
            except Exception:
                return None
        return None
    except Exception:
        return None
    finally:
        try:
            if g is not None:
                g.Dispose()
        except Exception:
            pass
        try:
            if bmp is not None:
                bmp.Dispose()
        except Exception:
            pass


class Fixture2D(object):
    __slots__ = ('element', 'center', 'bbox_min', 'bbox_max', 'kind')

    def __init__(self, element, center, bbox_min, bbox_max, kind=None):
        self.element = element
        self.center = center
        self.bbox_min = bbox_min
        self.bbox_max = bbox_max
        # kind helps prioritise fixtures (wm, boiler, rail, sink, fallback)
        self.kind = kind or 'wm'


def _fixture_priority(kind):
    k = (kind or '').lower()
    if 'boiler' in k or 'bk' in k:
        return 0
    if 'rail' in k:
        return 1
    if 'wm' in k or 'wash' in k:
        return 2
    if 'sink' in k:
        return 3
    if 'fallback' in k:
        return 9
    return 5


def get_room_boundary_segments_2d(room, boundary_opts):
    segs_2d = []
    if room is None:
        return segs_2d
    try:
        seglists = room.GetBoundarySegments(boundary_opts)
    except Exception:
        return segs_2d
    if not seglists:
        return segs_2d

    def _total_length(segs):
        total = 0.0
        for seg in segs:
            try:
                curve = seg.GetCurve()
                if curve:
                    total += float(curve.Length)
            except Exception:
                pass
        return total

    loop = max(seglists, key=_total_length)
    for seg in loop:
        try:
            curve = seg.GetCurve()
            if curve is None:
                continue
            wall = room.Document.GetElement(seg.ElementId)
            
            # Allow Walls and Columns (FamilyInstance)
            is_valid_bound = False
            if isinstance(wall, DB.Wall): is_valid_bound = True
            elif isinstance(wall, DB.FamilyInstance):
                # Check category if possible, or just allow any solid family instance
                try:
                    cat = wall.Category
                    if cat:
                        bic = cat.Id.IntegerValue
                        if bic in (int(DB.BuiltInCategory.OST_Columns), int(DB.BuiltInCategory.OST_StructuralColumns)):
                            is_valid_bound = True
                except: pass
            
            if not is_valid_bound:
                continue
                
            if isinstance(wall, DB.Wall) and su._is_curtain_wall(wall):
                continue
                
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
            if not p0 or not p1:
                continue
            if p0.DistanceTo(p1) <= 1e-6:
                continue
            segs_2d.append((p0, p1, wall))
        except Exception:
            continue
    return segs_2d


def get_2d_bbox(element):
    if element is None:
        return None
    try:
        bb = element.get_BoundingBox(None)
        if not bb:
            return None
        return DB.XYZ(bb.Min.X, bb.Min.Y, 0.0), DB.XYZ(bb.Max.X, bb.Max.Y, 0.0)
    except Exception:
        return None


def segments_intersect(p1, p2, p3, p4, tol=1e-9):
    r = DB.XYZ(p2.X - p1.X, p2.Y - p1.Y, 0.0)
    s = DB.XYZ(p4.X - p3.X, p4.Y - p3.Y, 0.0)
    denom = r.X * s.Y - r.Y * s.X
    if abs(denom) < tol:
        return False, None, None, None
    qp = DB.XYZ(p3.X - p1.X, p3.Y - p1.Y, 0.0)
    t = (qp.X * s.Y - qp.Y * s.X) / denom
    u = (qp.X * r.Y - qp.Y * r.X) / denom
    if -tol <= t <= 1.0 + tol and -tol <= u <= 1.0 + tol:
        ix = p1.X + r.X * t
        iy = p1.Y + r.Y * t
        return True, t, u, DB.XYZ(ix, iy, p1.Z)
    return False, None, None, None


def _closest_point_on_segment_xy(pt, a, b):
    if pt is None or a is None or b is None:
        return None
    abx = float(b.X) - float(a.X)
    aby = float(b.Y) - float(a.Y)
    denom = abx * abx + aby * aby
    if denom <= 1e-12:
        return None
    apx = float(pt.X) - float(a.X)
    apy = float(pt.Y) - float(a.Y)
    t = (apx * abx + apy * aby) / denom
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return DB.XYZ(float(a.X) + abx * t, float(a.Y) + aby * t, float(pt.Z))


def raycast_to_walls(origin_pt, directions, wall_segments, max_distance_ft):
    hits = []
    if not wall_segments or not directions or max_distance_ft is None:
        return hits
    max_dist = float(max_distance_ft)
    for dir_vec in directions:
        dir_xy = DB.XYZ(dir_vec.X, dir_vec.Y, 0.0)
        try:
            length = dir_xy.GetLength()
        except Exception:
            length = None
        if not length or length <= XY_TOL:
            continue
        dir_unit = dir_xy.Normalize()
        ray_end = DB.XYZ(
            origin_pt.X + dir_unit.X * max_dist,
            origin_pt.Y + dir_unit.Y * max_dist,
            origin_pt.Z
        )
        best_hit = None
        for p1, p2, wall in wall_segments:
            ok, t_ray, _, hit_pt = segments_intersect(origin_pt, ray_end, p1, p2)
            if not ok or t_ray is None or hit_pt is None:
                continue
            if t_ray < 0.0:
                continue
            dist = t_ray * max_dist
            if dist <= XY_TOL:
                continue
            if dist > max_dist + XY_TOL:
                continue
            wall_vec = DB.XYZ(p2.X - p1.X, p2.Y - p1.Y, 0.0)
            try:
                wall_len = wall_vec.GetLength()
            except Exception:
                wall_len = None
            if not wall_len or wall_len <= XY_TOL:
                continue
            wall_dir = wall_vec.Normalize()
            if best_hit is None or dist < best_hit['distance']:
                best_hit = {
                    'distance': dist,
                    'point': DB.XYZ(hit_pt.X, hit_pt.Y, origin_pt.Z),
                    'wall': wall,
                    'wall_dir': wall_dir,
                    'seg_p1': p1,
                    'seg_p2': p2
                }
        if best_hit:
            hits.append(best_hit)
    return hits


def _inward_normal_xy(wall_dir_xy, hit_pt_xy, room_center_xy):
    if wall_dir_xy is None or hit_pt_xy is None or room_center_xy is None:
        return None
    try:
        wd = DB.XYZ(float(wall_dir_xy.X), float(wall_dir_xy.Y), 0.0)
        if wd.GetLength() <= XY_TOL:
            return None
        wd = wd.Normalize()
        n1 = DB.XYZ(0, 0, 1).CrossProduct(wd)  # left
        n2 = wd.CrossProduct(DB.XYZ(0, 0, 1))  # right
        to_c = DB.XYZ(float(room_center_xy.X - hit_pt_xy.X), float(room_center_xy.Y - hit_pt_xy.Y), 0.0)
        if to_c.GetLength() <= XY_TOL:
            return n1.Normalize()
        to_c = to_c.Normalize()
        return n1.Normalize() if n1.Normalize().DotProduct(to_c) >= n2.Normalize().DotProduct(to_c) else n2.Normalize()
    except Exception:
        return None


def _push_point_inside_room(room,
                           pt,
                           in_dir_xy=None,
                           wall_dir_xy=None,
                           room_center_xy=None,
                           room_bb=None,
                           z_test=None,
                           max_push_mm=650):
    """Move a boundary/face point slightly into the room so it's not inside the wall thickness."""
    if room is None or pt is None:
        return pt

    # Z used for Room.IsPointInRoom (some linked elements have Z=0)
    z = None
    try:
        if z_test is not None:
            z = float(z_test)
    except Exception:
        z = None
    if z is None:
        try:
            if room_bb:
                z = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
        except Exception:
            z = None
    if z is None:
        try:
            z = float(pt.Z)
        except Exception:
            z = 0.0

    # Preferred: inward normal (perpendicular to wall direction, towards room center)
    dir_in = None
    try:
        if wall_dir_xy is not None and room_center_xy is not None:
            dir_in = _inward_normal_xy(wall_dir_xy, pt, room_center_xy)
    except Exception:
        dir_in = None

    # Fallback: use provided direction
    if dir_in is None and in_dir_xy is not None:
        try:
            v = DB.XYZ(float(in_dir_xy.X), float(in_dir_xy.Y), 0.0)
            if v.GetLength() > XY_TOL:
                dir_in = v.Normalize()
        except Exception:
            dir_in = None

    # Fallback: direction to room center
    if dir_in is None and room_center_xy is not None:
        try:
            v = DB.XYZ(float(room_center_xy.X - pt.X), float(room_center_xy.Y - pt.Y), 0.0)
            if v.GetLength() > XY_TOL:
                dir_in = v.Normalize()
        except Exception:
            dir_in = None

    if dir_in is None:
        return pt

    try:
        mmax = int(max_push_mm or 650)
    except Exception:
        mmax = 650
    mmax = max(mmax, 60)

    # Try increasing offsets until the point is inside the room.
    steps_mm = [20, 60, 120, 200, 300, 450, 650]
    out = pt
    for dmm in steps_mm:
        if dmm <= 0 or dmm > mmax:
            continue
        try:
            out = DB.XYZ(pt.X + dir_in.X * mm_to_ft(dmm), pt.Y + dir_in.Y * mm_to_ft(dmm), pt.Z)
            if _is_point_in_room(room, DB.XYZ(float(out.X), float(out.Y), z)):
                return out
        except Exception:
            continue
    return out


def _bbox_contains_point_xy(pt, bmin, bmax, tol=0.0):
    if pt is None or bmin is None or bmax is None:
        return False
    x, y = float(pt.X), float(pt.Y)
    minx, miny = float(min(bmin.X, bmax.X)), float(min(bmin.Y, bmax.Y))
    maxx, maxy = float(max(bmin.X, bmax.X)), float(max(bmin.Y, bmax.Y))
    return (minx - tol) <= x <= (maxx + tol) and (miny - tol) <= y <= (maxy + tol)


def _dist_point_to_rect_xy(pt, r_min, r_max):
    if pt is None or r_min is None or r_max is None:
        return None
    try:
        px, py = float(pt.X), float(pt.Y)
        minx, miny = float(min(r_min.X, r_max.X)), float(min(r_min.Y, r_max.Y))
        maxx, maxy = float(max(r_min.X, r_max.X)), float(max(r_min.Y, r_max.Y))
        dx = max(minx - px, 0.0, px - maxx)
        dy = max(miny - py, 0.0, py - maxy)
        return (dx * dx + dy * dy) ** 0.5
    except Exception:
        return None


def _bbox_intersects_xy(bmin_a, bmax_a, bmin_b, bmax_b):
    if not all([bmin_a, bmax_a, bmin_b, bmax_b]):
        return False
    minx_a, maxx_a = sorted([bmin_a.X, bmax_a.X])
    miny_a, maxy_a = sorted([bmin_a.Y, bmax_a.Y])
    minx_b, maxx_b = sorted([bmin_b.X, bmax_b.X])
    miny_b, maxy_b = sorted([bmin_b.Y, bmax_b.Y])
    return not (maxx_a < minx_b or maxx_b < minx_a or maxy_a < miny_b or maxy_b < miny_a)


def _expand_bbox_xy(bmin, bmax, buffer_ft):
    if bmin is None or bmax is None or buffer_ft is None:
        return bmin, bmax
    buf = float(buffer_ft)
    return (
        DB.XYZ(min(bmin.X, bmax.X) - buf, min(bmin.Y, bmax.Y) - buf, 0.0),
        DB.XYZ(max(bmin.X, bmax.X) + buf, max(bmin.Y, bmax.Y) + buf, 0.0)
    )


def _is_point_in_room(room, point):
    if room is None or point is None:
        return False
    try:
        return bool(room.IsPointInRoom(point))
    except Exception:
        return False


def _collect_fixture_candidates(link_doc, keywords, categories, fixture_kind='wm'):
    fixtures = []
    if not link_doc:
        return fixtures
    key_norms = [su._norm(k) for k in (keywords or []) if k]
    for bic in categories:
        try:
            collector = DB.FilteredElementCollector(link_doc).OfCategory(bic).WhereElementIsNotElementType()
        except Exception:
            continue
        for elem in collector:
            try:
                label = su._elem_text(elem)
                norm_label = su._norm(label)
                if key_norms and not any(k in norm_label for k in key_norms):
                    continue
                center = su._inst_center_point(elem)
                if not center:
                    continue
                bbox = get_2d_bbox(elem)
                # Some linked instances can return no BoundingBox; keep the element and build
                # a synthetic bbox so we don't lose kind/orientation/host metadata.
                if not bbox:
                    buf = mm_to_ft(350)
                    bbox = (
                        DB.XYZ(center.X - buf, center.Y - buf, 0.0),
                        DB.XYZ(center.X + buf, center.Y + buf, 0.0)
                    )
                fixtures.append(Fixture2D(elem, center, bbox[0], bbox[1], kind=fixture_kind))
            except Exception:
                continue
    return fixtures


def _collect_door_points(link_doc):
    pts = []
    if not link_doc:
        return pts
    try:
        col = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType()
    except Exception:
        col = None
    if not col:
        return pts
    for e in col:
        try:
            pt = su._inst_center_point(e)
        except Exception:
            pt = None
        if pt:
            pts.append(pt)
    return pts


def _filter_fixtures_by_points(fixtures, points, tolerance_ft):
    if not points:
        return fixtures
    tol = max(float(tolerance_ft or 0.5), 0.1)
    idx = su._XYZIndex(cell_ft=tol)
    for pt in points:
        try:
            idx.add(pt.X, pt.Y, 0.0)
        except Exception:
            continue
    filtered = []
    for fx in fixtures:
        c = fx.center
        if c and idx.has_near(c.X, c.Y, 0.0, tol):
            filtered.append(fx)
    return filtered


def _fixtures_in_room(fixtures, room, padding_ft=2.0):
    if not fixtures or room is None:
        return []
    room_bb = None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None
    selected = []
    for fx in fixtures:
        pt = fx.center
        if pt is None:
            continue
        # Some 2D/annotation elements in the linked AR model have an arbitrary Z (often 0)
        # which makes Room.IsPointInRoom fail. Always test using a Z inside the room bbox.
        pt_room = pt
        try:
            if room_bb:
                zmid = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
                pt_room = DB.XYZ(float(pt.X), float(pt.Y), zmid)
        except Exception:
            pt_room = pt
        if room_bb:
            min_exp = DB.XYZ(room_bb.Min.X - padding_ft, room_bb.Min.Y - padding_ft, room_bb.Min.Z)
            max_exp = DB.XYZ(room_bb.Max.X + padding_ft, room_bb.Max.Y + padding_ft, room_bb.Max.Z)
            if not _bbox_contains_point_xy(pt, min_exp, max_exp):
                continue
        if _is_point_in_room(room, pt_room):
            selected.append(fx)
            continue

        # For non-sinks, allow boundary-adjacent fixtures (often hosted on wall) by probing inward.
        try:
            k = (getattr(fx, 'kind', None) or '').lower()
            if k == 'sink':
                continue
        except Exception:
            pass

        # Tolerate fixtures hosted on/inside walls: if center is on boundary (or slightly outside),
        # probe a point towards the room bbox center.
        try:
            if room_bb:
                rc = DB.XYZ(
                    (room_bb.Min.X + room_bb.Max.X) * 0.5,
                    (room_bb.Min.Y + room_bb.Max.Y) * 0.5,
                    pt_room.Z
                )
                v = rc - pt_room
                if v and v.GetLength() > mm_to_ft(1):
                    vn = v.Normalize()
                    for dmm in (200, 500, 900):
                        probe = pt_room + vn * mm_to_ft(dmm)
                        if _is_point_in_room(room, probe):
                            selected.append(fx)
                            break
        except Exception:
            pass
    return selected


def _points_in_room(points, room, padding_ft=2.0):
    if not points or room is None:
        return []
    room_bb = None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None
    selected = []
    for pt in points:
        if pt is None:
            continue
        pt_room = pt
        try:
            if room_bb:
                zmid = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
                pt_room = DB.XYZ(float(pt.X), float(pt.Y), zmid)
        except Exception:
            pt_room = pt
        if room_bb:
            min_exp = DB.XYZ(room_bb.Min.X - padding_ft, room_bb.Min.Y - padding_ft, room_bb.Min.Z)
            max_exp = DB.XYZ(room_bb.Max.X + padding_ft, room_bb.Max.Y + padding_ft, room_bb.Max.Z)
            if not _bbox_contains_point_xy(pt, min_exp, max_exp):
                continue
        if _is_point_in_room(room, pt_room):
            selected.append(pt)
            continue

        # Doors are often on the boundary; tolerate boundary-adjacent points by probing inward.
        try:
            if room_bb:
                rc = DB.XYZ(
                    (room_bb.Min.X + room_bb.Max.X) * 0.5,
                    (room_bb.Min.Y + room_bb.Max.Y) * 0.5,
                    pt_room.Z
                )
                v = rc - pt_room
                if v and v.GetLength() > mm_to_ft(1):
                    vn = v.Normalize()
                    for dmm in (200, 500, 900):
                        probe = pt_room + vn * mm_to_ft(dmm)
                        if _is_point_in_room(room, probe):
                            selected.append(pt)
                            break
        except Exception:
            pass
    return selected


def _append_slide_candidates(candidates,
                            room,
                            room_bb,
                            room_center_xy,
                            origin_pt,
                            hit,
                            kind,
                            priority,
                            local_baths_clash,
                            local_sinks,
                            clash_buffer_ft,
                            sink_clear_ft,
                            slide_step_ft,
                            slide_max_ft,
                            wm_bbox_min=None,
                            wm_bbox_max=None):
    if not candidates or room is None or origin_pt is None or hit is None:
        return
    try:
        wall = hit.get('wall')
        p1 = hit.get('seg_p1')
        p2 = hit.get('seg_p2')
        base_pt = hit.get('point')
        wall_dir = hit.get('wall_dir')
    except Exception:
        return
    if (wall is None) or (p1 is None) or (p2 is None) or (base_pt is None) or (wall_dir is None):
        return

    try:
        step = float(slide_step_ft or 0.0)
        maxd = float(slide_max_ft or 0.0)
    except Exception:
        return
    if step <= mm_to_ft(50) or maxd <= mm_to_ft(50):
        return

    abx = float(p2.X) - float(p1.X)
    aby = float(p2.Y) - float(p1.Y)
    denom = abx * abx + aby * aby
    if denom <= 1e-12:
        return
    seg_len = denom ** 0.5
    if seg_len <= XY_TOL:
        return

    # Base parameter on segment
    try:
        t0 = ((float(base_pt.X) - float(p1.X)) * abx + (float(base_pt.Y) - float(p1.Y)) * aby) / denom
    except Exception:
        return
    if t0 < 0.0:
        t0 = 0.0
    elif t0 > 1.0:
        t0 = 1.0

    # How many steps each side
    try:
        n_steps = int(maxd / step)
    except Exception:
        n_steps = 0
    # Allow further sliding to reach the door in larger bathrooms.
    n_steps = max(min(n_steps, 12), 0)
    if n_steps <= 0:
        return

    # Z for room test
    z_test = None
    try:
        if room_bb:
            z_test = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
    except Exception:
        z_test = None
    if z_test is None:
        try:
            z_test = float(origin_pt.Z)
        except Exception:
            z_test = 0.0

    # Generate candidates
    for sign in (-1.0, 1.0):
        for i in range(1, n_steps + 1):
            try:
                dt = (sign * float(i) * step) / seg_len
            except Exception:
                continue
            t1 = t0 + dt
            if t1 < 0.0:
                t1 = 0.0
            elif t1 > 1.0:
                t1 = 1.0
            # Point on wall segment
            pt_wall = DB.XYZ(float(p1.X) + abx * t1, float(p1.Y) + aby * t1, float(origin_pt.Z))
            point_xy = DB.XYZ(float(pt_wall.X), float(pt_wall.Y), 0.0)

            # Block checks
            blocked = False
            for bmin, bmax in (local_baths_clash or []):
                try:
                    d_b = _dist_point_to_rect_xy(point_xy, bmin, bmax)
                    if d_b is not None and d_b < clash_buffer_ft:
                        blocked = True
                        break
                except Exception:
                    continue
            if blocked:
                continue
            for sink in (local_sinks or []):
                try:
                    sc = sink.center
                    if sc is None:
                        bmin, bmax = sink.bbox_min, sink.bbox_max
                        sc = DB.XYZ((bmin.X + bmax.X) * 0.5, (bmin.Y + bmax.Y) * 0.5, 0.0) if (bmin and bmax) else None
                    if sc is None:
                        continue
                    d_s = point_xy.DistanceTo(DB.XYZ(sc.X, sc.Y, 0.0))
                    if d_s < sink_clear_ft:
                        blocked = True
                        break
                except Exception:
                    continue
            if blocked:
                continue

            # Push point into room so it's not inside wall thickness
            hit_pt = pt_wall
            try:
                hit_pt = _push_point_inside_room(
                    room,
                    pt_wall,
                    in_dir_xy=(origin_pt - pt_wall) if origin_pt else None,
                    wall_dir_xy=wall_dir,
                    room_center_xy=room_center_xy,
                    room_bb=room_bb,
                    z_test=z_test
                )
            except Exception:
                hit_pt = pt_wall

            # Ensure inside room
            try:
                if not _is_point_in_room(room, DB.XYZ(float(hit_pt.X), float(hit_pt.Y), float(z_test))):
                    continue
            except Exception:
                pass

            # Distance to fixture (xy)
            try:
                dxy = DB.XYZ(float(origin_pt.X), float(origin_pt.Y), 0.0).DistanceTo(point_xy)
            except Exception:
                dxy = 1e9

            candidates.append({
                'wall': wall,
                'point': hit_pt,
                'point_on_wall': pt_wall,
                'wall_dir': wall_dir,
                'seg_p1': p1,
                'seg_p2': p2,
                'distance': dxy,
                'priority': priority,
                'kind': kind,
                'wm_bbox': _wm_bbox_contains_point_on_segment_xy(pt_wall, wm_bbox_min, wm_bbox_max, p1, p2) if (str(kind).lower() == 'wm' and wm_bbox_min is not None and wm_bbox_max is not None) else False,
                'wm_bbox_min': wm_bbox_min if str(kind).lower() == 'wm' else None,
                'wm_bbox_max': wm_bbox_max if str(kind).lower() == 'wm' else None
            })


def _bbox_corners_xy(bmin, bmax):
    if bmin is None or bmax is None:
        return []
    minx = float(min(bmin.X, bmax.X))
    maxx = float(max(bmin.X, bmax.X))
    miny = float(min(bmin.Y, bmax.Y))
    maxy = float(max(bmin.Y, bmax.Y))
    return [
        DB.XYZ(minx, miny, 0.0),
        DB.XYZ(minx, maxy, 0.0),
        DB.XYZ(maxx, miny, 0.0),
        DB.XYZ(maxx, maxy, 0.0),
    ]


def _bbox_interval_on_segment_ft(bmin, bmax, seg_p1, seg_p2):
    """Returns (lo, hi, seg_dir, seg_len) in feet along the segment direction."""
    if bmin is None or bmax is None or seg_p1 is None or seg_p2 is None:
        return None, None, None, None
    try:
        v = DB.XYZ(float(seg_p2.X - seg_p1.X), float(seg_p2.Y - seg_p1.Y), 0.0)
        seg_len = float(v.GetLength())
        if seg_len <= XY_TOL:
            return None, None, None, None
        seg_dir = v.Normalize()
    except Exception:
        return None, None, None, None

    try:
        corners = _bbox_corners_xy(bmin, bmax)
        if not corners:
            return None, None, None, None
        svals = []
        for c in corners:
            dv = DB.XYZ(float(c.X - seg_p1.X), float(c.Y - seg_p1.Y), 0.0)
            svals.append(float(dv.DotProduct(seg_dir)))
        lo = max(0.0, min(svals))
        hi = min(seg_len, max(svals))
        return lo, hi, seg_dir, seg_len
    except Exception:
        return None, None, None, None


def _wm_bbox_contains_point_on_segment_xy(pt_on_wall, bmin, bmax, seg_p1, seg_p2, tol_mm=30):
    if pt_on_wall is None:
        return False
    lo, hi, seg_dir, seg_len = _bbox_interval_on_segment_ft(bmin, bmax, seg_p1, seg_p2)
    if lo is None or hi is None or seg_dir is None or seg_len is None:
        return False
    if hi - lo <= mm_to_ft(50):
        return False
    try:
        s_pt = DB.XYZ(float(pt_on_wall.X - seg_p1.X), float(pt_on_wall.Y - seg_p1.Y), 0.0).DotProduct(seg_dir)
    except Exception:
        return False
    try:
        tol = mm_to_ft(tol_mm or 30)
    except Exception:
        tol = mm_to_ft(30)
    return (s_pt >= (lo - tol)) and (s_pt <= (hi + tol))


def _append_wm_bbox_candidates(candidates,
                              room,
                              room_bb,
                              room_center_xy,
                              z_test,
                              fixture,
                              wall_segments,
                              local_baths_clash,
                              local_sinks,
                              clash_buffer_ft,
                              sink_clear_ft,
                              priority,
                              max_wall_dist_ft):
    """Add candidates constrained to washing machine bbox projection on nearby boundary walls."""
    if candidates is None or room is None or fixture is None or not wall_segments:
        return
    bmin, bmax = getattr(fixture, 'bbox_min', None), getattr(fixture, 'bbox_max', None)
    if bmin is None or bmax is None:
        return
    c0 = getattr(fixture, 'center', None)
    if c0 is None:
        try:
            c0 = DB.XYZ((bmin.X + bmax.X) * 0.5, (bmin.Y + bmax.Y) * 0.5, 0.0)
        except Exception:
            return
    center_xy = DB.XYZ(float(c0.X), float(c0.Y), 0.0)

    try:
        maxd = float(max_wall_dist_ft or 0.0)
    except Exception:
        maxd = 0.0
    if maxd <= XY_TOL:
        maxd = mm_to_ft(1200)

    for p1, p2, wall in wall_segments:
        try:
            if (not isinstance(wall, DB.Wall)) or su._is_curtain_wall(wall):
                continue
        except Exception:
            continue

        # Only consider walls close to the washing machine
        try:
            cp = _closest_point_on_segment_xy(center_xy, p1, p2)
            if cp is None:
                continue
            d_perp = center_xy.DistanceTo(DB.XYZ(float(cp.X), float(cp.Y), 0.0))
            if d_perp > maxd:
                continue
        except Exception:
            continue

        lo, hi, seg_dir, seg_len = _bbox_interval_on_segment_ft(bmin, bmax, p1, p2)
        if lo is None or hi is None or seg_dir is None or seg_len is None:
            continue
        if hi - lo <= mm_to_ft(60):
            continue

        # Sample WM center projection first to keep the socket centered above WM.
        try:
            s_center = float(DB.XYZ(float(center_xy.X - p1.X), float(center_xy.Y - p1.Y), 0.0).DotProduct(seg_dir))
        except Exception:
            s_center = (lo + hi) * 0.5
        s_center = max(float(lo), min(float(hi), float(s_center)))
        # Also keep endpoints + middle for fallback.
        samples = [s_center, lo, hi, (lo + hi) * 0.5]
        seen = set()
        for s in samples:
            try:
                ss = float(s)
            except Exception:
                continue
            if ss < 0.0:
                ss = 0.0
            if ss > seg_len:
                ss = seg_len
            key = int(ss * 1000)
            if key in seen:
                continue
            seen.add(key)

            pt_wall = DB.XYZ(float(p1.X) + float(seg_dir.X) * ss, float(p1.Y) + float(seg_dir.Y) * ss, float(c0.Z))
            point_xy = DB.XYZ(float(pt_wall.X), float(pt_wall.Y), 0.0)

            # Block checks (use wall-edge point)
            blocked = False
            for bbmin, bbmax in (local_baths_clash or []):
                try:
                    d_b = _dist_point_to_rect_xy(point_xy, bbmin, bbmax)
                    if d_b is not None and d_b < clash_buffer_ft:
                        blocked = True
                        break
                except Exception:
                    continue
            if blocked:
                continue
            for sink in (local_sinks or []):
                try:
                    sc = sink.center
                    if sc is None:
                        sbmin, sbmax = sink.bbox_min, sink.bbox_max
                        sc = DB.XYZ((sbmin.X + sbmax.X) * 0.5, (sbmin.Y + sbmax.Y) * 0.5, 0.0) if (sbmin and sbmax) else None
                    if sc is None:
                        continue
                    d_s = point_xy.DistanceTo(DB.XYZ(float(sc.X), float(sc.Y), 0.0))
                    if d_s < sink_clear_ft:
                        blocked = True
                        break
                except Exception:
                    continue
            if blocked:
                continue

            # Inward point for room test; placement will use pt_wall
            pt_in = pt_wall
            try:
                pt_in = _push_point_inside_room(
                    room,
                    pt_wall,
                    wall_dir_xy=seg_dir,
                    room_center_xy=room_center_xy,
                    room_bb=room_bb,
                    z_test=z_test,
                    max_push_mm=200
                )
            except Exception:
                pt_in = pt_wall
            try:
                if z_test is not None and (not _is_point_in_room(room, DB.XYZ(float(pt_in.X), float(pt_in.Y), float(z_test)))):
                    continue
            except Exception:
                pass

            # Distance to fixture center (xy)
            try:
                dxy = center_xy.DistanceTo(point_xy)
            except Exception:
                dxy = 1e9

            candidates.append({
                'wall': wall,
                'point': pt_in,
                'point_on_wall': pt_wall,
                'wall_dir': seg_dir,
                'seg_p1': p1,
                'seg_p2': p2,
                'distance': dxy,
                'priority': priority,
                'kind': 'wm',
                'wm_bbox': True,
                'wm_bbox_min': bmin,
                'wm_bbox_max': bmax
            })


def _min_dist_to_rects_xy(pt_xy, rects):
    if pt_xy is None or not rects:
        return None
    best = None
    for bmin, bmax in rects or []:
        try:
            d = _dist_point_to_rect_xy(pt_xy, bmin, bmax)
        except Exception:
            d = None
        if d is None:
            continue
        if best is None or d < best:
            best = d
    return best


def _shift_wm_point_on_wall_towards_bath(room,
                                        pt_wall,
                                        seg_p1,
                                        seg_p2,
                                        room_center_xy,
                                        room_bb,
                                        z_test,
                                        wm_bbox_min,
                                        wm_bbox_max,
                                        local_baths,
                                        local_baths_clash,
                                        local_sinks,
                                        clash_buffer_ft,
                                        sink_clear_ft,
                                        shift_ft):
    if room is None or pt_wall is None or seg_p1 is None or seg_p2 is None:
        return None
    if not local_baths:
        return None
    try:
        sh = float(shift_ft or 0.0)
    except Exception:
        sh = 0.0
    if sh <= mm_to_ft(10):
        return None

    # Segment axis
    try:
        seg_vec = DB.XYZ(float(seg_p2.X - seg_p1.X), float(seg_p2.Y - seg_p1.Y), 0.0)
        seg_len = float(seg_vec.GetLength())
        if seg_len <= XY_TOL:
            return None
        seg_dir = seg_vec.Normalize()
    except Exception:
        return None

    # Current coordinate along segment
    try:
        s0 = float(DB.XYZ(float(pt_wall.X - seg_p1.X), float(pt_wall.Y - seg_p1.Y), 0.0).DotProduct(seg_dir))
    except Exception:
        return None

    lo = 0.0
    hi = seg_len
    if wm_bbox_min is not None and wm_bbox_max is not None:
        try:
            blo, bhi, _, _ = _bbox_interval_on_segment_ft(wm_bbox_min, wm_bbox_max, seg_p1, seg_p2)
        except Exception:
            blo, bhi = None, None
        if blo is not None and bhi is not None and bhi - blo > mm_to_ft(60):
            lo = max(lo, float(blo))
            hi = min(hi, float(bhi))
    if hi - lo <= mm_to_ft(60):
        return None

    def _pt_at_s(sval):
        try:
            s1 = float(sval)
        except Exception:
            return None
        if s1 < 0.0:
            s1 = 0.0
        if s1 > seg_len:
            s1 = seg_len
        return DB.XYZ(float(seg_p1.X) + float(seg_dir.X) * s1, float(seg_p1.Y) + float(seg_dir.Y) * s1, float(pt_wall.Z))

    def _is_ok(pw):
        if pw is None:
            return False
        pxy = DB.XYZ(float(pw.X), float(pw.Y), 0.0)
        # Clearance checks
        for bbmin, bbmax in (local_baths_clash or []):
            try:
                d_b = _dist_point_to_rect_xy(pxy, bbmin, bbmax)
                if d_b is not None and d_b < clash_buffer_ft:
                    return False
            except Exception:
                continue
        for sink in (local_sinks or []):
            try:
                sc = sink.center
                if sc is None:
                    sbmin, sbmax = sink.bbox_min, sink.bbox_max
                    sc = DB.XYZ((sbmin.X + sbmax.X) * 0.5, (sbmin.Y + sbmax.Y) * 0.5, 0.0) if (sbmin and sbmax) else None
                if sc is None:
                    continue
                d_s = pxy.DistanceTo(DB.XYZ(float(sc.X), float(sc.Y), 0.0))
                if d_s < sink_clear_ft:
                    return False
            except Exception:
                continue

        # Room test (use inward pushed point)
        try:
            pt_in = _push_point_inside_room(room, pw, wall_dir_xy=seg_dir, room_center_xy=room_center_xy, room_bb=room_bb, z_test=z_test, max_push_mm=200)
        except Exception:
            pt_in = pw
        try:
            if z_test is not None:
                if not _is_point_in_room(room, DB.XYZ(float(pt_in.X), float(pt_in.Y), float(z_test))):
                    return False
        except Exception:
            pass

        # WM bbox constraint
        try:
            if wm_bbox_min is not None and wm_bbox_max is not None:
                if not _wm_bbox_contains_point_on_segment_xy(pw, wm_bbox_min, wm_bbox_max, seg_p1, seg_p2):
                    return False
        except Exception:
            pass

        return True

    # Try shift distances (prefer exact 300mm, then smaller if necessary)
    try_steps = [sh, sh * 0.66, sh * 0.33]

    for step in try_steps:
        # Candidate s values clamped to allowed interval
        sp = max(lo, min(hi, s0 + step))
        sm = max(lo, min(hi, s0 - step))

        p_plus = _pt_at_s(sp)
        p_minus = _pt_at_s(sm)

        # Decide direction: move towards bath (smaller distance to bathtub bbox)
        d_plus = _min_dist_to_rects_xy(DB.XYZ(float(p_plus.X), float(p_plus.Y), 0.0), local_baths) if p_plus else None
        d_minus = _min_dist_to_rects_xy(DB.XYZ(float(p_minus.X), float(p_minus.Y), 0.0), local_baths) if p_minus else None

        prefs = []
        if d_plus is not None:
            prefs.append((d_plus, p_plus))
        if d_minus is not None:
            prefs.append((d_minus, p_minus))
        prefs = sorted(prefs, key=lambda x: x[0])

        for _, cand_pw in prefs:
            if cand_pw is None:
                continue
            if abs(float(cand_pw.X) - float(pt_wall.X)) <= XY_TOL and abs(float(cand_pw.Y) - float(pt_wall.Y)) <= XY_TOL:
                continue
            if _is_ok(cand_pw):
                return cand_pw

    return None


def _min_dist_to_points_xy(pt_xy, points):
    if pt_xy is None or not points:
        return None
    best = None
    for p in points or []:
        try:
            d = pt_xy.DistanceTo(DB.XYZ(float(p.X), float(p.Y), 0.0))
        except Exception:
            d = None
        if d is None:
            continue
        if best is None or d < best:
            best = d
    return best


def _shift_wm_point_on_wall_away_from_door(room,
                                          pt_wall,
                                          seg_p1,
                                          seg_p2,
                                          room_center_xy,
                                          room_bb,
                                          z_test,
                                          wm_bbox_min,
                                          wm_bbox_max,
                                          local_doors,
                                          local_baths_clash,
                                          local_sinks,
                                          clash_buffer_ft,
                                          sink_clear_ft,
                                          shift_ft):
    if room is None or pt_wall is None or seg_p1 is None or seg_p2 is None:
        return None
    if not local_doors:
        return None
    try:
        sh = float(shift_ft or 0.0)
    except Exception:
        sh = 0.0
    if sh <= mm_to_ft(10):
        return None

    # Segment axis
    try:
        seg_vec = DB.XYZ(float(seg_p2.X - seg_p1.X), float(seg_p2.Y - seg_p1.Y), 0.0)
        seg_len = float(seg_vec.GetLength())
        if seg_len <= XY_TOL:
            return None
        seg_dir = seg_vec.Normalize()
    except Exception:
        return None

    # Current coordinate along segment
    try:
        s0 = float(DB.XYZ(float(pt_wall.X - seg_p1.X), float(pt_wall.Y - seg_p1.Y), 0.0).DotProduct(seg_dir))
    except Exception:
        return None

    lo = 0.0
    hi = seg_len
    if wm_bbox_min is not None and wm_bbox_max is not None:
        try:
            blo, bhi, _, _ = _bbox_interval_on_segment_ft(wm_bbox_min, wm_bbox_max, seg_p1, seg_p2)
        except Exception:
            blo, bhi = None, None
        if blo is not None and bhi is not None and bhi - blo > mm_to_ft(60):
            lo = max(lo, float(blo))
            hi = min(hi, float(bhi))
    if hi - lo <= mm_to_ft(60):
        return None

    p0_xy = DB.XYZ(float(pt_wall.X), float(pt_wall.Y), 0.0)
    d0 = _min_dist_to_points_xy(p0_xy, local_doors)

    def _pt_at_s(sval):
        try:
            s1 = float(sval)
        except Exception:
            return None
        if s1 < 0.0:
            s1 = 0.0
        if s1 > seg_len:
            s1 = seg_len
        return DB.XYZ(float(seg_p1.X) + float(seg_dir.X) * s1, float(seg_p1.Y) + float(seg_dir.Y) * s1, float(pt_wall.Z))

    def _is_ok(pw):
        if pw is None:
            return False
        pxy = DB.XYZ(float(pw.X), float(pw.Y), 0.0)
        # Clearance checks
        for bbmin, bbmax in (local_baths_clash or []):
            try:
                d_b = _dist_point_to_rect_xy(pxy, bbmin, bbmax)
                if d_b is not None and d_b < clash_buffer_ft:
                    return False
            except Exception:
                continue
        for sink in (local_sinks or []):
            try:
                sc = sink.center
                if sc is None:
                    sbmin, sbmax = sink.bbox_min, sink.bbox_max
                    sc = DB.XYZ((sbmin.X + sbmax.X) * 0.5, (sbmin.Y + sbmax.Y) * 0.5, 0.0) if (sbmin and sbmax) else None
                if sc is None:
                    continue
                d_s = pxy.DistanceTo(DB.XYZ(float(sc.X), float(sc.Y), 0.0))
                if d_s < sink_clear_ft:
                    return False
            except Exception:
                continue

        # Room test (use inward pushed point)
        try:
            pt_in = _push_point_inside_room(room, pw, wall_dir_xy=seg_dir, room_center_xy=room_center_xy, room_bb=room_bb, z_test=z_test, max_push_mm=200)
        except Exception:
            pt_in = pw
        try:
            if z_test is not None:
                if not _is_point_in_room(room, DB.XYZ(float(pt_in.X), float(pt_in.Y), float(z_test))):
                    return False
        except Exception:
            pass

        # WM bbox constraint
        try:
            if wm_bbox_min is not None and wm_bbox_max is not None:
                if not _wm_bbox_contains_point_on_segment_xy(pw, wm_bbox_min, wm_bbox_max, seg_p1, seg_p2):
                    return False
        except Exception:
            pass

        return True

    # Try shift distances (prefer exact 300mm, then smaller if necessary)
    try_steps = [sh, sh * 0.66, sh * 0.33]

    for step in try_steps:
        sp = max(lo, min(hi, s0 + step))
        sm = max(lo, min(hi, s0 - step))

        p_plus = _pt_at_s(sp)
        p_minus = _pt_at_s(sm)

        dd_plus = _min_dist_to_points_xy(DB.XYZ(float(p_plus.X), float(p_plus.Y), 0.0), local_doors) if p_plus else None
        dd_minus = _min_dist_to_points_xy(DB.XYZ(float(p_minus.X), float(p_minus.Y), 0.0), local_doors) if p_minus else None

        prefs = []
        if dd_plus is not None:
            prefs.append((dd_plus, p_plus))
        if dd_minus is not None:
            prefs.append((dd_minus, p_minus))
        # Prefer farther from door
        prefs = sorted(prefs, key=lambda x: -float(x[0]))

        for dd, cand_pw in prefs:
            if cand_pw is None:
                continue
            if abs(float(cand_pw.X) - float(pt_wall.X)) <= XY_TOL and abs(float(cand_pw.Y) - float(pt_wall.Y)) <= XY_TOL:
                continue
            if d0 is not None:
                try:
                    min_improve = max(mm_to_ft(50), float(sh) * 0.33)
                    if float(dd) < float(d0) + float(min_improve):
                        continue
                except Exception:
                    pass
            if _is_ok(cand_pw):
                return cand_pw

    return None


def _shift_point_on_wall_off_segment_end(room,
                                        pt_wall,
                                        seg_p1,
                                        seg_p2,
                                        room_center_xy,
                                        room_bb,
                                        z_test,
                                        local_baths_clash,
                                        local_sinks,
                                        clash_buffer_ft,
                                        sink_clear_ft,
                                        end_clear_ft,
                                        wm_bbox_min=None,
                                        wm_bbox_max=None):
    if room is None or pt_wall is None or seg_p1 is None or seg_p2 is None:
        return None
    try:
        clr = float(end_clear_ft or 0.0)
    except Exception:
        clr = 0.0
    if clr <= mm_to_ft(10):
        return None

    # Segment axis
    try:
        seg_vec = DB.XYZ(float(seg_p2.X - seg_p1.X), float(seg_p2.Y - seg_p1.Y), 0.0)
        seg_len = float(seg_vec.GetLength())
        if seg_len <= XY_TOL:
            return None
        seg_dir = seg_vec.Normalize()
    except Exception:
        return None

    # Current coordinate along segment
    try:
        s0 = float(DB.XYZ(float(pt_wall.X - seg_p1.X), float(pt_wall.Y - seg_p1.Y), 0.0).DotProduct(seg_dir))
    except Exception:
        return None

    lo = 0.0
    hi = seg_len
    if wm_bbox_min is not None and wm_bbox_max is not None:
        try:
            blo, bhi, _, _ = _bbox_interval_on_segment_ft(wm_bbox_min, wm_bbox_max, seg_p1, seg_p2)
        except Exception:
            blo, bhi = None, None
        if blo is not None and bhi is not None and bhi - blo > mm_to_ft(60):
            lo = max(lo, float(blo))
            hi = min(hi, float(bhi))
    if hi - lo <= mm_to_ft(60):
        return None

    s_min = float(lo) + float(clr)
    s_max = float(hi) - float(clr)
    if s_max <= s_min + mm_to_ft(1):
        return None

    s1 = max(s_min, min(s_max, float(s0)))
    if abs(float(s1) - float(s0)) <= mm_to_ft(1):
        return None

    pw = DB.XYZ(float(seg_p1.X) + float(seg_dir.X) * s1, float(seg_p1.Y) + float(seg_dir.Y) * s1, float(pt_wall.Z))
    pxy = DB.XYZ(float(pw.X), float(pw.Y), 0.0)

    # Clearance checks
    for bbmin, bbmax in (local_baths_clash or []):
        try:
            d_b = _dist_point_to_rect_xy(pxy, bbmin, bbmax)
            if d_b is not None and d_b < clash_buffer_ft:
                return None
        except Exception:
            continue
    for sink in (local_sinks or []):
        try:
            sc = sink.center
            if sc is None:
                sbmin, sbmax = sink.bbox_min, sink.bbox_max
                sc = DB.XYZ((sbmin.X + sbmax.X) * 0.5, (sbmin.Y + sbmax.Y) * 0.5, 0.0) if (sbmin and sbmax) else None
            if sc is None:
                continue
            d_s = pxy.DistanceTo(DB.XYZ(float(sc.X), float(sc.Y), 0.0))
            if d_s < sink_clear_ft:
                return None
        except Exception:
            continue

    # Room test (use inward pushed point)
    try:
        pt_in = _push_point_inside_room(room, pw, wall_dir_xy=seg_dir, room_center_xy=room_center_xy, room_bb=room_bb, z_test=z_test, max_push_mm=200)
    except Exception:
        pt_in = pw
    try:
        if z_test is not None:
            if not _is_point_in_room(room, DB.XYZ(float(pt_in.X), float(pt_in.Y), float(z_test))):
                return None
    except Exception:
        pass

    # WM bbox constraint (defensive)
    try:
        if wm_bbox_min is not None and wm_bbox_max is not None:
            if not _wm_bbox_contains_point_on_segment_xy(pw, wm_bbox_min, wm_bbox_max, seg_p1, seg_p2):
                return None
    except Exception:
        pass

    return pw


def _bboxes_in_room(rects, room, padding_ft=2.0):
    if not rects or room is None:
        return []
    room_bb = None
    try:
        room_bb = room.get_BoundingBox(None)
    except Exception:
        room_bb = None
    if not room_bb:
        return rects
    min_exp = DB.XYZ(room_bb.Min.X - padding_ft, room_bb.Min.Y - padding_ft, 0.0)
    max_exp = DB.XYZ(room_bb.Max.X + padding_ft, room_bb.Max.Y + padding_ft, 0.0)
    filtered = []
    for rect in rects:
        bmin, bmax = rect
        if _bbox_intersects_xy(bmin, bmax, min_exp, max_exp):
            filtered.append(rect)
    return filtered


def _ensure_placeholders(points, fixtures, marker_label, placeholder_kind=None):
    if not points:
        return fixtures
    placeholders = list(fixtures)
    existing_idx = su._XYZIndex(cell_ft=0.5)
    for fx in fixtures:
        if getattr(fx, 'kind', None) is None:
            try:
                fx.kind = placeholder_kind or 'wm'
            except Exception:
                pass
        existing_idx.add(fx.center.X, fx.center.Y, 0.0)
    buffer_ft = mm_to_ft(350)
    for pt in points:
        if existing_idx.has_near(pt.X, pt.Y, 0.0, mm_to_ft(50)):
            continue
        bbox_min = DB.XYZ(pt.X - buffer_ft, pt.Y - buffer_ft, 0.0)
        bbox_max = DB.XYZ(pt.X + buffer_ft, pt.Y + buffer_ft, 0.0)
        placeholders.append(Fixture2D(None, pt, bbox_min, bbox_max, kind=placeholder_kind or 'wm'))
        existing_idx.add(pt.X, pt.Y, 0.0)
    if placeholders and len(placeholders) > len(fixtures):
        output.print_md('⚠️ Добавлено {0} фиктивных {1} (нет BoundingBox).'.format(len(placeholders) - len(fixtures), marker_label))
    return placeholders

def _build_fixtures(link_doc, rules):
    sink_pts = su._collect_sinks_points(link_doc, rules)
    wm_pts = su._collect_washing_machines_points(link_doc, rules)

    sink_keywords = rules.get('sink_family_keywords', []) or [u'раков', u'умыв', u'sink', u'washbasin', u'мойк', u'basin', u'lavatory']
    wm_keywords = rules.get('washing_machine_keywords', []) or [u'стирал', u'washing', u'machine']

    sink_candidates = _collect_fixture_candidates(link_doc, sink_keywords, [DB.BuiltInCategory.OST_PlumbingFixtures], fixture_kind='sink')
    wm_categories = [
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_PipeAccessory,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture
    ]
    wm_candidates = _collect_fixture_candidates(link_doc, wm_keywords, wm_categories, fixture_kind='wm')

    sink_fixtures = _filter_fixtures_by_points(sink_candidates, sink_pts, tolerance_ft=mm_to_ft(150))
    wm_fixtures = _filter_fixtures_by_points(wm_candidates, wm_pts, tolerance_ft=mm_to_ft(150))

    # If we have WM marks/points (e.g. tags "СМ") but no keyword-matched geometry, try
    # a targeted fallback: scan the same categories without keyword filtering and pick
    # elements near the points. This yields real BoundingBox for bbox-based placement.
    if wm_pts and (not wm_fixtures):
        try:
            wm_candidates_any = _collect_fixture_candidates(link_doc, [], wm_categories, fixture_kind='wm')
            wm_fixtures_any = _filter_fixtures_by_points(wm_candidates_any, wm_pts, tolerance_ft=mm_to_ft(300))
            if wm_fixtures_any:
                wm_fixtures = wm_fixtures_any
        except Exception:
            pass

    sink_fixtures = _ensure_placeholders(sink_pts, sink_fixtures, 'раковин', placeholder_kind='sink')
    wm_fixtures = _ensure_placeholders(wm_pts, wm_fixtures, 'стиральных машин', placeholder_kind='wm')

    return sink_fixtures, wm_fixtures


def main():
    gc.collect()
    output.print_md('# 05. Розетки: Ванная / Санузел')

    rules = config_loader.load_rules()
    comment_tag = rules.get('comment_tag', 'AUTO_EOM')
    comment_value = '{0}:SOCKET_WET'.format(comment_tag)

    socket_height_ft = mm_to_ft(rules.get('socket_height_wet_mm', 1300) or 1300)
    # In wet rooms we often need sockets on opposite sides of the same wall.
    # Using the global 300mm dedupe can incorrectly suppress those.
    dedupe_ft = mm_to_ft(rules.get('wet_socket_dedupe_radius_mm', 50) or 50)
    batch_size = int(rules.get('batch_size', 25) or 25)
    ray_limit_ft = mm_to_ft(1000)
    bath_buffer_ft = mm_to_ft(600)
    # Safety distances (per rules): 600mm from bathtub edge and 600mm from sink axis
    clash_buffer_ft = mm_to_ft(rules.get('wet_bath_clear_mm', 600) or 600)
    sink_clear_ft = mm_to_ft(rules.get('wet_sink_clear_mm', 600) or 600)
    raycast_slack_ft = mm_to_ft(rules.get('wet_raycast_slack_mm', 400) or 400)

    wall_end_clear_ft = mm_to_ft(rules.get('wet_wall_end_clear_mm', 100) or 100)

    wm_enforce_bbox = bool(rules.get('wet_wm_enforce_bbox', True))
    wm_wall_max_dist_ft = mm_to_ft(rules.get('wet_wm_wall_max_dist_mm', 1200) or 1200)
    wm_shift_bath_ft = mm_to_ft(rules.get('wet_wm_shift_towards_bath_mm', 300) or 300)
    wm_shift_door_ft = mm_to_ft(rules.get('wet_wm_shift_away_from_door_mm', 300) or 300)
    wm_shift_door_trigger_ft = mm_to_ft(rules.get('wet_wm_shift_away_from_door_trigger_mm', 700) or 700)

    use_screenshot_scoring = bool(rules.get('wet_use_screenshot_scoring', True)) and _HAS_DRAWING
    save_room_screens = bool(rules.get('wet_save_room_screens', True))
    show_screens_in_output = bool(rules.get('wet_show_screens_in_output', True))
    mark_room_screens = bool(rules.get('wet_mark_screens', True)) and _HAS_DRAWING_MARK
    want_room_screens = bool(use_screenshot_scoring or save_room_screens or show_screens_in_output)
    # 0 means "show all" (useful for validation)
    show_screens_limit = int(rules.get('wet_show_screens_limit', 0) or 0)
    ink_radius_ft = mm_to_ft(rules.get('wet_ink_radius_mm', 250) or 250)
    screen_px = int(rules.get('wet_screen_pixel_size', _SCREEN_PIXEL_SIZE) or _SCREEN_PIXEL_SIZE)
    screen_pad_ft = mm_to_ft(rules.get('wet_screen_pad_mm', _SCREEN_PAD_MM) or _SCREEN_PAD_MM)
    slide_step_ft = mm_to_ft(rules.get('wet_slide_step_mm', 300) or 300)
    slide_max_ft = mm_to_ft(rules.get('wet_slide_max_mm', 2400) or 2400)

    cfg = script.get_config()
    fams = rules.get('family_type_names', {})
    wet_names = []
    # Prioritize Double IP44 (Embedded then Surface), then Single IP44
    priority_names = [
        u'TSL_EF_о_СТ_в_IP44_Рзт_1P+N+PE_2п', 
        u'TSL_EF_т_СТ_н_IP44_Рзт_1P+N+PE_2п',
        u'TSL_EF_о_СТ_в_IP44_Рзт_1P+N+PE'
    ]
    wet_names.extend(priority_names)
    
    fam_wet = fams.get('socket_wet')
    if isinstance(fam_wet, (list, tuple)):
        wet_names.extend([n for n in fam_wet if n not in wet_names])
    elif fam_wet:
        wet_names.append(fam_wet)
    sym_wet, lbl_wet, _ = su._pick_socket_symbol(doc, cfg, wet_names, cache_prefix='socket_wet')

    def _sym_pt(sym):
        try:
            pt = sym.Family.FamilyPlacementType if sym and sym.Family else None
            return pt, str(pt)
        except Exception:
            return None, 'Unknown'

    def _is_link_placeable(sym):
        pt, pt_name = _sym_pt(sym)
        try:
            if pt == DB.FamilyPlacementType.OneLevelBased:
                return True
        except Exception:
            pass
        try:
            if pt == DB.FamilyPlacementType.WorkPlaneBased:
                return True
        except Exception:
            pass
        try:
            if pt == DB.FamilyPlacementType.FaceBased:
                return True
        except Exception:
            pass
        return 'face' in (pt_name or '').lower()

    def _auto_pick_link_placeable_socket(prefer_texts=None, scan_cap=20000):
        prefer_norm = [su._norm(x) for x in (prefer_texts or []) if x]
        best = None
        best_score = -1e9
        for bic in (DB.BuiltInCategory.OST_ElectricalFixtures, DB.BuiltInCategory.OST_ElectricalEquipment):
            scanned = 0
            for s in placement_engine.iter_family_symbols(doc, category_bic=bic, limit=None):
                scanned += 1
                if scan_cap and scanned > int(scan_cap):
                    break
                if not _is_link_placeable(s):
                    continue
                try:
                    lbl = placement_engine.format_family_type(s)
                except Exception:
                    lbl = ''
                t = su._norm(lbl)
                if not t:
                    continue

                # Avoid picking non-socket families (e.g. IP44 switches)
                if ('рзт' not in t) and ('розет' not in t) and ('socket' not in t) and ('outlet' not in t):
                    continue
                score = 0
                if 'ip44' in t:
                    score += 50
                if 'ip20' in t:
                    score -= 5
                if ('рзт' in t) or ('розет' in t) or ('socket' in t) or ('outlet' in t) or ('tsl_ef' in t):
                    score += 20
                for tok in prefer_norm:
                    try:
                        if tok and tok in t:
                            score += 5
                    except Exception:
                        continue
                if best is None or score > best_score:
                    best, best_score = s, score
        return best

    used_general_fallback = False
    if not sym_wet:
        fallback = fams.get('socket_general') or fams.get('power_socket')
        sym_wet, lbl_wet, _ = su._pick_socket_symbol(doc, cfg, fallback, cache_prefix='socket_general')
        used_general_fallback = bool(sym_wet)
        if not sym_wet:
            alert('Не найден тип розетки (IP44). Загрузите семейство TSL_EF IP44 (Face/WorkPlane/OneLevel).')
            return

    # Validate: in linked-host workflow we need FaceBased or point-based families.
    pt_enum, pt_name = _sym_pt(sym_wet)
    try:
        lbl_show = lbl_wet or placement_engine.format_family_type(sym_wet)
    except Exception:
        lbl_show = getattr(sym_wet, 'Name', u'')
    output.print_md(u'Тип розетки: **{0}**  `[{1}]`'.format(lbl_show, pt_name))

    if not _is_link_placeable(sym_wet):
        output.print_md(u'⚠️ Выбранный тип розетки не поддерживает размещение по грани стен из связи (FamilyPlacementType: `{0}`).'.format(pt_name))

        # Try to auto-pick a link-placeable IP44 socket if one exists.
        sym_alt = _auto_pick_link_placeable_socket(wet_names)
        if sym_alt is not None:
            sym_wet = sym_alt
            try:
                lbl_wet = placement_engine.format_family_type(sym_wet)
            except Exception:
                lbl_wet = None
            pt_enum, pt_name = _sym_pt(sym_wet)
            output.print_md(u'✅ Подобран альтернативный тип: **{0}**  `[{1}]`'.format(lbl_wet or getattr(sym_wet, 'Name', u''), pt_name))
        else:
            fallback = fams.get('socket_general') or fams.get('power_socket')
            sym_fb, lbl_fb, _ = su._pick_socket_symbol(doc, cfg, fallback, cache_prefix='socket_general')
            if not sym_fb:
                alert('Текущий тип розетки нельзя разместить по грани (связь), и fallback не найден.')
                return
            if not _is_link_placeable(sym_fb):
                _pt2, _pt2_name = _sym_pt(sym_fb)
                alert('Fallback тип розетки тоже не поддерживает размещение по грани стен из связи (FamilyPlacementType: {0}).\nНужно семейство FaceBased / WorkPlaneBased / OneLevelBased.'.format(_pt2_name))
                return
            sym_wet = sym_fb
            lbl_wet = lbl_fb
            used_general_fallback = True

    if used_general_fallback:
        output.print_md('**Внимание:** Используется общий тип розетки (fallback, IP20).')

    su._store_symbol_id(cfg, 'last_socket_wet_symbol_id', sym_wet)
    su._store_symbol_unique_id(cfg, 'last_socket_wet_symbol_uid', sym_wet)
    script.save_config()

    link_inst = su._select_link_instance_ru(doc, 'Выберите связь АР')
    if not link_inst:
        return
    try:
        if not link_inst.IsValidObject:
            alert('Связь недоступна. Повторите запуск.')
            return
    except Exception:
        return

    link_doc = link_reader.get_link_doc(link_inst)
    if not link_doc:
        alert('Не удалось получить документ связи.')
        return

    raw_rooms = su._get_all_linked_rooms(link_doc)
    wet_patterns = rules.get('wet_room_name_patterns', []) or rules.get('switch_wet_room_name_patterns', [])
    wet_rx = su._compile_patterns(wet_patterns)

    rooms = []
    for room in raw_rooms:
        txt = su._room_text(room)
        if su._match_any(wet_rx, txt):
            rooms.append(room)

    if not rooms:
        alert('Не найдено влажных помещений (по шаблону имен).')
        return

    sink_fixtures, wm_fixtures = _build_fixtures(link_doc, rules)
    door_points = _collect_door_points(link_doc)
    bath_raw = su._collect_bathtubs_data(link_doc)
    bath_rects = []
    bath_clash_rects = []
    for _, bmin, bmax in bath_raw:
        try:
            if bmin is None or bmax is None:
                continue
            bmin2 = DB.XYZ(min(bmin.X, bmax.X), min(bmin.Y, bmax.Y), 0.0)
            bmax2 = DB.XYZ(max(bmin.X, bmax.X), max(bmin.Y, bmax.Y), 0.0)
            bath_rects.append((bmin2, bmax2))
            bath_clash_rects.append((bmin2, bmax2))
        except Exception:
            continue

    # --------------------------------------------------------------------------------
    # FIX for "Missing Sinks": If 0 sinks found, maybe family names are tricky.
    # Try adding OST_GenericModel to sink search if not already? 
    # (Actually we only scan PlumbingFixtures for sinks in _build_fixtures).
    # Let's expand sink search categories here if count is 0.
    if len(sink_fixtures) == 0:
        sink_keywords = rules.get('sink_family_keywords', []) or [u'раков', u'умыв', u'sink', u'washbasin', u'мойк', u'basin', u'lavatory']
        # Add GenericModel and Furniture
        more_cats = [DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_Furniture]
        more_candidates = _collect_fixture_candidates(link_doc, sink_keywords, more_cats, fixture_kind='sink')
        sink_pts = su._collect_sinks_points(link_doc, rules) # This only does Plumbing.
        # We need points for filtering. 
        # _collect_fixture_candidates gets center points itself.
        # But _filter_fixtures_by_points filters candidates by `sink_pts`.
        # If `sink_pts` is empty, filter does nothing (returns original list) OR returns empty?
        # Check `_filter_fixtures_by_points`: `if not points: return fixtures`
        # So we just need candidates.
        sink_fixtures.extend(more_candidates)
    
    # --------------------------------------------------------------------------------
    # FIX: Collect Boilers (BK) and Towel Rails as targets
    # --------------------------------------------------------------------------------
    boiler_pts = su._collect_boilers_points(link_doc)
    rail_pts = su._collect_towel_rails_points(link_doc)
    
    # For geometry candidates, use only strong keywords (BK/БК marks are handled via points/placeholders).
    boiler_keywords = [
        u'boiler', u'boyler',
        u'water heater', u'waterheater', u'water_heater',
        u'vodonagrevatel', u'водонагреватель', u'водонагрев', u'водонагр',
        u'бойлер'
    ]
    rail_keywords = [u'polotence', u'sushitel', u'towel', u'dryer', u'сушител', u'полотенце']
    
    extra_cats = [
        DB.BuiltInCategory.OST_PlumbingFixtures,
        DB.BuiltInCategory.OST_SpecialityEquipment,
        DB.BuiltInCategory.OST_MechanicalEquipment,
        DB.BuiltInCategory.OST_PipeAccessory,
        DB.BuiltInCategory.OST_GenericModel,
        DB.BuiltInCategory.OST_Furniture
    ]
    
    boiler_candidates = _collect_fixture_candidates(link_doc, boiler_keywords, extra_cats, fixture_kind='boiler')
    rail_candidates = _collect_fixture_candidates(link_doc, rail_keywords, extra_cats, fixture_kind='rail')
    
    boiler_fixtures = _filter_fixtures_by_points(boiler_candidates, boiler_pts, tolerance_ft=mm_to_ft(150))
    rail_fixtures = _filter_fixtures_by_points(rail_candidates, rail_pts, tolerance_ft=mm_to_ft(150))
    
    # Merge Boilers and Towel Rails into WM list for unified processing
    # They will be treated as target points for socket placement
    wm_fixtures.extend(boiler_fixtures)
    wm_fixtures.extend(rail_fixtures)
    
    # Also ensure placeholders for Boilers/Rails if they were found by points but no geometry
    before = len(wm_fixtures)
    wm_fixtures = _ensure_placeholders(boiler_pts, wm_fixtures, 'бойлеров', placeholder_kind='boiler')
    added_boiler_ph = max(len(wm_fixtures) - before, 0)
    before = len(wm_fixtures)
    wm_fixtures = _ensure_placeholders(rail_pts, wm_fixtures, 'полотенцесушителей', placeholder_kind='rail')
    added_rail_ph = max(len(wm_fixtures) - before, 0)

    output.print_md('BK/Бойлер: точки **{0}**, эл-ты **{1}**, плейсхолдеры **{2}**; Полотенцесуш.: точки **{3}**, эл-ты **{4}**, плейсхолдеры **{5}**'.format(
        len(boiler_pts), len(boiler_fixtures), added_boiler_ph,
        len(rail_pts), len(rail_fixtures), added_rail_ph
    ))

    output.print_md('Помещений: **{0}**, ванн: **{1}**, раковин: **{2}**, стиральных машин/бойлеров: **{3}**'.format(
        len(rooms), len(bath_raw), len(sink_fixtures), len(wm_fixtures)
    ))

    # Convenience: show screenshots for all rooms when limit is 0 (or negative).
    if show_screens_in_output and show_screens_limit <= 0:
        show_screens_limit = len(rooms)

    t = link_reader.get_total_transform(link_inst)
    idx = su._XYZIndex(cell_ft=5.0)

    screens_folder = None
    view_cache = {}
    view_prepped = set()
    screens_shown = 0
    if want_room_screens:
        screens_folder = _get_temp_screens_folder()
        if show_screens_in_output:
            try:
                output.print_md('Скрины плана: `{0}`'.format(screens_folder))
            except Exception:
                pass

    sym_flags = {}
    sid = sym_wet.Id.IntegerValue
    placement_type = None
    try:
        placement_type = sym_wet.Family.FamilyPlacementType
    except Exception:
        placement_type = None
    is_wp = placement_type == DB.FamilyPlacementType.WorkPlaneBased
    is_ol = placement_type == DB.FamilyPlacementType.OneLevelBased
    sym_flags[sid] = (is_wp, is_ol)

    # For point-based families (OneLevel/WorkPlane) strict hosting can incorrectly suppress placement.
    strict_hosting_mode = True
    if is_wp or is_ol:
        strict_hosting_mode = False
        output.print_md(u'**Внимание:** тип розетки OneLevel/WorkPlane - размещение будет без хоста.')

    sp_cache = {}
    pending = []
    created = 0
    total_face = 0
    total_wp = 0
    total_ol = 0
    total_verified = 0 # New
    total_skipped_noface = 0
    total_skipped_noplace = 0
    wm_processed = 0
    wm_skipped = 0

    boundary_opts = DB.SpatialElementBoundaryOptions()
    directions = [
        DB.XYZ(1.0, 0.0, 0.0), DB.XYZ(-1.0, 0.0, 0.0),
        DB.XYZ(0.0, 1.0, 0.0), DB.XYZ(0.0, -1.0, 0.0),
        DB.XYZ(0.707, 0.707, 0.0), DB.XYZ(-0.707, -0.707, 0.0),
        DB.XYZ(0.707, -0.707, 0.0), DB.XYZ(-0.707, 0.707, 0.0)
    ]

    with forms.ProgressBar(title='05. Розетки (санузлы)...', cancellable=True) as pb:
        pb.max_value = len(rooms)
        for idx_room, room in enumerate(rooms):
            if pb.cancelled:
                break
            pb.update_progress(idx_room, pb.max_value)

            wall_segments = get_room_boundary_segments_2d(room, boundary_opts)
            if not wall_segments:
                try:
                    output.print_md(u'⚠️ {0}: пропуск — нет сегментов стен в границах помещения (границы не Wall/RoomBounding).'.format(su._room_text(room)))
                except Exception:
                    pass
                continue

            local_wm = _fixtures_in_room(wm_fixtures, room)
            
            # ------------------------------------------------------------------------
            # FIX for "Skipped Rooms": If no WM, don't skip!
            # Initialize candidates list.
            # ------------------------------------------------------------------------
            candidates = [] 
            
            local_sinks = _fixtures_in_room(sink_fixtures, room)
            local_baths = _bboxes_in_room(bath_rects, room)
            local_baths_clash = _bboxes_in_room(bath_clash_rects, room)
            local_doors = _points_in_room(door_points, room)

            base_z = su._room_level_elevation_ft(room, link_doc)

            room_bb = None
            room_center_xy = None
            room_z_test = None
            try:
                room_bb = room.get_BoundingBox(None)
                if room_bb:
                    room_center_xy = DB.XYZ((room_bb.Min.X + room_bb.Max.X) * 0.5, (room_bb.Min.Y + room_bb.Max.Y) * 0.5, 0.0)
                    try:
                        room_z_test = float(room_bb.Min.Z + room_bb.Max.Z) * 0.5
                    except Exception:
                        room_z_test = None
            except Exception:
                room_bb = None
                room_center_xy = None
                room_z_test = None

            # Rule: if there is a washing machine in the room, we must place the socket within
            # its plan bounds (projection to a nearby boundary wall). This also keeps it on wall edge.
            local_wms = []
            try:
                for fx in (local_wm or []):
                    try:
                        if str(getattr(fx, 'kind', '')).lower() == 'wm':
                            local_wms.append(fx)
                    except Exception:
                        continue
            except Exception:
                local_wms = []
            if wm_enforce_bbox and local_wms:
                for fx in local_wms:
                    try:
                        _append_wm_bbox_candidates(
                            candidates,
                            room,
                            room_bb,
                            room_center_xy,
                            room_z_test,
                            fx,
                            wall_segments,
                            local_baths_clash,
                            local_sinks,
                            clash_buffer_ft,
                            sink_clear_ft,
                            _fixture_priority('wm'),
                            wm_wall_max_dist_ft
                        )
                    except Exception:
                        pass

            # 1. Try Raycasting from WMs/Boilers/Rails (Priority)
            if local_wm:
                for fixture in local_wm:
                    bbox_min, bbox_max = fixture.bbox_min, fixture.bbox_max
                    if not bbox_min or not bbox_max:
                        continue
                    center = DB.XYZ(
                        (bbox_min.X + bbox_max.X) * 0.5,
                        (bbox_min.Y + bbox_max.Y) * 0.5,
                        fixture.center.Z if fixture.center else base_z
                    )

                    # Special case: boiler/rail placeholders (often BK text/annotation).
                    # Pick the boundary wall on the same side as the placeholder by casting a ray from
                    # outside the room back to its center.
                    try:
                        k0 = (getattr(fixture, 'kind', None) or '').lower()
                    except Exception:
                        k0 = ''
                    if k0 in ('boiler', 'rail') and getattr(fixture, 'element', None) is None and room_center_xy is not None:
                        try:
                            # First try: project the placeholder point to the nearest boundary wall.
                            best_proj = None
                            for p1, p2, wall in wall_segments:
                                try:
                                    if (not isinstance(wall, DB.Wall)) or su._is_curtain_wall(wall):
                                        continue
                                except Exception:
                                    continue
                                proj = _closest_point_on_segment_xy(center, p1, p2)
                                if proj is None:
                                    continue
                                try:
                                    dxy = DB.XYZ(float(center.X), float(center.Y), 0.0).DistanceTo(DB.XYZ(float(proj.X), float(proj.Y), 0.0))
                                except Exception:
                                    dxy = 1e9
                                if best_proj is None or dxy < best_proj['distance']:
                                    try:
                                        wdir = DB.XYZ(float(p2.X - p1.X), float(p2.Y - p1.Y), 0.0)
                                        wdir = wdir.Normalize() if wdir.GetLength() > XY_TOL else None
                                    except Exception:
                                        wdir = None
                                    best_proj = {'wall': wall, 'point': proj, 'wall_dir': wdir, 'distance': dxy, 'seg_p1': p1, 'seg_p2': p2}

                            if best_proj and best_proj.get('wall_dir') is not None:
                                wall = best_proj['wall']
                                point_xy = best_proj['point']
                                blocked = False
                                for bmin, bmax in local_baths_clash:
                                    try:
                                        d_b = _dist_point_to_rect_xy(point_xy, bmin, bmax)
                                        if d_b is not None and d_b < clash_buffer_ft:
                                            blocked = True
                                            break
                                    except Exception:
                                        continue
                                if not blocked:
                                    for sink in local_sinks:
                                        try:
                                            sc = sink.center
                                            if sc is None:
                                                bmin, bmax = sink.bbox_min, sink.bbox_max
                                                sc = DB.XYZ((bmin.X + bmax.X) * 0.5, (bmin.Y + bmax.Y) * 0.5, 0.0) if (bmin and bmax) else None
                                            if sc is None:
                                                continue
                                            d_s = point_xy.DistanceTo(DB.XYZ(sc.X, sc.Y, 0.0))
                                            if d_s < sink_clear_ft:
                                                blocked = True
                                                break
                                        except Exception:
                                            continue
                                if not blocked:
                                    hit_pt = point_xy
                                    try:
                                        hit_pt = _push_point_inside_room(
                                            room,
                                            point_xy,
                                            in_dir_xy=(room_center_xy - point_xy),
                                            wall_dir_xy=best_proj.get('wall_dir'),
                                            room_center_xy=room_center_xy,
                                            room_bb=room_bb,
                                            z_test=room_z_test
                                        )
                                    except Exception:
                                        hit_pt = point_xy

                                    ok_in = True
                                    try:
                                        if room_z_test is not None:
                                            ok_in = bool(_is_point_in_room(room, DB.XYZ(float(hit_pt.X), float(hit_pt.Y), float(room_z_test))))
                                    except Exception:
                                        ok_in = True

                                    if ok_in:
                                        candidates.append({
                                            'wall': wall,
                                            'point': hit_pt,
                                            'point_on_wall': point_xy,
                                            'wall_dir': best_proj.get('wall_dir'),
                                            'seg_p1': best_proj.get('seg_p1'),
                                            'seg_p2': best_proj.get('seg_p2'),
                                            'distance': best_proj.get('distance'),
                                            'priority': _fixture_priority(getattr(fixture, 'kind', None)),
                                            'kind': getattr(fixture, 'kind', 'wm'),
                                            'wm_bbox': False
                                        })
                                        wm_processed += 1
                                        continue

                            out_vec = DB.XYZ(center.X - room_center_xy.X, center.Y - room_center_xy.Y, 0.0)
                            if out_vec.GetLength() > mm_to_ft(1):
                                out_u = out_vec.Normalize()
                                outside_pt = None
                                for dmm in (50, 200, 500, 900, 1500, 2500):
                                    p_out = DB.XYZ(center.X + out_u.X * mm_to_ft(dmm), center.Y + out_u.Y * mm_to_ft(dmm), center.Z)
                                    if not _is_point_in_room(room, p_out):
                                        outside_pt = p_out
                                        break
                                if outside_pt is None:
                                    outside_pt = DB.XYZ(center.X + out_u.X * mm_to_ft(1500), center.Y + out_u.Y * mm_to_ft(1500), center.Z)

                                dir_in = DB.XYZ(room_center_xy.X - outside_pt.X, room_center_xy.Y - outside_pt.Y, 0.0)
                                if dir_in.GetLength() > mm_to_ft(1):
                                    dir_in = dir_in.Normalize()
                                    hits_in = raycast_to_walls(outside_pt, [dir_in], wall_segments, mm_to_ft(5000))
                                    if hits_in:
                                        h = None
                                        for hh in hits_in:
                                            try:
                                                w0 = hh.get('wall')
                                                if isinstance(w0, DB.Wall) and (not su._is_curtain_wall(w0)):
                                                    h = hh
                                                    break
                                            except Exception:
                                                continue
                                        wall = h.get('wall') if h else None
                                        if wall is not None:
                                            point_xy = h.get('point')
                                            blocked = False
                                            for bmin, bmax in local_baths_clash:
                                                try:
                                                    d_b = _dist_point_to_rect_xy(point_xy, bmin, bmax)
                                                    if d_b is not None and d_b < clash_buffer_ft:
                                                        blocked = True
                                                        break
                                                except Exception:
                                                    continue
                                            if not blocked:
                                                for sink in local_sinks:
                                                    try:
                                                        sc = sink.center
                                                        if sc is None:
                                                            bmin, bmax = sink.bbox_min, sink.bbox_max
                                                            sc = DB.XYZ((bmin.X + bmax.X) * 0.5, (bmin.Y + bmax.Y) * 0.5, 0.0) if (bmin and bmax) else None
                                                        if sc is None:
                                                            continue
                                                        d_s = point_xy.DistanceTo(DB.XYZ(sc.X, sc.Y, 0.0))
                                                        if d_s < sink_clear_ft:
                                                            blocked = True
                                                            break
                                                    except Exception:
                                                        continue
                                            if not blocked:
                                                hit_pt = point_xy
                                                try:
                                                    hit_pt = _push_point_inside_room(
                                                        room,
                                                        point_xy,
                                                        in_dir_xy=dir_in,
                                                        wall_dir_xy=h.get('wall_dir') if h else None,
                                                        room_center_xy=room_center_xy,
                                                        room_bb=room_bb,
                                                        z_test=room_z_test
                                                    )
                                                except Exception:
                                                    hit_pt = point_xy
                                                ok_in = True
                                                try:
                                                    if room_z_test is not None:
                                                        ok_in = bool(_is_point_in_room(room, DB.XYZ(float(hit_pt.X), float(hit_pt.Y), float(room_z_test))))
                                                except Exception:
                                                    ok_in = True

                                                if ok_in:
                                                    candidates.append({
                                                        'wall': wall,
                                                        'point': hit_pt,
                                                        'point_on_wall': point_xy,
                                                        'wall_dir': h.get('wall_dir'),
                                                        'distance': h.get('distance'),
                                                        'priority': _fixture_priority(getattr(fixture, 'kind', None)),
                                                        'kind': getattr(fixture, 'kind', 'wm'),
                                                        'wm_bbox': False
                                                    })
                                                    wm_processed += 1
                                                    continue
                        except Exception:
                            pass

                    origin_pt = center
                    # If the point is on/over the boundary (common for BK text or wall-hosted items),
                    # shift towards room center until we are inside the room.
                    try:
                        if room_center_xy is not None and (not _is_point_in_room(room, center)):
                            v = DB.XYZ(room_center_xy.X - center.X, room_center_xy.Y - center.Y, 0.0)
                            if v.GetLength() > mm_to_ft(1):
                                vn = v.Normalize()
                                for dmm in (30, 200, 500, 900):
                                    cand = DB.XYZ(center.X + vn.X * mm_to_ft(dmm), center.Y + vn.Y * mm_to_ft(dmm), center.Z)
                                    if _is_point_in_room(room, cand):
                                        origin_pt = cand
                                        break
                                else:
                                    origin_pt = DB.XYZ(center.X + vn.X * mm_to_ft(200), center.Y + vn.Y * mm_to_ft(200), center.Z)
                    except Exception:
                        origin_pt = center

                    # If this is a boiler/rail hosted on a specific wall, prefer that wall directly.
                    try:
                        k = (getattr(fixture, 'kind', None) or '').lower()
                    except Exception:
                        k = ''
                    preferred = None
                    if k in ('boiler', 'rail') and getattr(fixture, 'element', None) is not None:
                        try:
                            host = getattr(fixture.element, 'Host', None)
                        except Exception:
                            host = None
                        if host is not None:
                            try:
                                hid = int(host.Id.IntegerValue)
                            except Exception:
                                hid = None
                            if hid is not None:
                                best_proj = None
                                for p1, p2, wall in wall_segments:
                                    try:
                                        if int(wall.Id.IntegerValue) != hid:
                                            continue
                                    except Exception:
                                        continue
                                    proj = _closest_point_on_segment_xy(center, p1, p2)
                                    if proj is None:
                                        continue
                                    try:
                                        dxy = DB.XYZ(center.X, center.Y, 0.0).DistanceTo(DB.XYZ(proj.X, proj.Y, 0.0))
                                    except Exception:
                                        dxy = 1e9
                                    if best_proj is None or dxy < best_proj['distance']:
                                        try:
                                            wdir = DB.XYZ(p2.X - p1.X, p2.Y - p1.Y, 0.0).Normalize()
                                        except Exception:
                                            wdir = None
                                        best_proj = {'wall': wall, 'point': proj, 'wall_dir': wdir, 'distance': dxy, 'seg_p1': p1, 'seg_p2': p2}

                                if best_proj and best_proj.get('wall_dir') is not None:
                                    # Apply the same blocking checks
                                    point_xy = best_proj['point']
                                    blocked = False
                                    for bmin, bmax in local_baths_clash:
                                        try:
                                            d_b = _dist_point_to_rect_xy(point_xy, bmin, bmax)
                                            if d_b is not None and d_b < clash_buffer_ft:
                                                blocked = True
                                                break
                                        except Exception:
                                            continue
                                    if not blocked:
                                        for sink in local_sinks:
                                            try:
                                                sc = sink.center
                                                if sc is None:
                                                    bmin, bmax = sink.bbox_min, sink.bbox_max
                                                    sc = DB.XYZ((bmin.X + bmax.X) * 0.5, (bmin.Y + bmax.Y) * 0.5, 0.0) if (bmin and bmax) else None
                                                if sc is None:
                                                    continue
                                                d_s = point_xy.DistanceTo(DB.XYZ(sc.X, sc.Y, 0.0))
                                                if d_s < sink_clear_ft:
                                                    blocked = True
                                                    break
                                            except Exception:
                                                continue
                                    if not blocked:
                                        preferred = best_proj

                    if preferred is not None:
                        hit_pt = preferred['point']
                        try:
                            hit_pt = _push_point_inside_room(
                                room,
                                hit_pt,
                                in_dir_xy=(origin_pt - hit_pt) if origin_pt else None,
                                wall_dir_xy=preferred.get('wall_dir'),
                                room_center_xy=room_center_xy,
                                room_bb=room_bb,
                                z_test=room_z_test
                            )
                        except Exception:
                            pass

                        ok_in = True
                        try:
                            if room_z_test is not None:
                                ok_in = bool(_is_point_in_room(room, DB.XYZ(float(hit_pt.X), float(hit_pt.Y), float(room_z_test))))
                        except Exception:
                            ok_in = True

                        if ok_in:
                            candidates.append({
                                'wall': preferred['wall'],
                                'point': hit_pt,
                                'point_on_wall': preferred['point'],
                                'wall_dir': preferred['wall_dir'],
                                'seg_p1': preferred.get('seg_p1'),
                                'seg_p2': preferred.get('seg_p2'),
                                'distance': preferred.get('distance'),
                                'priority': _fixture_priority(getattr(fixture, 'kind', None)),
                                'kind': getattr(fixture, 'kind', 'wm'),
                                'wm_bbox': False
                            })
                            wm_processed += 1
                            continue

                    hits = raycast_to_walls(origin_pt, directions, wall_segments, ray_limit_ft)
                    wm_processed += 1
                    
                    if not hits:
                        # Will fall through to candidates check
                        pass
                    else:
                        viable_hits = []
                        for hit in hits:
                            wall = hit['wall']
                            if (not isinstance(wall, DB.Wall)) or su._is_curtain_wall(wall):
                                continue
                            point_xy = hit['point']
                            dist = hit['distance']
                            if dist > ray_limit_ft:
                                continue
                            blocked = False
                            # Use reduced clash buffer for targeted placement
                            for bmin, bmax in local_baths_clash:
                                try:
                                    d_b = _dist_point_to_rect_xy(point_xy, bmin, bmax)
                                    if d_b is not None and d_b < clash_buffer_ft:
                                        blocked = True
                                        break
                                except Exception:
                                    continue
                            if blocked:
                                continue
                            for sink in local_sinks:
                                try:
                                    sc = sink.center
                                    if sc is None:
                                        bmin, bmax = sink.bbox_min, sink.bbox_max
                                        sc = DB.XYZ((bmin.X + bmax.X) * 0.5, (bmin.Y + bmax.Y) * 0.5, 0.0) if (bmin and bmax) else None
                                    if sc is None:
                                        continue
                                    d_s = point_xy.DistanceTo(DB.XYZ(sc.X, sc.Y, 0.0))
                                    if d_s < sink_clear_ft:
                                        blocked = True
                                        break
                                except Exception:
                                    continue
                            if blocked:
                                continue
                            viable_hits.append(hit)

                        if viable_hits:
                            best_hit = None
                            # For boilers/rails, prefer the wall behind the fixture (FacingOrientation) if available.
                            try:
                                k = (getattr(fixture, 'kind', None) or '').lower()
                            except Exception:
                                k = ''
                            if k in ('boiler', 'rail'):
                                if getattr(fixture, 'element', None) is not None:
                                    try:
                                        facing = getattr(fixture.element, 'FacingOrientation', None)
                                    except Exception:
                                        facing = None
                                    if facing is not None:
                                        try:
                                            fxy = DB.XYZ(float(facing.X), float(facing.Y), 0.0)
                                            if fxy.GetLength() > XY_TOL:
                                                fxy = fxy.Normalize()
                                                best_align = -1e9
                                                best_aligned = None
                                                for h in viable_hits:
                                                    hv = center - h['point']
                                                    hvxy = DB.XYZ(float(hv.X), float(hv.Y), 0.0)
                                                    if hvxy.GetLength() <= XY_TOL:
                                                        continue
                                                    align = hvxy.Normalize().DotProduct(fxy)
                                                    if align > best_align:
                                                        best_align = align
                                                        best_aligned = h
                                                # If we have a meaningful alignment (>= 0.2 ~ within 78deg), use it.
                                                if best_aligned is not None and best_align >= 0.2:
                                                    best_hit = best_aligned
                                        except Exception:
                                            best_hit = None

                                    # Fallback: choose wall direction aligned with the fixture hand orientation.
                                    if best_hit is None:
                                        try:
                                            hand = getattr(fixture.element, 'HandOrientation', None)
                                        except Exception:
                                            hand = None
                                        if hand is not None:
                                            try:
                                                hxy = DB.XYZ(float(hand.X), float(hand.Y), 0.0)
                                                if hxy.GetLength() > XY_TOL:
                                                    hxy = hxy.Normalize()
                                                    best_hand = -1e9
                                                    best_hand_hit = None
                                                    for h in viable_hits:
                                                        wd = h.get('wall_dir')
                                                        if wd is None:
                                                            continue
                                                        wdxy = DB.XYZ(float(wd.X), float(wd.Y), 0.0)
                                                        if wdxy.GetLength() <= XY_TOL:
                                                            continue
                                                        a = abs(wdxy.Normalize().DotProduct(hxy))
                                                        if a > best_hand:
                                                            best_hand = a
                                                            best_hand_hit = h
                                                    # Require clear alignment with a wall direction.
                                                    if best_hand_hit is not None and best_hand >= 0.5:
                                                        best_hit = best_hand_hit
                                            except Exception:
                                                pass

                                # If this is a placeholder point (BK text), use which side of the room bbox
                                # the point is outside of to prefer the corresponding wall orientation.
                                if best_hit is None and room_bb is not None and getattr(fixture, 'element', None) is None:
                                    try:
                                        x = float(center.X)
                                        y = float(center.Y)
                                        minx = float(min(room_bb.Min.X, room_bb.Max.X))
                                        maxx = float(max(room_bb.Min.X, room_bb.Max.X))
                                        miny = float(min(room_bb.Min.Y, room_bb.Max.Y))
                                        maxy = float(max(room_bb.Min.Y, room_bb.Max.Y))
                                        dx_out = 0.0
                                        dy_out = 0.0
                                        if x < minx: dx_out = minx - x
                                        elif x > maxx: dx_out = x - maxx
                                        if y < miny: dy_out = miny - y
                                        elif y > maxy: dy_out = y - maxy
                                        # Only apply if clearly outside.
                                        if dx_out > mm_to_ft(50) or dy_out > mm_to_ft(50):
                                            prefer_h = dy_out >= dx_out
                                            best_oriented = None
                                            for h in viable_hits:
                                                wd = h.get('wall_dir')
                                                if wd is None:
                                                    continue
                                                if prefer_h and abs(float(wd.X)) < abs(float(wd.Y)):
                                                    continue
                                                if (not prefer_h) and abs(float(wd.Y)) < abs(float(wd.X)):
                                                    continue
                                                if best_oriented is None or h['distance'] < best_oriented['distance']:
                                                    best_oriented = h
                                            if best_oriented is not None:
                                                best_hit = best_oriented
                                    except Exception:
                                        pass

                                # For BK placeholders (TextNote points), choose wall whose inward normal
                                # best matches direction to room center.
                                if best_hit is None and room_center_xy is not None:
                                    try:
                                        vcen = DB.XYZ(room_center_xy.X - origin_pt.X, room_center_xy.Y - origin_pt.Y, 0.0)
                                        if vcen.GetLength() > XY_TOL:
                                            vcen = vcen.Normalize()
                                            best_score = -1e9
                                            best_scored = None
                                            for h in viable_hits:
                                                n_in = _inward_normal_xy(h.get('wall_dir'), h.get('point'), room_center_xy)
                                                if n_in is None:
                                                    continue
                                                score = float(n_in.DotProduct(vcen))
                                                if best_scored is None or score > best_score + 1e-6 or (abs(score - best_score) <= 1e-6 and h['distance'] < best_scored['distance']):
                                                    best_score = score
                                                    best_scored = h
                                            if best_scored is not None:
                                                best_hit = best_scored
                                    except Exception:
                                        pass

                                # Fallback: infer wall direction from fixture bbox proportions (horizontal/vertical).
                                if best_hit is None:
                                    try:
                                        dx = abs(float(bbox_max.X) - float(bbox_min.X))
                                        dy = abs(float(bbox_max.Y) - float(bbox_min.Y))
                                        prefer_h = dx >= dy
                                        best_oriented = None
                                        for h in viable_hits:
                                            wd = h.get('wall_dir')
                                            if wd is None:
                                                continue
                                            if prefer_h and abs(float(wd.X)) < abs(float(wd.Y)):
                                                continue
                                            if (not prefer_h) and abs(float(wd.Y)) < abs(float(wd.X)):
                                                continue
                                            if best_oriented is None or h['distance'] < best_oriented['distance']:
                                                best_oriented = h
                                        if best_oriented is not None:
                                            best_hit = best_oriented
                                    except Exception:
                                        pass

                            if best_hit is None:
                                best_hit = min(viable_hits, key=lambda h: h['distance'])

                            # If screenshot scoring is enabled, keep multiple wall-hit options.
                            # Otherwise preserve the previous (single best_hit) behavior.
                            cand_hits = None
                            if use_screenshot_scoring:
                                cand_hits = viable_hits

                                # For boilers/rails, restrict to "behind" hits if FacingOrientation is available.
                                if k in ('boiler', 'rail') and getattr(fixture, 'element', None) is not None:
                                    try:
                                        facing = getattr(fixture.element, 'FacingOrientation', None)
                                    except Exception:
                                        facing = None
                                    if facing is not None:
                                        try:
                                            fxy = DB.XYZ(float(facing.X), float(facing.Y), 0.0)
                                            if fxy.GetLength() > XY_TOL:
                                                fxy = fxy.Normalize()
                                                aligned = []
                                                for h0 in viable_hits:
                                                    try:
                                                        hv = center - h0['point']
                                                        hvxy = DB.XYZ(float(hv.X), float(hv.Y), 0.0)
                                                        if hvxy.GetLength() <= XY_TOL:
                                                            continue
                                                        align = hvxy.Normalize().DotProduct(fxy)
                                                        if align >= 0.2:
                                                            aligned.append(h0)
                                                    except Exception:
                                                        continue
                                                if aligned:
                                                    cand_hits = aligned
                                        except Exception:
                                            pass

                            if (not use_screenshot_scoring) or (not cand_hits):
                                cand_hits = [best_hit]

                            # Keep only near-wall options so the socket stays "above" the fixture.
                            try:
                                md = min([float(h1.get('distance', 1e9) or 1e9) for h1 in cand_hits])
                                lim = md + float(raycast_slack_ft or 0.0)
                                cand_hits = [h1 for h1 in cand_hits if float(h1.get('distance', 1e9) or 1e9) <= lim]
                            except Exception:
                                pass

                            for h0 in cand_hits:
                                # Keep the wall-edge point for actual placement,
                                # but use an inward-pushed point for room/clearance tests.
                                pt_wall = h0['point']
                                hit_pt = pt_wall
                                try:
                                    hit_pt = _push_point_inside_room(
                                        room,
                                        pt_wall,
                                        in_dir_xy=(origin_pt - pt_wall) if origin_pt else None,
                                        wall_dir_xy=h0.get('wall_dir'),
                                        room_center_xy=room_center_xy,
                                        room_bb=room_bb,
                                        z_test=room_z_test
                                    )
                                except Exception:
                                    pass

                                ok_in = True
                                try:
                                    if room_z_test is not None:
                                        ok_in = bool(_is_point_in_room(room, DB.XYZ(float(hit_pt.X), float(hit_pt.Y), float(room_z_test))))
                                except Exception:
                                    ok_in = True
                                if not ok_in:
                                    continue

                                try:
                                    _kind0 = getattr(fixture, 'kind', 'wm')
                                except Exception:
                                    _kind0 = 'wm'
                                try:
                                    _prio0 = _fixture_priority(_kind0)
                                except Exception:
                                    _prio0 = 99

                                # If this is a washing machine, prefer candidates whose wall-position
                                # falls within the fixture bbox projection on the same wall segment.
                                wm_bbox_ok = False
                                bmin0 = None
                                bmax0 = None
                                try:
                                    if str(_kind0).lower() == 'wm':
                                        bmin0, bmax0 = fixture.bbox_min, fixture.bbox_max
                                        sp1, sp2 = h0.get('seg_p1'), h0.get('seg_p2')
                                        if bmin0 is not None and bmax0 is not None and sp1 is not None and sp2 is not None:
                                            wm_bbox_ok = _wm_bbox_contains_point_on_segment_xy(pt_wall, bmin0, bmax0, sp1, sp2)
                                except Exception:
                                    wm_bbox_ok = False

                                candidates.append({
                                    'wall': h0['wall'],
                                    'point': hit_pt,
                                    'point_on_wall': pt_wall,
                                    'wall_dir': h0.get('wall_dir'),
                                    'seg_p1': h0.get('seg_p1'),
                                    'seg_p2': h0.get('seg_p2'),
                                    'distance': h0.get('distance'),
                                    'priority': _prio0,
                                    'kind': _kind0,
                                    'wm_bbox': wm_bbox_ok,
                                    'wm_bbox_min': bmin0 if str(_kind0).lower() == 'wm' else None,
                                    'wm_bbox_max': bmax0 if str(_kind0).lower() == 'wm' else None
                                })

                                # For washing machines: also try sliding along the same wall to find a
                                # more convenient spot (e.g. closer to the door) while keeping clearances.
                                try:
                                    if (str(_kind0).lower() == 'wm') and slide_step_ft and slide_max_ft:
                                        _append_slide_candidates(
                                            candidates,
                                            room,
                                            room_bb,
                                            room_center_xy,
                                            origin_pt,
                                            h0,
                                            _kind0,
                                            _prio0,
                                            local_baths_clash,
                                            local_sinks,
                                            clash_buffer_ft,
                                            sink_clear_ft,
                                            slide_step_ft,
                                            slide_max_ft,
                                            wm_bbox_min=bmin0,
                                            wm_bbox_max=bmax0
                                        )
                                except Exception:
                                    pass

            # 2. If NO candidates (No WM or Raycast failed), try Maximin Scan
            # This ensures EVERY room gets a socket if possible.
            if not candidates:
                wm_skipped += 1 # Count as "WM logic skipped", but we still try placing

                best_strict = None
                best_strict_score = -1.0
                best_any = None
                best_any_score = -1.0

                try:
                    step_ft = mm_to_ft(rules.get('wet_fallback_step_mm', 500) or 500)
                except Exception:
                    step_ft = mm_to_ft(500)
                step_ft = max(float(step_ft), mm_to_ft(150))

                for p1, p2, wall in wall_segments:
                    try:
                        if not isinstance(wall, DB.Wall):
                            continue
                        seg_vec = p2 - p1
                        seg_len = float(seg_vec.GetLength())
                        if seg_len <= XY_TOL:
                            continue
                        seg_dir = seg_vec.Normalize()

                        sample_dists = []
                        if seg_len < step_ft:
                            sample_dists.append(seg_len * 0.5)
                        else:
                            curr_dist = step_ft * 0.5
                            while curr_dist < seg_len:
                                sample_dists.append(curr_dist)
                                curr_dist += step_ft

                        for curr_dist in sample_dists:
                            pt = p1 + seg_dir * curr_dist
                            point_xy = pt

                            min_dist = 1e9
                            hard_block = False
                            strict_ok = True

                            # Bathtubs: enforce 600mm from edge (distance to bbox), but allow relaxed fallback.
                            for bmin, bmax in local_baths:
                                d_b = _dist_point_to_rect_xy(point_xy, bmin, bmax)
                                if d_b is None:
                                    continue
                                if d_b <= XY_TOL:
                                    hard_block = True
                                    break
                                if d_b < clash_buffer_ft:
                                    strict_ok = False
                                if d_b < min_dist:
                                    min_dist = d_b
                            if hard_block:
                                continue

                            # Sinks: enforce 600mm from axis (center point)
                            for sink in local_sinks:
                                try:
                                    if sink.bbox_min and sink.bbox_max and _bbox_contains_point_xy(point_xy, sink.bbox_min, sink.bbox_max):
                                        hard_block = True
                                        break
                                except Exception:
                                    pass
                                try:
                                    sc = sink.center
                                    if sc is None:
                                        bmin, bmax = sink.bbox_min, sink.bbox_max
                                        sc = DB.XYZ((bmin.X + bmax.X) * 0.5, (bmin.Y + bmax.Y) * 0.5, 0.0) if (bmin and bmax) else None
                                    if sc is None:
                                        continue
                                    d_s = point_xy.DistanceTo(DB.XYZ(sc.X, sc.Y, 0.0))
                                    if d_s < sink_clear_ft:
                                        strict_ok = False
                                    if d_s < min_dist:
                                        min_dist = d_s
                                except Exception:
                                    continue
                            if hard_block:
                                continue

                            if strict_ok and min_dist > best_strict_score:
                                best_strict_score = min_dist
                                best_strict = {
                                    'point': pt,
                                    'wall': wall,
                                    'wall_dir': seg_dir,
                                    'distance': min_dist,
                                    'seg_p1': p1,
                                    'seg_p2': p2,
                                }
                            if min_dist > best_any_score:
                                best_any_score = min_dist
                                best_any = {
                                    'point': pt,
                                    'wall': wall,
                                    'wall_dir': seg_dir,
                                    'distance': min_dist,
                                    'seg_p1': p1,
                                    'seg_p2': p2,
                                }
                    except Exception:
                        continue

                best_maximin_pt = best_strict or best_any

                if best_maximin_pt:
                    # Offset Maximin point slightly inward too?
                    # We don't have a "center" reference. 
                    # Let's use Room Centroid or just assume wall normal?
                    # We don't have wall normal easily here without query.
                    # Use 'wall_dir' cross product? (Z axis)
                    # Vector(x, y, 0) cross Z(0,0,1) -> (-y, x, 0).
                    # We need to know which side is "in".
                    # Let's project to Room BBox center?
                    # Or just rely on 1ft-base projection in socket_utils.
                    # Let's try to offset 20mm "left" of wall vector?
                    # Wall segments in `get_room_boundary_segments_2d` are CCW (counter-clockwise) for outer loops?
                    # Revit returns them CCW usually.
                    # If CCW, "In" is Left.
                    # Cross(Dir, Z) = Right. So Cross(Z, Dir) = Left.
                    # Let's try Cross(Z, Dir).
                    
                    wd = best_maximin_pt['wall_dir']
                    hit_pt = best_maximin_pt['point']
                    try:
                        hit_pt = _push_point_inside_room(
                            room,
                            hit_pt,
                            wall_dir_xy=wd,
                            room_center_xy=room_center_xy,
                            room_bb=room_bb,
                            z_test=room_z_test
                        )
                    except Exception:
                        pass
                    
                    candidates.append({
                        'wall': best_maximin_pt['wall'],
                        'point': hit_pt,
                        'point_on_wall': best_maximin_pt['point'],
                        'wall_dir': wd,
                        'seg_p1': best_maximin_pt.get('seg_p1'),
                        'seg_p2': best_maximin_pt.get('seg_p2'),
                        'distance': best_maximin_pt.get('distance', 1e9),
                        'priority': _fixture_priority('fallback'),
                        'kind': 'fallback',
                        'wm_bbox': False
                    })

            # 3. Place from candidates
            if not candidates:
                try:
                    output.print_md(u'⚠️ {0}: пропуск — после fallback не найдено ни одного кандидата (нет валидных стен/лучи не попали).'.format(su._room_text(room)))
                except Exception:
                    pass
                continue

            # Enforce WM rule: if room has washing machine, place only within its bounds.
            if wm_enforce_bbox and local_wms:
                try:
                    wm_bbox_cands = [c for c in candidates if str(c.get('kind', '')).lower() == 'wm' and bool(c.get('wm_bbox'))]
                except Exception:
                    wm_bbox_cands = []
                if wm_bbox_cands:
                    candidates = wm_bbox_cands
                else:
                    try:
                        wm_only = [c for c in candidates if str(c.get('kind', '')).lower() == 'wm']
                    except Exception:
                        wm_only = []
                    if wm_only:
                        candidates = wm_only

            screen_png = None
            screen_ink_grid = None
            screen_crop_bb = None
            screen_crop_inv_tr = None

            # Optional: export plan screenshot (and optionally score candidates by "ink")
            if room_bb and screens_folder:
                ink_grid = None
                crop_min_host = None
                crop_max_host = None
                crop_bb = None
                crop_inv_tr = None
                try:
                    bbmin = room_bb.Min
                    bbmax = room_bb.Max
                    corners = [
                        DB.XYZ(bbmin.X, bbmin.Y, base_z),
                        DB.XYZ(bbmin.X, bbmax.Y, base_z),
                        DB.XYZ(bbmax.X, bbmin.Y, base_z),
                        DB.XYZ(bbmax.X, bbmax.Y, base_z),
                    ]
                    hx = []
                    hy = []
                    for cpt in corners:
                        hp = t.OfPoint(cpt)
                        hx.append(hp.X)
                        hy.append(hp.Y)
                    crop_min_host = DB.XYZ(min(hx), min(hy), 0.0)
                    crop_max_host = DB.XYZ(max(hx), max(hy), 0.0)

                    room_center_link = DB.XYZ((bbmin.X + bbmax.X) * 0.5, (bbmin.Y + bbmax.Y) * 0.5, base_z)
                    room_center_host = t.OfPoint(room_center_link)
                    lvl = _nearest_level_by_elev(doc, room_center_host.Z)
                    try:
                        vname = 'EOM_05_Wet_Screen_L{0}'.format(int(lvl.Id.IntegerValue)) if lvl else 'EOM_05_Wet_Screen'
                    except Exception:
                        vname = 'EOM_05_Wet_Screen'
                    v = _get_or_create_floor_plan_view(doc, lvl, vname, view_cache=view_cache)
                    if v:
                        vid = int(v.Id.IntegerValue)
                        if vid not in view_prepped:
                            _setup_view_for_screenshot(doc, v)
                            view_prepped.add(vid)
                        _set_view_crop_to_host_rect(v, crop_min_host, crop_max_host, screen_pad_ft)
                        try:
                            crop_bb = v.CropBox
                            crop_inv_tr = crop_bb.Transform.Inverse if crop_bb else None
                        except Exception:
                            crop_bb = None
                            crop_inv_tr = None
                        base_file = os.path.join(screens_folder, 'WetRoom_{0}'.format(int(room.Id.IntegerValue)))
                        png = _export_view_png(doc, v, base_file, screen_px)
                        if png:
                            need_ink = (use_screenshot_scoring and len(candidates) > 1) or mark_room_screens
                            if need_ink:
                                ink_grid = _build_ink_grid(png)
                            screen_png = png
                            screen_ink_grid = ink_grid
                            screen_crop_bb = crop_bb
                            screen_crop_inv_tr = crop_inv_tr

                    # Score only if there is a choice and scoring is enabled
                    if use_screenshot_scoring and ink_grid and crop_bb and crop_inv_tr and len(candidates) > 1:
                        for cnd in candidates:
                            try:
                                psc = cnd.get('point_on_wall') or cnd.get('point')
                                cnd['ink'] = _ink_density_at_link_point(ink_grid, crop_bb, crop_inv_tr, psc, t, ink_radius_ft)
                            except Exception:
                                cnd['ink'] = 1.0
                    else:
                        for cnd in candidates:
                            cnd['ink'] = 1.0
                except Exception:
                    for cnd in candidates:
                        cnd['ink'] = 1.0
            else:
                for cnd in candidates:
                    cnd['ink'] = 1.0

            # Door distance (used for WM post-shift away from door when too close).
            if local_doors:
                for cnd in candidates:
                    try:
                        p0 = cnd.get('point_on_wall') or cnd.get('point')
                        if p0 is None:
                            cnd['door_dist'] = 1e9
                            continue
                        best_d = None
                        for dp in local_doors:
                            if dp is None:
                                continue
                            d0 = su._dist_xy(p0, dp)
                            if best_d is None or d0 < best_d:
                                best_d = d0
                        cnd['door_dist'] = best_d if best_d is not None else 1e9
                    except Exception:
                        cnd['door_dist'] = 1e9
            else:
                for cnd in candidates:
                    cnd['door_dist'] = 1e9

            # Pick best candidate with priority (boiler/rail > wm > fallback) then distance (closer to fixture)
            # then ink (lower is better) as a tie-breaker.
            has_doors = bool(local_doors)

            def _cand_key(c):
                try:
                    pr = c.get('priority', 99)
                    dist = c.get('distance', 1e9)
                    ink = c.get('ink', 1.0)
                    return (pr, dist, ink)
                except Exception:
                    return (99, 1e9, 1.0)

            candidates_sorted = sorted(candidates, key=_cand_key)

            # Dedupe: don't skip whole rooms due to sockets on the opposite side of the same wall.
            # If the top candidate collides, try next ones. If all collide, still place the best.
            cand = None
            place_point = None
            dedupe_skipped = 0
            room_txt = None
            try:
                room_txt = su._room_text(room)
            except Exception:
                room_txt = None

            try:
                use_dedupe = float(dedupe_ft or 0.0) > XY_TOL
            except Exception:
                use_dedupe = False

            for c0 in candidates_sorted:
                try:
                    pbase = c0.get('point_on_wall') or c0.get('point')
                    if pbase is None:
                        continue
                    pp = DB.XYZ(pbase.X, pbase.Y, base_z + socket_height_ft)
                except Exception:
                    continue

                if use_dedupe:
                    try:
                        if idx.has_near(pp.X, pp.Y, pp.Z, dedupe_ft):
                            dedupe_skipped += 1
                            continue
                    except Exception:
                        pass

                cand = c0
                place_point = pp
                break

            if cand is None:
                cand = candidates_sorted[0]
                try:
                    pbase = cand.get('point_on_wall') or cand.get('point')
                    place_point = DB.XYZ(pbase.X, pbase.Y, base_z + socket_height_ft) if pbase is not None else None
                except Exception:
                    place_point = None
                if room_txt:
                    try:
                        output.print_md(u'⚠️ {0}: все кандидаты попали в dedupe ({1}мм) — ставлю лучший.'.format(room_txt, int(ft_to_mm(dedupe_ft))))
                    except Exception:
                        pass
            elif dedupe_skipped > 0 and room_txt:
                try:
                    output.print_md(u'ℹ️ {0}: пропущено кандидатов из-за dedupe: **{1}**'.format(room_txt, dedupe_skipped))
                except Exception:
                    pass

            # If the socket family has non-centered geometry, placing too close to wall end can
            # make the device hang in the air. For washing machines, shift 300mm towards bathtub.
            try:
                ksel = (cand.get('kind') or '').lower()
            except Exception:
                ksel = ''
            if ksel == 'wm' and local_baths and wm_shift_bath_ft and place_point is not None:
                try:
                    pw0 = cand.get('point_on_wall') or cand.get('point')
                    sp1 = cand.get('seg_p1')
                    sp2 = cand.get('seg_p2')
                    wm_bmin = cand.get('wm_bbox_min')
                    wm_bmax = cand.get('wm_bbox_max')

                    # Shift only when point is near a wall end; otherwise keep WM-centered placement.
                    do_shift = False
                    try:
                        if sp1 is not None and sp2 is not None and pw0 is not None:
                            seg_vec = DB.XYZ(float(sp2.X - sp1.X), float(sp2.Y - sp1.Y), 0.0)
                            seg_len = float(seg_vec.GetLength())
                            if seg_len > XY_TOL:
                                seg_dir = seg_vec.Normalize()
                                s0 = float(DB.XYZ(float(pw0.X - sp1.X), float(pw0.Y - sp1.Y), 0.0).DotProduct(seg_dir))
                                d_end = min(max(0.0, s0), max(0.0, seg_len - s0))
                                if d_end < float(wm_shift_bath_ft) * 1.05:
                                    do_shift = True
                    except Exception:
                        pass

                    if do_shift:
                        pshift = _shift_wm_point_on_wall_towards_bath(
                            room,
                            pw0,
                            sp1,
                            sp2,
                            room_center_xy,
                            room_bb,
                            room_z_test,
                            wm_bmin,
                            wm_bmax,
                            local_baths,
                            local_baths_clash,
                            local_sinks,
                            clash_buffer_ft,
                            sink_clear_ft,
                            wm_shift_bath_ft
                        )
                        if pshift is not None:
                            pp2 = None
                            try:
                                pp2 = DB.XYZ(pshift.X, pshift.Y, base_z + socket_height_ft)
                            except Exception:
                                pp2 = None
                            ok_dedupe = True
                            if use_dedupe and pp2 is not None:
                                try:
                                    ok_dedupe = not idx.has_near(pp2.X, pp2.Y, pp2.Z, dedupe_ft)
                                except Exception:
                                    ok_dedupe = True
                            if ok_dedupe and pp2 is not None:
                                cand['point_on_wall'] = pshift
                                place_point = pp2
                except Exception:
                    pass

            # If still too close to the door, shift 300mm away from the door along the same wall segment.
            if ksel == 'wm' and local_doors and wm_shift_door_ft and wm_shift_door_trigger_ft and place_point is not None:
                try:
                    pw0 = cand.get('point_on_wall') or cand.get('point')
                    sp1 = cand.get('seg_p1')
                    sp2 = cand.get('seg_p2')
                    wm_bmin = cand.get('wm_bbox_min')
                    wm_bmax = cand.get('wm_bbox_max')
                    d0 = _min_dist_to_points_xy(DB.XYZ(float(pw0.X), float(pw0.Y), 0.0), local_doors) if pw0 is not None else None
                    do_shift_end = False
                    try:
                        if sp1 is not None and sp2 is not None and pw0 is not None:
                            seg_vec = DB.XYZ(float(sp2.X - sp1.X), float(sp2.Y - sp1.Y), 0.0)
                            seg_len = float(seg_vec.GetLength())
                            if seg_len > XY_TOL:
                                seg_dir = seg_vec.Normalize()
                                s0 = float(DB.XYZ(float(pw0.X - sp1.X), float(pw0.Y - sp1.Y), 0.0).DotProduct(seg_dir))
                                d_end = min(max(0.0, s0), max(0.0, seg_len - s0))
                                if d_end < float(wm_shift_door_ft) * 1.05:
                                    do_shift_end = True
                    except Exception:
                        do_shift_end = False

                    if d0 is not None and float(d0) < float(wm_shift_door_trigger_ft) and do_shift_end:
                        pshift = _shift_wm_point_on_wall_away_from_door(
                            room,
                            pw0,
                            sp1,
                            sp2,
                            room_center_xy,
                            room_bb,
                            room_z_test,
                            wm_bmin,
                            wm_bmax,
                            local_doors,
                            local_baths_clash,
                            local_sinks,
                            clash_buffer_ft,
                            sink_clear_ft,
                            wm_shift_door_ft
                        )
                        if pshift is not None:
                            pp2 = None
                            try:
                                pp2 = DB.XYZ(pshift.X, pshift.Y, base_z + socket_height_ft)
                            except Exception:
                                pp2 = None
                            ok_dedupe = True
                            if use_dedupe and pp2 is not None:
                                try:
                                    ok_dedupe = not idx.has_near(pp2.X, pp2.Y, pp2.Z, dedupe_ft)
                                except Exception:
                                    ok_dedupe = True
                            if ok_dedupe and pp2 is not None:
                                cand['point_on_wall'] = pshift
                                place_point = pp2
                except Exception:
                    pass

            # If the point is too close to a wall segment end, the family geometry can hang in the air.
            # Clamp the wall-edge point away from segment ends.
            if wall_end_clear_ft and place_point is not None:
                try:
                    pw0 = cand.get('point_on_wall') or cand.get('point')
                    sp1 = cand.get('seg_p1')
                    sp2 = cand.get('seg_p2')
                    if pw0 is not None and sp1 is not None and sp2 is not None:
                        wm_bmin = cand.get('wm_bbox_min') if ksel == 'wm' else None
                        wm_bmax = cand.get('wm_bbox_max') if ksel == 'wm' else None
                        pshift = None
                        for frac in (1.0, 0.66, 0.33):
                            try:
                                pshift = _shift_point_on_wall_off_segment_end(
                                    room,
                                    pw0,
                                    sp1,
                                    sp2,
                                    room_center_xy,
                                    room_bb,
                                    room_z_test,
                                    local_baths_clash,
                                    local_sinks,
                                    clash_buffer_ft,
                                    sink_clear_ft,
                                    float(wall_end_clear_ft) * float(frac),
                                    wm_bbox_min=wm_bmin,
                                    wm_bbox_max=wm_bmax
                                )
                            except Exception:
                                pshift = None
                            if pshift is not None:
                                break

                        if pshift is not None:
                            pp2 = None
                            try:
                                pp2 = DB.XYZ(pshift.X, pshift.Y, base_z + socket_height_ft)
                            except Exception:
                                pp2 = None
                            ok_dedupe = True
                            if use_dedupe and pp2 is not None:
                                try:
                                    ok_dedupe = not idx.has_near(pp2.X, pp2.Y, pp2.Z, dedupe_ft)
                                except Exception:
                                    ok_dedupe = True
                            if ok_dedupe and pp2 is not None:
                                cand['point_on_wall'] = pshift
                                place_point = pp2
                except Exception:
                    pass

            # Save validation screenshot with chosen point marker (the raw export happens BEFORE placement)
            marked_png = None
            if mark_room_screens and screen_png and screen_ink_grid and screen_crop_bb and screen_crop_inv_tr:
                try:
                    pmark = cand.get('point_on_wall') or cand.get('point')
                    pxpy = _screen_pixel_from_link_point(screen_ink_grid, screen_crop_bb, screen_crop_inv_tr, pmark, t)
                    if pxpy:
                        lbl = cand.get('kind')
                        outp = _mark_png_socket(screen_png, pxpy[0], pxpy[1], label=lbl)
                        if outp:
                            marked_png = outp
                            try:
                                os.remove(screen_png)
                            except Exception:
                                pass
                except Exception:
                    pass

            if show_screens_in_output and screens_shown < show_screens_limit:
                try:
                    ttl = u'Комната: {0} | {1}'.format(su._room_text(room), cand.get('kind'))
                except Exception:
                    ttl = u'Комната | {0}'.format(cand.get('kind'))
                try:
                    _output_show_png(output, marked_png or screen_png, title=ttl)
                    screens_shown += 1
                except Exception:
                    pass

            if len(candidates_sorted) > 1:
                pass

            if place_point is None:
                continue

            try:
                if use_dedupe:
                    idx.add(place_point.X, place_point.Y, place_point.Z)
            except Exception:
                pass

            pending.append((cand['wall'], place_point, cand['wall_dir'], sym_wet, 0.0))

            if len(pending) >= batch_size:
                c0, cf, cwp, col, skipped_noface, skipped_noplace, c_ver = su._place_socket_batch(doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode)
                created += c0
                total_face += cf
                total_wp += cwp
                total_ol += col
                total_skipped_noface += skipped_noface
                total_skipped_noplace += skipped_noplace
                total_verified += c_ver
                pending = []

    if pending:
        c0, cf, cwp, col, skipped_noface, skipped_noplace, c_ver = su._place_socket_batch(doc, link_inst, t, pending, sym_flags, sp_cache, comment_value, strict_hosting=strict_hosting_mode)
        created += c0
        total_face += cf
        total_wp += cwp
        total_ol += col
        total_skipped_noface += skipped_noface
        total_skipped_noplace += skipped_noplace
        total_verified += c_ver

    wm_served = max(wm_processed - wm_skipped, 0)
    output.print_md('Создано розеток: **{0}** (по {1} стиральным машинам, пропущено {2})'.format(created, wm_served, wm_skipped))
    if created > 0:
        output.print_md('- На грани: {0}'.format(total_face))
        output.print_md('- WorkPlane: {0}'.format(total_wp))
        output.print_md('- OneLevel: {0}'.format(total_ol))
        
        # New logic: Only warn about floating if they were NOT verified geometry
        floating = created - total_verified
        if floating > 0:
            output.print_md('⚠️ {0} розеток размещены без привязки к стене (floating).'.format(floating))
    
    if total_skipped_noplace > 0:
        if strict_hosting_mode:
            output.print_md('⚠️ **{0}** розеток не удалось разместить (Strict Hosting: требуется грань стены).'.format(total_skipped_noplace))
        else:
            output.print_md('⚠️ **{0}** розеток не удалось разместить.'.format(total_skipped_noplace))

    if show_screens_in_output:
        try:
            if screens_shown < len(rooms):
                output.print_md('Показано скринов: **{0}** из **{1}** (лимит: {2}). Чтобы показать все — установите `wet_show_screens_limit: 0` в rules.'.format(
                    screens_shown, len(rooms), show_screens_limit
                ))
        except Exception:
            pass

try:
    main()
except Exception:
    log_exception('Error in 05_Wet')
