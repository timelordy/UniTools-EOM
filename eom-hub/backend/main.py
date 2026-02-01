import eel
import os
import sys
import json
import glob
import yaml
import tempfile
import time

# Set web files folder
# In production (bundled), this will be consistent
# In dev, point to frontend/dist if built, or use dev server url if running
if getattr(sys, 'frozen', False):
    WEB_DIR = os.path.join(sys._MEIPASS, 'frontend', 'dist')
else:
    WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')

@eel.expose
def get_tools_list():
    """Scans the extension directory for tools."""
    tools = []
    
    # Path to the extension root
    # Assuming we are in eom-hub/backend, extension is in root/EOMTemplateTools.extension
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    extension_dir = os.path.join(root_dir, "EOMTemplateTools.extension", "EOM.tab")
    
    if not os.path.exists(extension_dir):
        return {"success": False, "error": f"Extension directory not found at {extension_dir}"}

    # Find all .panel folders
    search_pattern = os.path.join(extension_dir, "*.panel")
    panels = glob.glob(search_pattern)
    
    print(f"Scanning {extension_dir}...")
    print(f"Found {len(panels)} panels.")

    for panel_path in panels:
        panel_dir_name = os.path.basename(panel_path)
        # Extract group name: "02_Освещение.panel" -> "Освещение"
        # Remove extension
        group_name = panel_dir_name.replace(".panel", "")
        # Remove leading numbers and underscore if present (e.g. "02_")
        if "_" in group_name:
            parts = group_name.split("_", 1)
            if parts[0].isdigit():
                group_name = parts[1]
        
        # Find pushbuttons in this panel
        pb_search_pattern = os.path.join(panel_path, "*.pushbutton")
        pushbuttons = glob.glob(pb_search_pattern)
        
        for pb_path in pushbuttons:
            try:
                bundle_yaml_path = os.path.join(pb_path, "bundle.yaml")
                name = os.path.basename(pb_path).replace(".pushbutton", "") # Fallback name
                desc = ""
                
                if os.path.exists(bundle_yaml_path):
                    with open(bundle_yaml_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if data:
                            name = data.get('title', name)
                            desc = data.get('tooltip', '')
                
                # Icon handling
                icon = "/logo.png" # Default fallback
                
                tools.append({
                    "id": os.path.basename(pb_path), # ID must be unique
                    "name": name,
                    "description": desc,
                    "category": "tools",
                    "group": group_name,
                    "path": pb_path,
                    "icon": icon
                })
                
            except Exception as e:
                print(f"Error reading {pb_path}: {e}")

    return {"success": True, "tools": tools}

@eel.expose
def run_tool(tool_id):
    print(f"Running tool: {tool_id}")
    
    # 1. Find the tool path again (inefficient, but robust for now)
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    extension_dir = os.path.join(root_dir, "EOMTemplateTools.extension", "EOM.tab")
    
    # Simple search
    tool_path = None
    search_pattern = os.path.join(extension_dir, "*", "*.pushbutton")
    for pb_path in glob.glob(search_pattern):
        if os.path.basename(pb_path) == tool_id:
            tool_path = pb_path
            break
            
    if not tool_path:
         return {"success": False, "error": f"Tool {tool_id} not found."}
         
    # 2. Setup job ID and communication
    job_id = f"{tool_id}_{int(time.time())}"
    
    # We assume we are running in a mode where EOMHub acts as a server for Revit
    # Revit monitor polls for `eom_hub_command.txt` in TEMP
    temp_dir = tempfile.gettempdir()
    command_file = os.path.join(temp_dir, "eom_hub_command.txt")
    
    # Command format: "run:tool_id:job_id"
    cmd_str = f"run:{tool_id}:{job_id}"
    
    try:
        with open(command_file, 'w', encoding='utf-8') as f:
            f.write(cmd_str)
            
        return {
            "success": True, 
            "job_id": job_id, 
            "message": "Command sent to Revit",
            "status": "queued"
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to write command file: {e}"}

@eel.expose
def check_job_status(job_id):
    """Checks for result file in TEMP."""
    temp_dir = tempfile.gettempdir()
    # Revit script writes to this fixed file for now, 
    # but logically it should be per-job if we supported concurrent jobs.
    # The current script uses a fixed "eom_hub_result.json".
    # We will verify if the result inside matches our job_id.
    
    result_file = os.path.join(temp_dir, "eom_hub_result.json")
    
    if not os.path.exists(result_file):
        return {"status": "pending", "message": "Waiting for Revit..."}
        
    try:
        # Try to read safely (retry if locked)
        content = None
        for _ in range(3):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                break
            except:
                time.sleep(0.1)
                
        if not content:
             return {"status": "pending", "message": "Result file locked or empty"}
             
        data = json.loads(content)
        
        # Check if this result belongs to our job
        # If the script hasn't updated the file yet, we might see old results.
        # The script should overwrite it quickly.
        res_job_id = data.get("job_id")
        
        if str(res_job_id) != str(job_id):
             # It might be an old result or another job
             # If we just queued it, maybe Revit hasn't picked it up yet.
             return {"status": "running", "message": "Job queued..."}
             
        return data
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def start():
    if not os.path.exists(WEB_DIR):
        print(f"Web directory not found at {WEB_DIR}. Did you build the frontend?")
        # Fallback for dev - connect to Vite dev server?
        # For now, just warn
    
    eel.init(WEB_DIR)
    
    # Start the app
    try:
        eel.start('index.html', size=(1200, 800))
    except (SystemExit, MemoryError, KeyboardInterrupt):
        pass

if __name__ == "__main__":
    start()
