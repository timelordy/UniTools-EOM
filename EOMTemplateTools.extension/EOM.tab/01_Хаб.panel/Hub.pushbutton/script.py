# -*- coding: utf-8 -*-
"""EOM Hub - Web interface launcher with file-based communication."""

__title__ = "EOM\nHub"
__author__ = "EOM Team"

import os
_os = os
import sys
import ctypes
import threading
import json
import time
import uuid
import tempfile
import re
import subprocess
import io

try:
    text_type = unicode  # IronPython 2
    binary_type = str
except NameError:
    text_type = str
    binary_type = bytes


def _fs_encoding():
    try:
        enc = sys.getfilesystemencoding()
        if not enc:
            enc = "utf-8"
        return enc
    except Exception:
        return "utf-8"


def _to_unicode(value):
    try:
        if isinstance(value, text_type):
            return value
        if isinstance(value, binary_type):
            enc = _fs_encoding()
            try:
                return value.decode(enc)
            except Exception:
                return value.decode('utf-8', 'ignore')
        return text_type(value)
    except Exception:
        try:
            return text_type(value)
        except Exception:
            return u"" if text_type is not str else ""


def _get_root_temp_dir(temp_dir):
    try:
        base = os.path.basename(temp_dir.rstrip("\\/"))
        if re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", base):
            return os.path.dirname(temp_dir)
    except Exception:
        pass
    return temp_dir

# Session binding (Hub <-> Revit)
SESSION_ID = None
_EOM_MONITOR_STARTED = False
_EOM_HUB_EVENT = None
_EOM_HUB_HANDLER = None
_EOM_PROCESS_TOOL = None


def _get_runner_lock_path():
    try:
        temp_root = os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
    except Exception:
        temp_root = tempfile.gettempdir()
    return os.path.join(temp_root, "eom_hub_runner.lock")


def _set_runner_env(tool_id, job_id):
    def _safe_text(value):
        try:
            return _to_unicode(value)
        except Exception:
            try:
                return str(value)
            except Exception:
                return ""

    try:
        os.environ["EOM_HUB_RUN_TOOL_ID"] = _safe_text(tool_id)
    except Exception:
        pass
    try:
        os.environ["EOM_HUB_RUN_JOB_ID"] = _safe_text(job_id)
    except Exception:
        pass


def _clear_runner_env():
    for key in ("EOM_HUB_RUN_TOOL_ID", "EOM_HUB_RUN_JOB_ID"):
        try:
            if key in os.environ:
                del os.environ[key]
        except Exception:
            pass


def _get_postcommand_id():
    """Return configured Revit command id for PostCommand, or None."""
    import os as _os
    env_val = _os.environ.get("EOM_HUB_POSTCOMMAND_ID")
    file_val = None
    try:
        temp_root = _os.environ.get("TEMP") or _os.environ.get("TMP") or tempfile.gettempdir()
        roots = [temp_root]
        try:
            from hub_temp_paths import iter_temp_roots
            roots = iter_temp_roots(temp_root)
        except Exception:
            try:
                root_temp = _get_root_temp_dir(temp_root)
                if root_temp and root_temp != temp_root:
                    roots.append(root_temp)
            except Exception:
                pass

        for root in roots:
            cfg_path = _os.path.join(root, "eom_hub_postcommand_id.txt")
            if _os.path.exists(cfg_path):
                with io.open(cfg_path, "r", encoding="utf-8") as f:
                    file_val = f.read()
                break
    except Exception:
        file_val = None

    try:
        from hub_postcommand import select_command_id
        return select_command_id(env_val, file_val)
    except Exception:
        # Fallback: simple normalization
        try:
            val = env_val or file_val
            if not val:
                return None
            if isinstance(val, str):
                val = val.strip()
            else:
                val = str(val).strip()
            return val if val else None
        except Exception:
            return None


def _get_tool_postcommand_id(tool_id):
    """Return configured Revit command id for a tool, or None."""
    import os as _os
    env_val = _os.environ.get("EOM_HUB_TOOL_COMMAND_MAP")
    file_val = None
    try:
        temp_root = _os.environ.get("TEMP") or _os.environ.get("TMP") or tempfile.gettempdir()
        roots = [temp_root]
        try:
            from hub_temp_paths import iter_temp_roots
            roots = iter_temp_roots(temp_root)
        except Exception:
            try:
                root_temp = _get_root_temp_dir(temp_root)
                if root_temp and root_temp != temp_root:
                    roots.append(root_temp)
            except Exception:
                pass

        for root in roots:
            cfg_path = _os.path.join(root, "eom_hub_tool_command_map.txt")
            if _os.path.exists(cfg_path):
                with io.open(cfg_path, "r", encoding="utf-8") as f:
                    file_val = f.read()
                break
    except Exception:
        file_val = None

    try:
        from hub_tool_commands import select_command_id_for_tool
        return select_command_id_for_tool(tool_id, env_val, file_val)
    except Exception:
        return None


def _run_tool_via_pyrevit_command(script_path):
    """Try to execute a tool using pyRevit command class."""
    import os as _os
    try:
        from pyrevit.extensions.genericcomps import GenericUIComponent
        from pyrevit.loader import sessionmgr
    except Exception as imp_err:
        return False, imp_err

    try:
        tool_dir = _os.path.dirname(script_path)
        unique_name = GenericUIComponent.make_unique_name(tool_dir)
        if not unique_name:
            return False, "unique name not resolved"

        cmd_cls = sessionmgr.find_pyrevitcmd(unique_name)
        if not cmd_cls:
            return False, "command class not found"

        try:
            sessionmgr.execute_command_cls(cmd_cls, exec_from_ui=True)
        except Exception:
            sessionmgr.execute_command(unique_name)

        return True, unique_name
    except Exception as run_err:
        return False, run_err


