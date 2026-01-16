import sys
import os

file_path = r'C:\Users\anton\EOMTemplateTools\EOMTemplateTools.extension\EOM.tab\04_Sockets.panel\Sockets.pulldown\04_AC.pushbutton\script.py'

if not os.path.exists(file_path):
    print(f'File not found: {file_path}')
    sys.exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert facade_dir_vec calculation
target_1 = '        if not c_ext:\n            continue'
replacement_1 = '''        if not c_ext:
            continue

        facade_dir_vec = None
        try:
            fd = c_ext.GetEndPoint(1) - c_ext.GetEndPoint(0)
            if fd.GetLength() > 1e-9:
                facade_dir_vec = fd.Normalize()
        except Exception:
            facade_dir_vec = None'''

if target_1 in content and 'facade_dir_vec =' not in content:
    content = content.replace(target_1, replacement_1)
    print('Applied patch part 1')
else:
    print('Skipped part 1 (already applied or target not found)')

# 2. Insert parallel check
target_2 = '''                try:
                    wall_side = link_doc.GetElement(s_adj.ElementId)
                except Exception:
                    wall_side = None'''

replacement_2 = '''                try:
                    wall_side = link_doc.GetElement(s_adj.ElementId)
                except Exception:
                    wall_side = None

                if facade_dir_vec:
                    try:
                        ad = c_adj.GetEndPoint(1) - c_adj.GetEndPoint(0)
                        if ad.GetLength() > 1e-9:
                            ad = ad.Normalize()
                            if abs(float(facade_dir_vec.DotProduct(ad))) > 0.5:
                                continue
                    except Exception:
                        pass'''

if target_2 in content and 'if abs(float(facade_dir_vec.DotProduct(ad))) > 0.5:' not in content:
    content = content.replace(target_2, replacement_2)
    print('Applied patch part 2')
else:
    print('Skipped part 2 (already applied or target not found)')

# 3. Remove old perpendicularity check
# We need to be careful with indentation and multi-line matching.
# The block to remove/replace:
old_block_start = '                if wall_side and isinstance(wall_side, DB.Wall):'
old_block_end = '                    wall_any = wall_side'

# We want to remove everything between start and end, and keep start and end (but adjacent).
# Actually, we want to remove the check inside.

# Logic: Find the block start. Find the next occurrence of block end.
# Replace the text in between with just a newline (or nothing if indentation matches).

idx_start = content.find(old_block_start)
if idx_start != -1:
    idx_end = content.find(old_block_end, idx_start)
    if idx_end != -1:
        # Check if the text in between contains 'is_perp'
        chunk = content[idx_start:idx_end]
        if 'is_perp' in chunk:
            # Reconstruct
            # content before start + start line + newline + end line + content after
            # Warning: idx_end points to the start of "                    wall_any..."
            
            # The original code structure:
            # if wall_side ...:
            #     ...
            #     wall_any = wall_side
            
            # We want:
            # if wall_side ...:
            #     wall_any = wall_side
            
            new_chunk = old_block_start + '\n'
            
            content = content[:idx_start] + new_chunk + content[idx_end:]
            print('Applied patch part 3')
        else:
            print('Skipped part 3 (is_perp check not found in the expected block)')
    else:
        print('Skipped part 3 (end marker not found)')
else:
    print('Skipped part 3 (start marker not found)')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done writing file')
