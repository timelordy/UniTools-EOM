import json
import sys

file_path = r"C:\Users\anton\.local\share\opencode\tool-output\tool_beb5662ad0014nhCgEdPuCY4xz"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    inner_json = data.get('result', '{}')
    try:
        parsed_inner = json.loads(inner_json)
    except (TypeError, json.JSONDecodeError):
        parsed_inner = inner_json
    
    if isinstance(parsed_inner, str):
         print("Warning: could not parse inner JSON result")
         parsed_inner = {}

    elements = parsed_inner.get('elements', [])
    
    found_ids = []
    
    # Priority 1: Exact "05_wet" match
    wet_ids = []
    
    # Priority 2: Sockets/Switches/Wet-rated
    other_ids = []

    keywords = ["Рзт", "Вык", "Socket", "Switch", "IP44", "IP54", "IP55", "IP65", "Влаго"]
    
    print(f"Total elements scanned: {len(elements)}")

    for el in elements:
        # Convert values to string for easy searching
        el_values = str(el.values())
        
        if "05_wet" in el_values:
            wet_ids.append(el['id'])
        else:
            for kw in keywords:
                if kw in el_values:
                    other_ids.append(el['id'])
                    break
    
    if wet_ids:
        print(f"Found {len(wet_ids)} exact matches for '05_wet'.")
        print(f"IDs: {wet_ids}")
    else:
        print("No exact matches for '05_wet'.")
        print(f"Found {len(other_ids)} related matches (Sockets, Switches, Wet-rated).")
        print(f"IDs: {other_ids}")

except Exception as e:
    print(f"Error: {e}")