def _get_time_savings_for_tool(tool_key):
    """Return (avg, min, max) minutes saved for tool, or (None, None, None)."""
    try:
        from time_savings import calculate_time_saved, calculate_time_saved_range, get_last_time_saved_entry
    except Exception:
        return None, None, None

    entry = None
    try:
        entry = get_last_time_saved_entry(tool_key)
    except Exception:
        entry = None

    if isinstance(entry, dict):
        try:
            count = entry.get("count")
            avg = entry.get("minutes")
            mn = entry.get("minutes_min")
            mx = entry.get("minutes_max")
            if avg is None or mn is None or mx is None:
                mn, mx = calculate_time_saved_range(tool_key, count)
                avg = calculate_time_saved(tool_key, count)
            return avg, mn, mx
        except Exception:
            pass

    try:
        mn, mx = calculate_time_saved_range(tool_key)
        avg = calculate_time_saved(tool_key)
        return avg, mn, mx
    except Exception:
        return None, None, None


def _get_session_id():
    global SESSION_ID
    if SESSION_ID:
        return SESSION_ID
    session_id = os.environ.get("EOM_SESSION_ID")
    if not session_id:
        session_id = str(uuid.uuid4())
        os.environ["EOM_SESSION_ID"] = session_id
    SESSION_ID = session_id
    return SESSION_ID


def _session_filename(stem, ext):
    sid = _get_session_id()
    if sid:
        return "eom_{0}_{1}.{2}".format(stem, sid, ext)
    return "eom_{0}.{1}".format(stem, ext)


def _get_hub_session_path(session_id):
    temp_root = os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
    return os.path.join(temp_root, "eom_hub_session_{0}.json".format(session_id))


