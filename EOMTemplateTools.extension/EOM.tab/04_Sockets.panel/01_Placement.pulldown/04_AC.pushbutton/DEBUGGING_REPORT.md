# AC Socket Placement Debugging Report
**Date:** 2026-01-26  
**Tool:** 04_AC.pushbutton  
**Issue:** Not placing any sockets

---

## 🔍 Analysis Summary

### Issue Found: **MISSING script.py FILE**

**Root Cause:**  
PyRevit requires a file named `script.py` to execute a button. The working code was in `script_original.py.bak` (a backup file) which PyRevit cannot execute automatically.

### Files in Directory:
- ✅ `diagnostic.py` - Diagnostic tool (not the main script)
- ❌ `script_backup.py` - Empty placeholder file  
- ✅ `script_original.py.bak` - **Full working code (4587 lines)** but wrong filename
- ⚠️ `script.py` - **WAS MISSING** (now created with debugging)

---

## 📋 What the Script Does

The AC Socket Placement tool (`script_original.py.bak`) is a comprehensive solution for automatically placing electrical sockets for air conditioning units:

### Process Flow:
1. **Load Configuration** - Reads rules from `config/rules.default.json`
2. **Select AR Links** - User selects architectural links containing AC units
3. **Collect Data:**
   - Levels to process
   - Rooms on those levels
   - Walls (for socket placement)
   - AC baskets/outdoor units (via keyword search)
4. **Find Placement Points:**
   - For each AC basket, find nearest room
   - Locate wall closest to basket
   - Calculate socket position (offset from corner, height from ceiling)
   - Avoid exterior walls (configurable)
5. **Place Sockets:**
   - Use face-based or point-based placement
   - Deduplicate existing sockets
   - Validate placement (height, distance, etc.)
6. **Cleanup:**
   - Remove duplicate sockets on same wall side
   - Fix socket facing orientation
7. **Report Results**

---

## 🐛 Potential Silent Failure Points

Even with the correct `script.py`, the tool can fail silently if:

### 1. **No AC Baskets Found** (Lines 1876-1976)
**Why it might fail:**
- AC units categorized differently than expected
- Family/type names don't match keywords
- Keywords too restrictive

**Default keywords searched:**
```python
['кондиц', 'кондиционер', 'конд', 'конденс',
 'наружный блок', 'внешний блок',
 'external unit', 'outdoor unit', 'air conditioner']
```

**Categories searched:**
- `OST_MechanicalEquipment`
- `OST_ElectricalEquipment`
- `OST_GenericModel`
- `OST_SpecialityEquipment`

**Fix:** Check if AC units are in these categories and have matching keywords in their family/type names.

---

### 2. **No Nearby Rooms** (Lines 2423-2461)
**Why it might fail:**
- Rooms not placed on selected levels
- Room boundaries incomplete
- AC basket too far from rooms (>2500mm default)

**Parameters:**
- `ac_room_search_boundary_mm`: 2500 (default)
- `ac_room_search_boundary_fallback_mm`: 4000
- `ac_room_hard_max_dist_mm`: 8000

**Fix:** 
- Ensure rooms are properly placed
- Check room boundaries are closed
- Increase search distance in config

---

### 3. **Excluded Rooms** (Lines 2105-2136)
**Why it might fail:**
- Nearest room is excluded by type (балкон, лоджия, санузел, коридор, etc.)

**Excluded room patterns:**
```python
'балкон', 'лодж', 'loggia', 'balcony', 'клад', 'гардер', 'тамбур'
+ wet_room_name_patterns + wc_room_name_patterns + bath_room_name_patterns + hallway_room_name_patterns
```

**Fix:** If AC should be placed in these rooms, modify config exclusion lists.

---

### 4. **No Wall Candidates** (Lines 2782-3036)
**Why it might fail:**
- All candidate walls are exterior walls (and `ac_socket_avoid_external_wall: true`)
- Room boundary segments missing
- Walls not perpendicular to facade direction

**Parameters:**
- `ac_socket_avoid_external_wall`: true (default)
- `ac_allow_facade_wall_last_resort`: true
- `ac_perp_dot_strict`: 0.35
- `ac_perp_dot_max`: 0.80

**Fix:**
- Set `ac_socket_avoid_external_wall: false` to allow exterior walls
- Check room boundary integrity

