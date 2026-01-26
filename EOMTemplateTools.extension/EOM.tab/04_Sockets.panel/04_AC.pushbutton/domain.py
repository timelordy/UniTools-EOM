# -*- coding: utf-8 -*-

import math
from pyrevit import DB
import constants

def mm2ft(mm):
    return float(mm) / 304.8

def ft2mm(ft):
    return float(ft) * 304.8

def dist_xy(p1, p2):
    return math.sqrt((p1.X - p2.X)**2 + (p1.Y - p2.Y)**2)

def is_exterior(wall):
    """Check if wall is exterior based on parameter or name."""
    try:
        # Check Function Parameter (1 = Exterior)
        p = wall.get_Parameter(DB.BuiltInParameter.FUNCTION_PARAM)
        if p and p.AsInteger() == 1:
            return True
    except:
        pass
    
    try:
        # Check Name Keywords
        type_name = wall.WallType.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString() or ""
        full_name = ((wall.Name or "") + " " + type_name).lower()
        return any(k in full_name for k in constants.EXTERIOR_WALL_KW)
    except:
        return False

def get_wall_direction(wall):
    """Return normalized direction vector of the wall."""
    try:
        c = wall.Location.Curve
        p0 = c.GetEndPoint(0)
        p1 = c.GetEndPoint(1)
        dx, dy = p1.X - p0.X, p1.Y - p0.Y
        length = math.sqrt(dx*dx + dy*dy)
        if length > 1e-9:
            return DB.XYZ(dx/length, dy/length, 0)
    except:
        pass
    return None

def are_walls_perpendicular(dir1, dir2):
    """Check if two direction vectors are perpendicular."""
    if not dir1 or not dir2:
        return False
    dot_product = dir1.X * dir2.X + dir1.Y * dir2.Y
    return abs(dot_product) < constants.PERP_TOLERANCE

def project_to_line(pt, line_p0, line_dir):
    """Project point onto an infinite line defined by p0 and direction."""
    # Vector from p0 to pt
    vx = pt.X - line_p0.X
    vy = pt.Y - line_p0.Y
    
    # Dot product to find projection scalar
    t = vx * line_dir.X + vy * line_dir.Y
    
    # Projected point
    proj_pt = DB.XYZ(
        line_p0.X + t * line_dir.X,
        line_p0.Y + t * line_dir.Y,
        pt.Z # Keep original Z
    )
    return proj_pt

def project_to_segment_xy(pt, p0, p1):
    """Project point to segment defined by p0 and p1. Returns (projected_pt, distance)."""
    dx = p1.X - p0.X
    dy = p1.Y - p0.Y
    
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        # Segment is a point
        dist = math.sqrt((pt.X - p0.X)**2 + (pt.Y - p0.Y)**2)
        return p0, dist
        
    length_sq = dx*dx + dy*dy
    
    # Vector from p0 to pt
    vx = pt.X - p0.X
    vy = pt.Y - p0.Y
    
    # Dot product projection
    t = (vx * dx + vy * dy) / length_sq
    
    # Clamp to segment
    t = max(0.0, min(1.0, t))
    
    proj_x = p0.X + t * dx
    proj_y = p0.Y + t * dy
    
    proj_pt = DB.XYZ(proj_x, proj_y, pt.Z)
    dist = math.sqrt((pt.X - proj_x)**2 + (pt.Y - proj_y)**2)
    
    return proj_pt, dist

def intersect_lines_xy(p1, dir1, p2, dir2):
    """Find intersection of two infinite lines in XY plane."""
    # Line 1: P1 + t * D1
    # Line 2: P2 + u * D2
    # Cross product of directions (2D)
    det = dir1.X * dir2.Y - dir1.Y * dir2.X
    
    if abs(det) < 1e-9:
        return None # Parallel lines
    
    dx = p2.X - p1.X
    dy = p2.Y - p1.Y
    
    t = (dx * dir2.Y - dy * dir2.X) / det
    
    return DB.XYZ(
        p1.X + t * dir1.X,
        p1.Y + t * dir1.Y,
        p1.Z
    )

def get_wall_width(wall):
    try:
        if hasattr(wall, 'Width'): return wall.Width
    except: pass
    
    try:
        if hasattr(wall, 'WallType') and hasattr(wall.WallType, 'Width'):
            return wall.WallType.Width
    except: pass
    
    return mm2ft(200) # Default