def find_hub_exe():
    """Find EOMHub.exe in possible locations."""
    script_dir = _to_unicode(os.path.dirname(__file__))
    # script_dir = .../EOMTemplateTools.extension/EOM.tab/01_РҐР°Р±.panel/Hub.pushbutton
    extension_dir = _to_unicode(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))
    extensions_dir = _to_unicode(os.path.dirname(extension_dir))

    possible_paths = [
        os.path.join(extension_dir, "bin", "EOMHub.exe"),
        os.path.join(extensions_dir, "EOMHub.exe"),
        os.path.join(extension_dir, "EOMHub.exe"),
        os.path.join(script_dir, "EOMHub.exe"),
        os.path.join(os.environ.get("APPDATA", ""), "pyRevit", "Extensions", "EOMTemplateTools.extension", "bin", "EOMHub.exe"),
        r"C:\Users\anton\EOMTemplateTools\EOMHub\dist\EOMHub.exe",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def is_hub_running():
    """Check if EOMHub is running and activate window."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, u"EOM Hub")
        if hwnd and hwnd != 0:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return True
    except:
        pass
    return False


def start_command_monitor(start_thread=True):
    """Start background monitoring of commands from EOMHub."""
    import io
    import json as _json
    import os as _os
    import threading as _threading
    import time as _time
    import glob as _glob
    import tempfile as _tempfile

    def _to_unicode(value, _orig=_to_unicode):
        try:
            return _orig(value)
        except Exception:
            try:
                return unicode(value)
            except Exception:
                try:
                    return str(value)
                except Exception:
                    return ""

    try:
        global _EOM_MONITOR_STARTED, _EOM_HUB_EVENT, _EOM_HUB_HANDLER
        
        # Ensure path variables are unicode to prevent mojibake in IronPython 2.7
        # This is critical for os.walk/glob to return unicode strings
        script_dir = _to_unicode(_os.path.dirname(__file__))
            
        extension_dir = _os.path.dirname(_os.path.dirname(_os.path.dirname(script_dir)))
        lib_dir = _os.path.join(extension_dir, u"lib")
        
        if lib_dir not in sys.path:
            sys.path.insert(0, lib_dir)

        try:
            from hub_command_parser import parse_command
        except Exception:
            parse_command = None
            
        # Singleton check with thread liveness verification
        if start_thread:
            monitor_thread = getattr(sys, "eom_hub_monitor_thread", None)
            if monitor_thread and monitor_thread.is_alive():
                try:
                    temp_probe = _to_unicode(_tempfile.gettempdir())
                    status_probe = _os.path.join(temp_probe, u"eom_hub_status.json")
                    if _os.path.exists(status_probe):
                        age = _time.time() - _os.path.getmtime(status_probe)
                        if age < 10:
                            return
                except Exception:
                    return
            else:
                try:
                    temp_probe = _to_unicode(_tempfile.gettempdir())
                    status_probe = _os.path.join(temp_probe, u"eom_hub_status.json")
                    if _os.path.exists(status_probe):
                        age = _time.time() - _os.path.getmtime(status_probe)
                        if age < 10:
                            return
                except Exception:
                    pass
            sys.eom_hub_monitor_started = True

        # Use USERPROFILE (or TEMP) for logs to ensure visibility and persistence
        user_profile = _os.environ.get("USERPROFILE") or _os.environ.get("TEMP") or _tempfile.gettempdir()
        DEBUG_LOG = _os.path.join(user_profile, "eom_debug.log")

        def debug_log(msg):
            try:
                # Ensure msg is unicode
                if isinstance(msg, str):
                    msg = msg.decode('utf-8', 'replace')
                elif not isinstance(msg, unicode):
                    msg = unicode(msg)
                    
                timestamp = _time.strftime("%Y-%m-%d %H:%M:%S")
                # Write as UTF-8
                with io.open(DEBUG_LOG, 'a', encoding='utf-8') as f:
                    f.write(u"[{0}] {1}\n".format(timestamp, msg))
                    try:
                        f.flush()
                    except Exception:
                        pass
            except Exception:
                pass

        debug_log(u"Monitor init attempt...")

        from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent

        # Capture globals to survive pyRevit cleanup
        os_mod = _os
        get_postcommand_id = _get_postcommand_id
        get_tool_postcommand_id = _get_tool_postcommand_id
        set_runner_env = _set_runner_env
        clear_runner_env = _clear_runner_env
        get_runner_lock_path = _get_runner_lock_path
        
        _EOM_MONITOR_STARTED = True

        session_id = _get_session_id()
        TEMP_DIR = _to_unicode(_tempfile.gettempdir())
        ROOT_TEMP_DIR = _get_root_temp_dir(TEMP_DIR)
            
        # Use fixed filenames for simpler communication with Hub
        COMMAND_FILE = _os.path.join(TEMP_DIR, u"eom_hub_command.txt")
        COMMAND_FILES_GLOB = _os.path.join(TEMP_DIR, u"eom_hub_command_*.txt")
        STATUS_FILE = _os.path.join(TEMP_DIR, u"eom_hub_status.json")
        STATUS_FILE_ROOT = None
        try:
            if ROOT_TEMP_DIR and ROOT_TEMP_DIR != TEMP_DIR:
                STATUS_FILE_ROOT = _os.path.join(ROOT_TEMP_DIR, u"eom_hub_status.json")
        except Exception:
            STATUS_FILE_ROOT = None
        RESULT_FILE = _os.path.join(TEMP_DIR, u"eom_hub_result.json")
        
        debug_log(u"Monitor init")
        debug_log(u"TEMP_DIR=" + TEMP_DIR)
        debug_log(u"SESSION_ID=" + _to_unicode(session_id))

        def write_result_json(payload):
            """Write legacy result JSON atomically (eom_hub_result.json)."""
            try:
                tmp_path = RESULT_FILE + u".tmp"
                with io.open(tmp_path, 'w', encoding='utf-8') as f:
                    _json.dump(payload, f, ensure_ascii=False, indent=2)
                try:
                    if _os.path.exists(RESULT_FILE):
                        _os.remove(RESULT_FILE)
                except Exception:
                    pass
                try:
                    _os.rename(tmp_path, RESULT_FILE)
                except Exception:
                    with io.open(RESULT_FILE, 'w', encoding='utf-8') as f:
                        _json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception:
                try:
                    with io.open(RESULT_FILE, 'w', encoding='utf-8') as f:
                        _json.dump(payload, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        def write_job_result_json(job_id, payload):
            """Write per-job result JSON (eom_hub_result_{job_id}.json)."""
            try:
                if not job_id:
                    return
                job_result_file = _os.path.join(TEMP_DIR, u"eom_hub_result_{0}.json".format(job_id))
                tmp_path = job_result_file + u".tmp"
                with io.open(tmp_path, 'w', encoding='utf-8') as f:
                    _json.dump(payload, f, ensure_ascii=False, indent=2)
                try:
                    if _os.path.exists(job_result_file):
                        _os.remove(job_result_file)
                except Exception:
                    pass
                try:
                    _os.rename(tmp_path, job_result_file)
                except Exception:
                    with io.open(job_result_file, 'w', encoding='utf-8') as f:
                        _json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception:
                try:
                    job_result_file = _os.path.join(TEMP_DIR, u"eom_hub_result_{0}.json".format(job_id))
                    with io.open(job_result_file, 'w', encoding='utf-8') as f:
                        _json.dump(payload, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        # Save references before globals cleanup
        uiapp_ref = None
        try:
            uiapp_ref = __revit__  # noqa: F821
        except Exception:
            uiapp_ref = None
        run_tool_via_pyrevit_command = _run_tool_via_pyrevit_command
        get_time_savings_for_tool = _get_time_savings_for_tool
        
        # Tool ID -> script path mapping
        TOOL_SCRIPTS = {}
        
        tab_dirs = [
            _os.path.join(extension_dir, u"EOM.tab"),
            _os.path.join(extension_dir, u"Разработка.tab"),
            _os.path.join(extension_dir, u"Teslabim.tab"),
        ]
        
        try:
            for tab_dir in tab_dirs:
                if _os.path.exists(tab_dir):
                    # os.walk with unicode path returns unicode items
                    for root, dirs, files in _os.walk(tab_dir):
                        base = _os.path.basename(root)
                        if not base.endswith(u".pushbutton"):
                            continue

                        # Skip Hub itself
                        if u"Hub" in base or u"РҐР°Р±" in base:
                            continue

                        script_file = _os.path.join(root, u"script.py")
                        if not _os.path.exists(script_file):
                            continue

                        rel_dir = _os.path.relpath(root, tab_dir)
                        rel_id = rel_dir.replace(u"\\", u"/")
                        TOOL_SCRIPTS[rel_id] = script_file

                        # Use full folder name as ID
                        TOOL_SCRIPTS[base] = script_file

                        # Legacy id support
                        legacy_id = base.replace(u".pushbutton", u"")
                        if legacy_id not in TOOL_SCRIPTS:
                            TOOL_SCRIPTS[legacy_id] = script_file
        except Exception as e:
            debug_log(u"Error scanning tabs: " + _to_unicode(e))

        # Legacy/Hardcoded fallbacks
        FALLBACK_SCRIPTS = {
            "lights_center": _os.path.join(extension_dir, u"EOM.tab", u"02_Освещение.panel", u"СветПоЦентру.pushbutton", u"script.py"),
            "lights_entrance": _os.path.join(extension_dir, u"EOM.tab", u"02_Освещение.panel", u"СветУВхода.pushbutton", u"script.py"),
            "lights_elevator": _os.path.join(extension_dir, u"EOM.tab", u"02_Освещение.panel", u"СветВЛифтах.pushbutton", u"script.py"),
            "lights_pk": _os.path.join(extension_dir, u"Разработка.tab", u"02_Освещение_Dev.panel", u"СветПК.pushbutton", u"script.py"),
            "panel_door": _os.path.join(extension_dir, u"EOM.tab", u"03_ЩитыВыключатели.panel", u"ЩитНадДверью.pushbutton", u"script.py"),
            "switches_doors": _os.path.join(extension_dir, u"EOM.tab", u"03_ЩитыВыключатели.panel", u"ВыключателиУДверей.pushbutton", u"script.py"),
            "entrance_numbering": _os.path.join(extension_dir, u"Разработка.tab", u"03_ЩитыВыключатели_Dev.panel", u"НумерацияПодъезда.pushbutton", u"script.py"),
            "sockets_general": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"01_Общие.pushbutton", u"script.py"),
            "kitchen_block": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"02_КухняБлок.pushbutton", u"script.py"),
            "kitchen_general": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"02_КухняБлок.pushbutton", u"script.py"),
            "ac_sockets": _os.path.join(extension_dir, u"Разработка.tab", u"04_Розетки.panel", u"04_Кондиционеры.pushbutton", u"script.py"),
            "wet_zones": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"05_ВлажныеЗоны.pushbutton", u"script.py"),
            "low_voltage": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"06_Слаботочка.pushbutton", u"script.py"),
            "shdup": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"07_ШДУП.pushbutton", u"script.py"),
            "storage_rooms": _os.path.join(extension_dir, u"Разработка.tab", u"04_Розетки.panel", u"08_Кладовые.pushbutton", u"script.py"),
            "magic_button": _os.path.join(extension_dir, u"EOM.tab", u"10_АвтоРазмещение.panel", u"00_ВолшебнаяКнопка.pushbutton", u"script.py"),
            "gost_validation": _os.path.join(extension_dir, u"Разработка.tab", u"99_Обслуживание.panel", u"ВалидацияГОСТ.pushbutton", u"script.py"),
            "rollback": _os.path.join(extension_dir, u"Разработка.tab", u"99_Обслуживание.panel", u"ОтменитьРазмещение.pushbutton", u"script.py"),
            "family_diagnostics": _os.path.join(extension_dir, u"Разработка.tab", u"04_Розетки.panel", u"99_ДиагностикаСемейств.pushbutton", u"script.py"),
        }
        
        for k, v in FALLBACK_SCRIPTS.items():
            TOOL_SCRIPTS[k] = v

        last_status = [0]
        last_mtime_ns = [0]
        last_cmd = [""]
        pending_jobs = []
        needs_raise = [False]
        last_raise = [0]
        pending_lock = _threading.Lock()
        last_cancel_time = [0]

        def _parse_command(cmd):
            if parse_command:
                try:
                    return parse_command(cmd)
                except Exception:
                    pass

            tool_id = None
            job_id = None
            mode = None
            action = None

            if cmd == "cancel" or cmd.startswith("run:cancel"):
                action = "cancel"
            elif cmd.startswith("run:"):
                parts = cmd.split(":")
                if len(parts) >= 2 and parts[1]:
                    tool_id = parts[1]
                    action = "run"
                if len(parts) >= 3 and parts[2]:
                    job_id = parts[2]
                if len(parts) >= 4 and parts[3]:
                    mode = parts[3]
            elif cmd:
                tool_id = cmd
                action = "run"

            return {"action": action, "tool_id": tool_id, "job_id": job_id, "mode": mode}

        def _dispatch_command(cmd):
            try:
                data = _parse_command(cmd)
                action = data.get("action")
                if action == "cancel":
                    with pending_lock:
                        pending_jobs[:] = []
                        last_cancel_time[0] = _time.time()
                    debug_log(u"Cancellation requested")
                    return True, False

                if action != "run":
                    return False, False

                tool_id = data.get("tool_id")
                job_id = data.get("job_id")
                mode = data.get("mode")

                if tool_id:
                    with pending_lock:
                        pending_jobs.append({
                            "tool_id": tool_id,
                            "job_id": job_id,
                            "enqueue_time": _time.time(),
                            "mode": mode,
                        })
                    debug_log(u"Job queued: tool_id={0} job_id={1}".format(tool_id, job_id))
                    if job_id:
                        try:
                            legacy_path = _os.path.join(TEMP_DIR, u"eom_hub_command_{0}.txt".format(job_id))
                            if _os.path.exists(legacy_path):
                                _os.remove(legacy_path)
                        except Exception:
                            pass
                    return True, True
            except Exception as e:
                debug_log(u"ERROR parsing cmd: " + _to_unicode(e))
            return False, False

        def write_status():
            """Write status file for Hub."""
            try:
                uiapp = uiapp_ref
                uidoc = uiapp.ActiveUIDocument if uiapp else None
                doc = uidoc.Document if uidoc else None
                
                status = {
                    "connected": doc is not None,
                    "document": getattr(doc, "Title", None) if doc else None,
                    "documentPath": getattr(doc, "PathName", None) if doc else None,
                    "revitVersion": getattr(uiapp.Application, "VersionNumber", None) if uiapp else None,
                    "tempDir": TEMP_DIR,
                    "sessionId": session_id,
                    "commandFile": COMMAND_FILE,
                    "resultFile": RESULT_FILE,
                    "timestamp": _time.time(),
                }

                json_str = _json.dumps(status, ensure_ascii=False, indent=2)
                f = io.open(STATUS_FILE, 'w', encoding='utf-8')
                f.write(json_str)
                f.close()
                if STATUS_FILE_ROOT:
                    try:
                        f = io.open(STATUS_FILE_ROOT, 'w', encoding='utf-8')
                        f.write(json_str)
                        f.close()
                    except Exception:
                        pass
            except Exception:
                # debug_log("ERROR write_status: " + str(e))
                pass

        try:
            string_types = (basestring,)
        except Exception:
            string_types = (str,)

        def process_tool(uiapp, doc, tool_id=None, job_id=None, enqueue_time=None):
            """Execute tool script and capture output."""
            tool_id = tool_id or "unknown"
            job_id = job_id or "job_{0}_{1}".format(tool_id, int(_time.time()))
            enqueue_time = enqueue_time or _time.time()
            script_path = TOOL_SCRIPTS.get(tool_id)
            
            # Try to resolve path-style tool id directly
            if (not script_path) and isinstance(tool_id, string_types):
                try:
                    # tool_id might come in as utf-8 bytes or unicode
                    if isinstance(tool_id, str):
                        tid = tool_id.decode('utf-8', 'ignore')
                    else:
                        tid = tool_id
                        
                    # Also ensure tab_dirs are checked
                    rel_path = tid.replace(u"/", _os.sep)
                    for t_dir in tab_dirs:
                        candidate = _os.path.join(t_dir, rel_path, u"script.py")
                        if _os.path.exists(candidate):
                            script_path = candidate
                            break
                except Exception:
                    pass
                    
            debug_log(u"process_tool start tool_id={0} job_id={1}".format(tool_id, job_id))
            
            if script_path:
                debug_log(u"script_path={0}".format(script_path))
              
            try:
                if not script_path or not _os.path.exists(script_path):
                    result = {
                        "job_id": job_id,
                        "tool_id": tool_id,
                        "status": "error",
                        "error": u"Script not found for tool: {} (path: {})".format(tool_id, script_path),
                        "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 1},
                    }
                    write_result_json(result)
                    write_job_result_json(job_id, result)
                    return

                # Check cancellation
                if enqueue_time < last_cancel_time[0]:
                    result = {
                        "job_id": job_id,
                        "tool_id": tool_id,
                        "status": "cancelled",
                        "executionTime": 0,
                        "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 0},
                        "details": []
                    }
                    write_result_json(result)
                    write_job_result_json(job_id, result)
                    return

                # Write "running" marker
                try:
                    running_marker = {
                        "job_id": job_id,
                        "tool_id": tool_id,
                        "status": "running",
                        "message": u"Р’С‹РїРѕР»РЅСЏРµС‚СЃСЏ РІ Revit...",
                        "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 0},
                        "timestamp": _time.time(),
                    }
                    write_result_json(running_marker)
                    write_job_result_json(job_id, running_marker)
                except:
                    pass

                import sys
                import io

                class SafeStringIO(io.StringIO):
                    def __init__(self):
                        io.StringIO.__init__(self)
                        self.encoding = 'utf-8'

                    def write(self, s):
                        try:
                            if isinstance(s, str): # bytes in Py2
                                s = s.decode('utf-8', 'replace')
                            io.StringIO.write(self, s)
                        except Exception:
                            pass

                execution_start = _time.time()
                script_error = None
                hub_summary = None
                cancelled_by_user = False
                env_backup = {}
                ran_via_pyrevit = False
                pyrevit_info = None

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                captured_stdout = None
                captured_stderr = None
                root_logger = None
                old_handlers = []
                old_sys_path = None

                try:
                    # Set environment variables
                    try:
                        env_backup["EOM_HUB_MODE"] = _os.environ.get("EOM_HUB_MODE")
                        env_backup["EOM_HUB_JOB_ID"] = _os.environ.get("EOM_HUB_JOB_ID")
                        env_backup["EOM_HUB_TOOL_ID"] = _os.environ.get("EOM_HUB_TOOL_ID")
                        env_backup["EOM_SESSION_ID"] = _os.environ.get("EOM_SESSION_ID")

                        _os.environ["EOM_HUB_MODE"] = "1"
                        _os.environ["EOM_HUB_JOB_ID"] = _to_unicode(job_id)
                        _os.environ["EOM_HUB_TOOL_ID"] = _to_unicode(tool_id)
                        _os.environ["EOM_SESSION_ID"] = _to_unicode(session_id)
                    except Exception:
                        env_backup = {}

                    # Try to execute via pyRevit command (like ribbon click)
                    try:
                        ran_via_pyrevit, pyrevit_info = run_tool_via_pyrevit_command(script_path)
                    except Exception as run_err:
                        ran_via_pyrevit = False
                        pyrevit_info = run_err

                    if ran_via_pyrevit:
                        try:
                            avg_minutes, min_minutes, max_minutes = get_time_savings_for_tool(tool_id)
                            hub_summary = {
                                "runner": "pyrevit_command",
                                "command": _to_unicode(pyrevit_info),
                            }
                            if avg_minutes is None:
                                if min_minutes is not None and max_minutes is not None:
                                    avg_minutes = (float(min_minutes) + float(max_minutes)) / 2.0
                                elif min_minutes is not None:
                                    avg_minutes = min_minutes
                                elif max_minutes is not None:
                                    avg_minutes = max_minutes

                            if min_minutes is None and avg_minutes is not None:
                                min_minutes = avg_minutes
                            if max_minutes is None and avg_minutes is not None:
                                max_minutes = avg_minutes

                            if avg_minutes is not None:
                                hub_summary["time_saved_minutes"] = avg_minutes
                            if min_minutes is not None:
                                hub_summary["time_saved_minutes_min"] = min_minutes
                            if max_minutes is not None:
                                hub_summary["time_saved_minutes_max"] = max_minutes
                        except Exception:
                            hub_summary = None
                    else:
                        # Capture stdout/stderr for direct exec
                        captured_stdout = SafeStringIO()
                        captured_stderr = SafeStringIO()
                        sys.stdout = captured_stdout
                        sys.stderr = captured_stderr

                        # Redirect logging
                        import logging
                        root_logger = logging.getLogger()
                        old_handlers = list(root_logger.handlers)
                        for h in old_handlers:
                            root_logger.removeHandler(h)

                        safe_handler = logging.StreamHandler(captured_stderr)
                        root_logger.addHandler(safe_handler)

                        # Execute the script
                        tool_dir = _os.path.dirname(script_path)
                        old_sys_path = list(sys.path)
                        if tool_dir and tool_dir not in sys.path:
                            sys.path.insert(0, tool_dir)

                        try:
                            if 'orchestrator' in sys.modules:
                                del sys.modules['orchestrator']
                        except Exception:
                            pass

                        script_globals = {
                            '__revit__': uiapp,
                            '__file__': script_path,
                            '__name__': '__main__',
                            '__window__': None,
                            'sys': sys,
                            'doc': doc,
                            'uidoc': uiapp.ActiveUIDocument if uiapp else None,
                            'EOM_HUB_MODE': True,
                            'EOM_HUB_JOB_ID': job_id,
                            'EOM_HUB_TOOL_ID': tool_id,
                            'EOM_SESSION_ID': session_id,
                            'EOM_IS_CANCELLED': lambda: last_cancel_time[0] > execution_start,
                        }

                        # Read script as UTF-8
                        with io.open(script_path, 'r', encoding='utf-8') as f:
                            script_code = f.read()

                        # EXECUTE
                        exec(script_code, script_globals)

                        try:
                            maybe_summary = script_globals.get('EOM_HUB_RESULT')
                            if isinstance(maybe_summary, dict):
                                hub_summary = maybe_summary
                        except Exception:
                            hub_summary = None

                except BaseException as script_ex:
                    script_error = script_ex
                    try:
                        cancelled_by_user = isinstance(script_ex, SystemExit)
                    except Exception:
                        cancelled_by_user = False
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr

                    if root_logger is not None:
                        try:
                            for h in root_logger.handlers:
                                root_logger.removeHandler(h)
                            for h in old_handlers:
                                root_logger.addHandler(h)
                        except Exception:
                            pass

                    if old_sys_path is not None:
                        try:
                            sys.path[:] = old_sys_path
                        except Exception:
                            pass

                    try:
                        if env_backup:
                            for key, val in env_backup.items():
                                if val is None:
                                    try:
                                        del _os.environ[key]
                                    except Exception:
                                        pass
                                else:
                                    try:
                                        _os.environ[key] = val
                                    except Exception:
                                        pass
                    except Exception:
                        pass

                execution_time = _time.time() - execution_start

                stdout_content = captured_stdout.getvalue() if captured_stdout else ""
                stderr_content = captured_stderr.getvalue() if captured_stderr else ""
                
                details = []
                if stdout_content:
                    for i, line in enumerate(stdout_content.split('\n')):
                        if line.strip():
                            details.append({
                                "id": u"stdout_{}".format(i),
                                "status": "success",
                                "message": line.strip()[:200],
                            })
                
                if stderr_content:
                    for i, line in enumerate(stderr_content.split('\n')):
                        if line.strip():
                            details.append({
                                "id": u"stderr_{}".format(i),
                                "status": "error",
                                "message": line.strip()[:200],
                            })
                
                stats = None
                try:
                    if isinstance(hub_summary, dict) and isinstance(hub_summary.get('stats'), dict):
                        stats = hub_summary.get('stats')
                except Exception:
                    stats = None

                if script_error and not cancelled_by_user:
                    result = {
                        "job_id": job_id,
                        "tool_id": tool_id,
                        "status": "error",
                        "error": _to_unicode(script_error),
                        "executionTime": execution_time,
                        "stats": stats or {"total": 1, "processed": 0, "skipped": 0, "errors": 1},
                        "details": details
                    }
                elif cancelled_by_user:
                    result = {
                        "job_id": job_id,
                        "tool_id": tool_id,
                        "status": "cancelled",
                        "executionTime": execution_time,
                        "stats": stats or {"total": 0, "processed": 0, "skipped": 0, "errors": 0},
                        "details": details
                    }
                else:
                    result = {
                        "job_id": job_id,
                        "tool_id": tool_id,
                        "status": "completed",
                        "executionTime": execution_time,
                        "stats": stats or {"total": 1, "processed": 1, "skipped": 0, "errors": 0},
                        "details": details
                    }

                if isinstance(hub_summary, dict):
                    result["summary"] = hub_summary

                try:
                    result["timestamp"] = _time.time()
                except Exception:
                    pass
                 
                write_result_json(result)
                write_job_result_json(job_id, result)
                debug_log(u"process_tool finished status=" + result.get("status", "unknown"))

                try:
                    user32 = ctypes.windll.user32
                    hwnd = user32.FindWindowW(None, u"EOM Hub")
                    if hwnd and hwnd != 0:
                        user32.ShowWindow(hwnd, 9)
                        user32.SetForegroundWindow(hwnd)
                except:
                    pass
                      
            except Exception as e:
                debug_log(u"process_tool CRASH: " + _to_unicode(e))
                result = {
                    "job_id": job_id,
                    "tool_id": tool_id,
                    "status": "error",
                    "error": _to_unicode(e),
                    "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 1},
                }
                write_result_json(result)
                write_job_result_json(job_id, result)

        # Expose for runner mode
        global _EOM_PROCESS_TOOL
        _EOM_PROCESS_TOOL = process_tool

        postcommand_id = get_postcommand_id()
        postcommand_cmd_id = None
        if postcommand_id:
            try:
                from Autodesk.Revit.UI import RevitCommandId
                postcommand_cmd_id = RevitCommandId.LookupCommandId(postcommand_id)
                if postcommand_cmd_id is None:
                    debug_log(u"PostCommand id not resolved: " + _to_unicode(postcommand_id))
            except Exception as e:
                debug_log(u"PostCommand lookup failed: " + _to_unicode(e))
                postcommand_cmd_id = None

        # Default to direct-run mode unless explicitly enabled
        try:
            use_post = os_mod.environ.get("EOM_HUB_USE_POSTCOMMAND")
            if not use_post or str(use_post).strip().lower() in ("0", "false", "no"):
                postcommand_cmd_id = None
                debug_log(u"PostCommand disabled via EOM_HUB_USE_POSTCOMMAND")
        except Exception:
            pass

        runner_lock_path = get_runner_lock_path()

        class ApplyHandler(IExternalEventHandler):
            def Execute(self, uiapp):
                try:
                    debug_log(u"ApplyHandler.Execute called")
                    uidoc = uiapp.ActiveUIDocument if uiapp else None
                    doc = uidoc.Document if uidoc else None
                    job = None
                    queue_len = 0
                    with pending_lock:
                        queue_len = len(pending_jobs)
                        if pending_jobs:
                            job = pending_jobs.pop(0)
                    try:
                        debug_log(u"ApplyHandler queue_len={0} job_present={1}".format(queue_len, bool(job)))
                    except Exception:
                        pass
                    if not job:
                        return

                    tool_id = job.get("tool_id")
                    job_id = job.get("job_id")
                    enqueue_time = job.get("enqueue_time", 0)

                    tool_postcommand_id = None
                    tool_postcommand_cmd_id = None
                    try:
                        try:
                            temp_root = os_mod.environ.get("TEMP") or os_mod.environ.get("TMP") or tempfile.gettempdir()
                            cfg_path = os_mod.path.join(temp_root, "eom_hub_tool_command_map.txt")
                            debug_log(u"Tool map path={0} exists={1}".format(_to_unicode(cfg_path), _os.path.exists(cfg_path)))
                            if not _os.path.exists(cfg_path):
                                debug_log(u"Tool map missing for tool_id={0}".format(_to_unicode(tool_id)))
                        except Exception:
                            pass
                        tool_postcommand_id = get_tool_postcommand_id(tool_id)
                        debug_log(u"Tool PostCommand id raw={0}".format(_to_unicode(tool_postcommand_id)))
                        if not tool_postcommand_id:
                            debug_log(u"Tool PostCommand id not found for tool_id={0}".format(_to_unicode(tool_id)))
                        if tool_postcommand_id:
                            from Autodesk.Revit.UI import RevitCommandId
                            tool_postcommand_cmd_id = RevitCommandId.LookupCommandId(tool_postcommand_id)
                            if tool_postcommand_cmd_id is None:
                                debug_log(u"Tool PostCommand id not resolved: " + _to_unicode(tool_postcommand_id))
                    except Exception as e:
                        debug_log(u"Tool PostCommand lookup failed: " + _to_unicode(e))
                        tool_postcommand_cmd_id = None

                    is_quiescent = None
                    try:
                        app = uiapp.Application if uiapp else None
                        is_quiescent = getattr(app, "IsQuiescent", None)
                    except Exception:
                        is_quiescent = None

                    try:
                        from hub_run_guard import should_defer_run
                        if should_defer_run(doc is not None, is_quiescent):
                            with pending_lock:
                                pending_jobs.insert(0, job)
                            needs_raise[0] = True
                            debug_log(u"ApplyHandler: defer run doc={0} quiescent={1}".format(doc is not None, _to_unicode(is_quiescent)))
                            return
                    except Exception:
                        if doc is None:
                            with pending_lock:
                                pending_jobs.insert(0, job)
                            needs_raise[0] = True
                            debug_log(u"ApplyHandler: doc is None, defer")
                            return

                    if postcommand_cmd_id:
                        try:
                            # If runner is busy, re-queue and wait
                            if runner_lock_path and _os.path.exists(runner_lock_path):
                                with pending_lock:
                                    pending_jobs.insert(0, job)
                                needs_raise[0] = True
                                return

                            set_runner_env(tool_id, job_id)
                            try:
                                with io.open(runner_lock_path, "w", encoding="utf-8") as f:
                                    f.write(u"{0}|{1}".format(_to_unicode(tool_id), _to_unicode(job_id)))
                            except Exception:
                                pass

                            uiapp.PostCommand(postcommand_cmd_id)
                            # Job will be executed via external command context
                            with pending_lock:
                                has_more = bool(pending_jobs)
                            if has_more:
                                needs_raise[0] = True
                            return
                        except Exception as e:
                            debug_log(u"PostCommand failed, fallback to direct run: " + _to_unicode(e))
                            clear_runner_env()
                            try:
                                if runner_lock_path and _os.path.exists(runner_lock_path):
                                    _os.remove(runner_lock_path)
                            except Exception:
                                pass

                    if tool_postcommand_cmd_id:
                        try:
                            debug_log(u"Tool PostCommand invoke: " + _to_unicode(tool_postcommand_id))
                            uiapp.PostCommand(tool_postcommand_cmd_id)
                            with pending_lock:
                                has_more = bool(pending_jobs)
                            if has_more:
                                needs_raise[0] = True
                            return
                        except Exception as e:
                            debug_log(u"Tool PostCommand failed, fallback to hub/direct: " + _to_unicode(e))

                    process_tool(uiapp, doc, tool_id=tool_id, job_id=job_id, enqueue_time=enqueue_time)
                    with pending_lock:
                        has_more = bool(pending_jobs)
                    if has_more:
                        needs_raise[0] = True
                except Exception as e:
                    debug_log(u"ApplyHandler ERROR: " + _to_unicode(e))

            def GetName(self):
                return "EOM Apply Handler"

        handler = ApplyHandler()
        try:
            event = ExternalEvent.Create(handler)
        except Exception as e:
            debug_log(u"ERROR: ExternalEvent.Create failed: " + _to_unicode(e))
            _EOM_MONITOR_STARTED = False
            return
        _EOM_HUB_HANDLER = handler
        _EOM_HUB_EVENT = event

        debug_log(u"Monitor started")

        def monitor():
            debug_log(u"Monitor thread running")
            loop_count = [0]
            while True:
                try:
                    now = _time.time()
                    loop_count[0] += 1
                     
                    if loop_count[0] % 20 == 0:
                        # Log less frequently
                        pass
                     
                    # Update status every 5 seconds
                    if now - last_status[0] > 5:
                        write_status()
                        last_status[0] = now
                     
                    # Monitor single command file (UniPlagin-style)
                    try:
                        if _os.path.exists(COMMAND_FILE):
                            mtime = _os.path.getmtime(COMMAND_FILE)
                            if mtime > last_mtime_ns[0]:
                                last_mtime_ns[0] = mtime
                                with io.open(COMMAND_FILE, 'r', encoding='utf-8') as f:
                                    cmd = f.read().strip()

                                if cmd:
                                    handled, should_raise = _dispatch_command(cmd)
                                    if handled:
                                        try:
                                            with io.open(COMMAND_FILE, 'w', encoding='utf-8') as f:
                                                f.write(u"")
                                            try:
                                                last_mtime_ns[0] = _os.path.getmtime(COMMAND_FILE)
                                            except Exception:
                                                pass
                                        except Exception:
                                            pass
                                    if should_raise:
                                        try:
                                            event.Raise()
                                            needs_raise[0] = False
                                        except Exception:
                                            needs_raise[0] = True
                    except Exception as e:
                        debug_log(u"ERROR reading COMMAND_FILE: " + _to_unicode(e))

                    # Monitor queued per-job command files from Hub
                    try:
                        cmd_files = []
                        try:
                            # Use glob (which returns unicode because COMMAND_FILES_GLOB is unicode)
                            cmd_files = list(_glob.glob(COMMAND_FILES_GLOB))
                        except Exception:
                            cmd_files = []

                        if cmd_files:
                            try:
                                cmd_files.sort(key=lambda p: _os.path.getmtime(p))
                            except Exception:
                                pass

                        for cmd_path in cmd_files[:50]:
                            try:
                                with io.open(cmd_path, 'r', encoding='utf-8') as f:
                                    cmd = f.read().strip()
                                
                                # Always delete command file immediately to prevent re-processing loop
                                try:
                                    _os.remove(cmd_path)
                                except Exception:
                                    pass
                                    
                                if not cmd:
                                    continue

                                handled, should_raise = _dispatch_command(cmd)
                                if should_raise:
                                    try:
                                        event.Raise()
                                        needs_raise[0] = False
                                    except Exception:
                                        needs_raise[0] = True

                            except Exception as e:
                                debug_log(u"ERROR reading cmd file: " + _to_unicode(e))
                    except Exception as e:
                        debug_log(u"ERROR scanning cmd files: " + _to_unicode(e))

                    try:
                        if needs_raise[0]:
                            with pending_lock:
                                has_pending = bool(pending_jobs)
                            if has_pending and (now - last_raise[0]) > 0.5:
                                try:
                                    event.Raise()
                                    needs_raise[0] = False
                                    last_raise[0] = now
                                except Exception:
                                    pass
                    except Exception:
                        pass

                except Exception as e:
                    debug_log(u"ERROR in monitor: " + _to_unicode(e))
                try:
                    _time.sleep(0.5)
                except Exception:
                    pass

        if start_thread:
            thread = _threading.Thread(target=monitor)
            sys.eom_hub_monitor_thread = thread
            thread.daemon = True
            thread.start()
            
            # Write status immediately
            write_status()

    except Exception as e:
        try:
            # Fallback log (avoid ascii codec errors)
            msg = _to_unicode(e)
            try:
                sys.stdout.write(msg.encode('utf-8', 'replace') + "\n")
            except Exception:
                pass
        except Exception:
            pass


def _run_job_once(tool_id, job_id):
    """Run a single Hub job inside an external command context."""
    try:
        start_command_monitor(start_thread=False)
    except Exception:
        pass

    try:
        uiapp = __revit__  # noqa: F821
    except Exception:
        uiapp = None

    uidoc = uiapp.ActiveUIDocument if uiapp else None
    doc = uidoc.Document if uidoc else None

    try:
        if _EOM_PROCESS_TOOL:
            _EOM_PROCESS_TOOL(uiapp, doc, tool_id=tool_id, job_id=job_id, enqueue_time=time.time())
    finally:
        _clear_runner_env()
        try:
            lock_path = _get_runner_lock_path()
            if lock_path and os.path.exists(lock_path):
                os.remove(lock_path)
        except Exception:
            pass


def main():
    session_id = _get_session_id()

    run_tool_id = os.environ.get("EOM_HUB_RUN_TOOL_ID")
    if run_tool_id:
        run_job_id = os.environ.get("EOM_HUB_RUN_JOB_ID") or u"job_{0}_{1}".format(run_tool_id, int(time.time()))
        _run_job_once(run_tool_id, run_job_id)
        return

    # Start command monitor
    start_command_monitor()

    # If Hub already running for this session, just focus and exit
    hub_session_path = _get_hub_session_path(session_id)
    if hub_session_path and os.path.exists(hub_session_path):
        is_hub_running()
        return

    hub_exe = find_hub_exe()
    if hub_exe:
        hub_exe = _to_unicode(hub_exe)
        try:
            launch_env = os.environ.copy()
            temp_root = tempfile.gettempdir()
            if temp_root:
                launch_env["TEMP"] = _to_unicode(temp_root)
                launch_env["TMP"] = _to_unicode(temp_root)
            launch_env["EOM_SESSION_ID"] = _to_unicode(session_id)
            subprocess.Popen([hub_exe, u"--session={0}".format(_to_unicode(session_id))], close_fds=True, env=launch_env)
        except Exception:
            try:
                os.startfile(_to_unicode(hub_exe))
            except Exception:
                pass
    else:
        # Fallback: show message that Hub not found
        try:
            from pyrevit import forms
            forms.alert(
                u"EOMHub.exe РЅРµ РЅР°Р№РґРµРЅ.\n\n"
                u"РЎРѕР±РµСЂРёС‚Рµ Hub РєРѕРјР°РЅРґРѕР№:\n"
                u"cd C:\\Users\\anton\\EOMTemplateTools\\EOMHub\n"
                u".\\build.ps1"
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()