---

### 5. **Socket Inside Basket BBox** (Lines 2669-2696, 3601-3625)
**Why it might fail:**
- Calculated socket position intersects AC basket bounding box
- Push-out logic fails

**Parameters:**
- `ac_basket_exclude_bbox_mm`: 200 (padding around basket)
- `ac_basket_bbox_z_tol_mm`: 1500 (vertical tolerance)

**Fix:** Increase basket exclusion padding or check basket placement.

---

### 6. **Too Far from Basket** (Lines 2732-2736, 3632-3636)
**Why it might fail:**
- Best candidate point exceeds max distance

**Parameter:**
- `ac_validate_basket_max_dist_mm`: 2500

**Fix:** Increase max distance in config.

---

### 7. **Facade Wall Detection** (Lines 2387-2402, 3650-3664)
**Why it might fail:**
- Wall incorrectly classified as facade/exterior
- Room probing fails (no rooms on one side)

**Parameters:**
- `ac_room_side_probe_mm`: 400
- `ac_room_side_scan_bbox_mm`: 8000
- `ac_room_side_scan_limit`: 250

**Fix:** Check room volumes/boundaries are correct.

---

## 🔧 Debugging Enhancements Added

The new `script.py` includes:

1. **Header logging:**
   ```
   # 🔌 AC Socket Placement Tool v2.0
   Plugin initialized successfully
   ```

2. **Step-by-step progress:**
   - Configuration loading
   - Link selection
   - Data collection per link
   - Basket search by category
   - Summary statistics

3. **Detailed counts:**
   - Levels selected
   - Rooms found
   - Walls found
   - Baskets found (by category)
   - Total summary

4. **Failure diagnostics:**
   - If no baskets: shows possible reasons
   - If no rooms: shows room count
   - If no walls: shows wall count

---

## ✅ Solution Applied

**Created:** `script.py` (working version with debugging output)

**Changes from original:**
1. Added `output.print_md()` statements throughout main()
2. Added basket counting by category
3. Added summary section with diagnostics
4. Preserved all original logic

**Files to use:**
- ✅ `script.py` - **Main script (with debugging)**
- 📖 `diagnostic.py` - Separate diagnostic tool
- 📦 `script_original.py.bak` - Original backup

---

## 🧪 Testing Checklist

When running the tool, check the output for:

1. ✅ "Configuration loaded successfully"
2. ✅ Selected X link(s)
3. ✅ Found X rooms
4. ✅ Found X walls
5. ✅ Found X AC baskets total
6. ⚠️ If "No AC baskets found" - check categories & keywords
7. ⚠️ If "No nearby rooms" - check room placement
8. ⚠️ If "No candidate" - check wall availability & avoid_external setting

---

## 📝 Configuration Tips

Key config parameters to adjust if sockets aren't placing:

```json
{
  "ac_basket_family_keywords": ["кондиц", "outdoor", ...],
  "ac_socket_avoid_external_wall": true,
  "ac_allow_facade_wall_last_resort": true,
  "ac_room_search_boundary_mm": 2500,
  "ac_validate_basket_max_dist_mm": 2500,
  "socket_ac_height_from_ceiling_mm": 300,
  "socket_ac_offset_from_corner_mm": 200
}
```

**To allow exterior wall placement:**
```json
{
  "ac_socket_avoid_external_wall": false
}
```

**To increase search radius:**
```json
{
  "ac_room_search_boundary_mm": 5000,
  "ac_validate_basket_max_dist_mm": 5000
}
```

---

## 🎯 Next Steps

1. **Run the tool** in Revit using the new `script.py`
2. **Check output** for detailed progress
3. **If still no sockets:**
   - Look for "Found 0 AC baskets" → check categories/keywords
   - Look for "No nearby rooms" → check room placement
   - Look for "No candidate" → check wall configuration
4. **Adjust config** based on diagnostic output
5. **Re-run** and verify

---

## 📞 Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| No baskets found | Add AC family names to keywords list |
| Baskets found but no sockets | Disable `ac_socket_avoid_external_wall` |
| Sockets in wrong rooms | Adjust room exclusion patterns |
| Sockets too far from basket | Increase `ac_validate_basket_max_dist_mm` |
| Sockets inside basket | Increase `ac_basket_exclude_bbox_mm` |

---

**End of Report**
