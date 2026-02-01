# -*- coding: utf-8 -*-
"""EOM Hub - Web interface launcher with file-based communication."""

__title__ = "EOM\nHub"
__author__ = "EOM Team"

import os
import sys
import ctypes
import threading
import json
import time
import uuid
import tempfile
import subprocess
import io

# Session binding (Hub <-> Revit)
SESSION_ID = None
_EOM_MONITOR_STARTED = False
_EOM_HUB_EVENT = None
_EOM_HUB_HANDLER = None


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
    script_dir = os.path.dirname(__file__)
    # script_dir = .../EOMTemplateTools.extension/EOM.tab/01_Хаб.panel/Hub.pushbutton
    extension_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    extensions_dir = os.path.dirname(extension_dir)

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


def start_command_monitor():
    """Start background monitoring of commands from EOMHub."""
    import io
    import json as _json
    import os as _os
    import threading as _threading
    import time as _time
    import glob as _glob
     
    try:
        global _EOM_MONITOR_STARTED, _EOM_HUB_EVENT, _EOM_HUB_HANDLER
        # Add lib to path
        script_dir = _os.path.dirname(__file__)
        # Use the extension that is actually loaded by Revit
        extension_dir = _os.path.dirname(_os.path.dirname(_os.path.dirname(script_dir)))
        lib_dir = _os.path.join(extension_dir, "lib")
        if lib_dir not in sys.path:
            sys.path.insert(0, lib_dir)
            
        # Singleton check
        # Singleton check with thread liveness verification
        monitor_thread = getattr(sys, "eom_hub_monitor_thread", None)
        if monitor_thread and monitor_thread.is_alive():
            return
            
        sys.eom_hub_monitor_started = True

        from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent
        import tempfile

        # Use USERPROFILE for logs to ensure visibility and persistence
        user_profile = _os.environ.get("USERPROFILE")
        DEBUG_LOG = _os.path.join(user_profile, "eom_debug.log")

        def debug_log(msg):
            try:
                timestamp = _time.strftime("%Y-%m-%d %H:%M:%S")
                with io.open(DEBUG_LOG, 'a', encoding='utf-8') as f:
                    f.write(u"[{0}] {1}\n".format(timestamp, msg))
            except:
                pass

        debug_log("Monitor init attempt...")
        
        # If we are here, previous thread died or never started. 
        # Clean up any stale event if possible (though we can't easily dispose old ones)
        
        _EOM_MONITOR_STARTED = True

        session_id = _get_session_id()
        TEMP_DIR = tempfile.gettempdir()
        # Use fixed filenames for simpler communication with Hub
        COMMAND_FILE = _os.path.join(TEMP_DIR, "eom_hub_command.txt")
        COMMAND_FILES_GLOB = _os.path.join(TEMP_DIR, "eom_hub_command_*.txt")
        STATUS_FILE = _os.path.join(TEMP_DIR, "eom_hub_status.json")
        RESULT_FILE = _os.path.join(TEMP_DIR, "eom_hub_result.json")
        debug_log("Monitor init")
        debug_log("TEMP_DIR=" + TEMP_DIR)
        debug_log("SESSION_ID=" + str(session_id))
        debug_log("COMMAND_FILE=" + COMMAND_FILE)
        debug_log("STATUS_FILE=" + STATUS_FILE)
        debug_log("RESULT_FILE=" + RESULT_FILE)

        def write_result_json(payload):
            """Write legacy result JSON atomically (eom_hub_result.json)."""
            try:
                tmp_path = RESULT_FILE + ".tmp"
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
                job_result_file = _os.path.join(TEMP_DIR, "eom_hub_result_{0}.json".format(job_id))
                tmp_path = job_result_file + ".tmp"
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
                    job_result_file = _os.path.join(TEMP_DIR, "eom_hub_result_{0}.json".format(job_id))
                    with io.open(job_result_file, 'w', encoding='utf-8') as f:
                        _json.dump(payload, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        # Save references before globals cleanup
        script_path_self = __file__
        uiapp_ref = None
        try:
            uiapp_ref = __revit__  # noqa: F821
        except Exception:
            uiapp_ref = None
        
        # Tool ID -> script path mapping
        # Dynamic scanning of EOM.tab and Разработка.tab
        TOOL_SCRIPTS = {}
        
        tab_dirs = [
            _os.path.join(extension_dir, u"EOM.tab"),
            _os.path.join(extension_dir, u"Разработка.tab")
        ]
        
        try:
            for tab_dir in tab_dirs:
                if _os.path.exists(tab_dir):
                    for root, dirs, files in _os.walk(tab_dir):
                        base = _os.path.basename(root)
                        if not base.endswith(".pushbutton"):
                            continue

                        # Skip Hub itself to prevent recursion loop if called
                        if "Hub" in base or u"Хаб" in base:
                            continue

                        script_file = _os.path.join(root, "script.py")
                        if not _os.path.exists(script_file):
                            continue

                        rel_dir = _os.path.relpath(root, tab_dir)
                        rel_id = rel_dir.replace("\\", "/")
                        TOOL_SCRIPTS[rel_id] = script_file

                        # Use full folder name as ID (matches what backend typically sends now)
                        TOOL_SCRIPTS[base] = script_file

                        # Legacy id support (folder name without .pushbutton)
                        legacy_id = base.replace(".pushbutton", "")
                        if legacy_id not in TOOL_SCRIPTS:
                            TOOL_SCRIPTS[legacy_id] = script_file
        except Exception:
            pass

        # Legacy/Hardcoded fallbacks (can overlay dynamic ones)
        FALLBACK_SCRIPTS = {
            "lights_center": _os.path.join(extension_dir, u"EOM.tab", u"02_Освещение.panel", u"СветПоЦентру.pushbutton", "script.py"),
            "lights_entrance": _os.path.join(extension_dir, u"EOM.tab", u"02_Освещение.panel", u"СветУВхода.pushbutton", "script.py"),
            "lights_elevator": _os.path.join(extension_dir, u"EOM.tab", u"02_Освещение.panel", u"СветВЛифтах.pushbutton", "script.py"),
            "lights_pk": _os.path.join(extension_dir, u"EOM.tab", u"02_Освещение.panel", u"СветПК.pushbutton", "script.py"),
            "panel_door": _os.path.join(extension_dir, u"EOM.tab", u"03_ЩитыВыключатели.panel", u"ЩитНадДверью.pushbutton", "script.py"),
            "switches_doors": _os.path.join(extension_dir, u"EOM.tab", u"03_ЩитыВыключатели.panel", u"ВыключателиУДверей.pushbutton", "script.py"),
            "entrance_numbering": _os.path.join(extension_dir, u"EOM.tab", u"03_ЩитыВыключатели.panel", u"НумерацияПодъезда.pushbutton", "script.py"),
            "sockets_general": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"01_Общие.pushbutton", "script.py"),
            "kitchen_block": _os.path.join(extension_dir, u"Разработка.tab", u"04_Розетки.panel", u"02_КухняБлок.pushbutton", "script.py"),
            "kitchen_general": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"03_КухняОбщие.pushbutton", "script.py"),
            "ac_sockets": _os.path.join(extension_dir, u"Разработка.tab", u"04_Розетки.panel", u"04_Кондиционеры.pushbutton", "script.py"),
            "wet_zones": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"05_ВлажныеЗоны.pushbutton", "script.py"),
            "low_voltage": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"06_Слаботочка.pushbutton", "script.py"),
            "shdup": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"07_ШДУП.pushbutton", "script.py"),
            "storage_rooms": _os.path.join(extension_dir, u"Разработка.tab", u"04_Розетки.panel", u"08_Кладовые.pushbutton", "script.py"),
            "magic_button": _os.path.join(extension_dir, u"EOM.tab", u"10_АвтоРазмещение.panel", u"00_ВолшебнаяКнопка.pushbutton", "script.py"),
            "gost_validation": _os.path.join(extension_dir, u"EOM.tab", u"99_Обслуживание.panel", u"ВалидацияГОСТ.pushbutton", "script.py"),
            "rollback": _os.path.join(extension_dir, u"EOM.tab", u"99_Обслуживание.panel", u"ОтменитьРазмещение.pushbutton", "script.py"),
            "family_diagnostics": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"99_ДиагностикаСемейств.pushbutton", "script.py"),
        }
        
        # Merge fallbacks (fallbacks take precedence if we want to support short IDs)
        # But actually, let's allow dynamic IDs to work too
        for k, v in FALLBACK_SCRIPTS.items():
            TOOL_SCRIPTS[k] = v

        last_status = [0]
        last_mtime_ns = [0]
        last_mtime_ns = [0]
        last_cmd = [""]
        pending_jobs = []
        needs_raise = [False]
        pending_lock = _threading.Lock()
        last_cancel_time = [0]

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
                    "scriptPath": script_path_self,
                    "timestamp": _time.time(),
                }

                json_str = _json.dumps(status, ensure_ascii=False, indent=2)
                f = io.open(STATUS_FILE, 'w', encoding='utf-8')
                f.write(json_str)
                f.close()
            except Exception as e:
                debug_log("ERROR write_status: " + str(e))

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
            if (not script_path) and tab_dir and isinstance(tool_id, string_types):
                # Try to resolve path-style tool id directly
                try:
                    rel_path = tool_id.replace("/", _os.sep)
                    candidate = _os.path.join(tab_dir, rel_path, "script.py")
                    if _os.path.exists(candidate):
                        script_path = candidate
                except Exception:
                    pass
            debug_log("process_tool start tool_id={0} job_id={1} script_path={2}".format(tool_id, job_id, script_path))
              
            try:
                if script_path:
                    debug_log("process_tool script exists={0}".format(_os.path.exists(script_path)))
                 
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

                # Check cancellation before starting (using timestamps to handle race conditions)
                # If job was enqueued BEFORE the last cancel request, it should be skipped.
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
                        "message": u"Выполняется в Revit...",
                        "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 0},
                        "timestamp": _time.time(),
                    }
                    write_result_json(running_marker)
                    write_job_result_json(job_id, running_marker)
                except:
                    pass

                # Capture stdout/stderr
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
                            # Last resort fallback
                            try:
                                io.StringIO.write(self, repr(s))
                            except:
                                pass

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                captured_stdout = SafeStringIO()
                captured_stderr = SafeStringIO()
                
                sys.stdout = captured_stdout
                sys.stderr = captured_stderr
                
                # Redirect logging handlers to capture stream
                import logging
                root_logger = logging.getLogger()
                old_handlers = list(root_logger.handlers)
                # Remove existing handlers to prevent writing to original stream
                for h in old_handlers:
                    root_logger.removeHandler(h)
                
                # Add our safe handler
                safe_handler = logging.StreamHandler(captured_stderr)
                # Force UTF-8 formatting if possible
                try:
                    safe_handler.stream = captured_stderr
                except:
                    pass
                root_logger.addHandler(safe_handler)
                
                execution_start = _time.time()
                script_error = None
                hub_summary = None
                cancelled_by_user = False
                env_backup = {}
                  
                try:
                    # Set environment variables
                    try:
                        env_backup["EOM_HUB_MODE"] = _os.environ.get("EOM_HUB_MODE")
                        env_backup["EOM_HUB_JOB_ID"] = _os.environ.get("EOM_HUB_JOB_ID")
                        env_backup["EOM_HUB_TOOL_ID"] = _os.environ.get("EOM_HUB_TOOL_ID")
                        env_backup["EOM_SESSION_ID"] = _os.environ.get("EOM_SESSION_ID")

                        _os.environ["EOM_HUB_MODE"] = "1"
                        _os.environ["EOM_HUB_JOB_ID"] = str(job_id)
                        _os.environ["EOM_HUB_TOOL_ID"] = str(tool_id)
                        _os.environ["EOM_SESSION_ID"] = str(session_id)
                    except Exception:
                        env_backup = {}

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
                    
                    with io.open(script_path, 'r', encoding='utf-8') as f:
                        script_code = f.read()
                    
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
                    try:
                        maybe_summary = script_globals.get('EOM_HUB_RESULT')
                        if isinstance(maybe_summary, dict):
                            hub_summary = maybe_summary
                    except Exception:
                        hub_summary = None
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    
                    # Restore logging handlers
                    try:
                        for h in root_logger.handlers:
                            root_logger.removeHandler(h)
                        for h in old_handlers:
                            root_logger.addHandler(h)
                    except Exception:
                        pass

                    try:
                        sys.path[:] = old_sys_path
                    except Exception:
                        pass

                    # Restore environment
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
                 
                stdout_content = captured_stdout.getvalue()
                stderr_content = captured_stderr.getvalue()
                
                # Try to parse saved time from stdout
                try:
                    import re
                    # Pattern matches: Сэкономлено времени: **~1.0 час**
                    # or: Сэкономлено времени: **~5 минут**
                    match = re.search(r"Сэкономлено времени:\s*\*\*(.*?)\*\*", stdout_content)
                    if match:
                        time_text = match.group(1)
                        minutes = 0.0
                        
                        if u"меньше минуты" in time_text:
                            minutes = 0.5
                        elif u"час" in time_text:
                            # Extract number (e.g. 1.0)
                            num_match = re.search(r"[\d\.]+", time_text)
                            if num_match:
                                minutes = float(num_match.group(0)) * 60.0
                        elif u"минут" in time_text:
                            # Extract number (e.g. 5)
                            num_match = re.search(r"[\d\.]+", time_text)
                            if num_match:
                                minutes = float(num_match.group(0))
                                
                        if minutes > 0:
                            if hub_summary is None:
                                hub_summary = {}
                            
                            # Only use parsed time if script didn't provide it explicitly
                            if 'time_saved_minutes' not in hub_summary:
                                hub_summary['time_saved_minutes'] = minutes
                                debug_log("Parsed saved time: {0} minutes".format(minutes))
                except Exception as e:
                    debug_log("Error parsing saved time: " + str(e))

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
                        "error": str(script_error),
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
                debug_log("process_tool finished status=" + result.get("status", "unknown"))

                # Bring Hub back to front
                try:
                    user32 = ctypes.windll.user32
                    hwnd = user32.FindWindowW(None, u"EOM Hub")
                    if hwnd and hwnd != 0:
                        user32.ShowWindow(hwnd, 9)
                        user32.SetForegroundWindow(hwnd)
                except:
                    pass
                      
            except Exception as e:
                result = {
                    "job_id": job_id,
                    "tool_id": tool_id,
                    "status": "error",
                    "error": str(e),
                    "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 1},
                }
                try:
                    write_result_json(result)
                    write_job_result_json(job_id, result)
                except:
                    pass
                debug_log("process_tool ERROR: " + str(e))

        class ApplyHandler(IExternalEventHandler):
            def Execute(self, uiapp):
                try:
                    debug_log("ApplyHandler.Execute called")
                    uidoc = uiapp.ActiveUIDocument if uiapp else None
                    doc = uidoc.Document if uidoc else None
                    if doc is None:
                        debug_log("ApplyHandler: doc is None, skip")
                        return

                    while True:
                        with pending_lock:
                            if not pending_jobs:
                                break
                            job = pending_jobs.pop(0)
                        debug_log("ApplyHandler processing job")

                        if isinstance(job, dict):
                            tool_id = job.get("tool_id")
                            job_id = job.get("job_id")
                            enqueue_time = job.get("enqueue_time", 0)
                        else:
                            # Legacy tuple support?
                            tool_id = job[0] if job and len(job) > 0 else None
                            job_id = job[1] if job and len(job) > 1 else None
                            enqueue_time = 0

                        process_tool(uiapp, doc, tool_id=tool_id, job_id=job_id, enqueue_time=enqueue_time)
                except Exception as e:
                    debug_log("ApplyHandler ERROR: " + str(e))

            def GetName(self):
                return "EOM Apply Handler"

        handler = ApplyHandler()
        try:
            event = ExternalEvent.Create(handler)
        except Exception as e:
            debug_log("ERROR: ExternalEvent.Create failed: " + str(e))
            _EOM_MONITOR_STARTED = False
            return
        _EOM_HUB_HANDLER = handler
        _EOM_HUB_EVENT = event

        debug_log("Monitor started")

        def monitor():
            debug_log("Monitor thread running")
            loop_count = [0]
            while True:
                try:
                    now = _time.time()
                    loop_count[0] += 1
                     
                    if loop_count[0] % 20 == 0:
                        exists = _os.path.exists(COMMAND_FILE)
                        debug_log("Loop {0}, COMMAND_FILE exists: {1}".format(loop_count[0], exists))
                     
                    # Update status every 5 seconds
                    if now - last_status[0] > 5:
                        write_status()
                        last_status[0] = now
                     
                    # Monitor queued per-job command files from Hub
                    try:
                        cmd_files = []
                        try:
                            cmd_files = list(_glob.glob(COMMAND_FILES_GLOB))
                        except Exception:
                            cmd_files = []

                        if cmd_files:
                            # Process in chronological order
                            try:
                                cmd_files.sort(key=lambda p: _os.path.getmtime(p))
                            except Exception:
                                pass

                        for cmd_path in cmd_files[:50]:
                            try:
                                with io.open(cmd_path, 'r', encoding='utf-8') as f:
                                    cmd = f.read().strip()
                                if not cmd:
                                    try:
                                        _os.remove(cmd_path)
                                    except Exception:
                                        pass
                                    continue

                                tool_id = None
                                job_id = None
                                if cmd == "cancel" or cmd.startswith("run:cancel"):
                                    # Handle cancellation
                                    with pending_lock:
                                        pending_jobs[:] = []
                                        last_cancel_time[0] = _time.time()
                                    debug_log("Cancellation requested - queue cleared")
                                    
                                    try:
                                        _os.remove(cmd_path)
                                    except Exception:
                                        pass
                                    continue
                                
                                if cmd.startswith("run:"):
                                    parts = cmd.split(":")
                                    if len(parts) >= 2 and parts[1]:
                                        tool_id = parts[1]
                                    if len(parts) >= 3 and parts[2]:
                                        job_id = parts[2]
                                elif cmd != "cancel":
                                    tool_id = cmd

                                if tool_id:
                                    with pending_lock:
                                        pending_jobs.append({
                                            "tool_id": tool_id,
                                            "job_id": job_id,
                                            "enqueue_time": _time.time(),
                                        })
                                    debug_log("Job queued (file): tool_id={0} job_id={1}".format(tool_id, job_id))

                                    try:
                                        event.Raise()
                                        needs_raise[0] = False
                                    except Exception:
                                        needs_raise[0] = True

                                # Delete command file after enqueue
                                try:
                                    _os.remove(cmd_path)
                                except Exception:
                                    pass
                            except Exception as e:
                                debug_log("ERROR reading cmd file: " + str(e))
                    except Exception as e:
                        debug_log("ERROR scanning cmd files: " + str(e))

                    # Monitor legacy single command file from Hub
                    if _os.path.exists(COMMAND_FILE):
                        try:
                            stat = _os.stat(COMMAND_FILE)
                            mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1000000000))
                        except Exception:
                            mtime_ns = 0

                        with io.open(COMMAND_FILE, 'r', encoding='utf-8') as f:
                            cmd = f.read().strip()

                        if cmd and (mtime_ns != last_mtime_ns[0] or cmd != last_cmd[0]):
                            last_mtime_ns[0] = mtime_ns
                            last_cmd[0] = cmd
                            debug_log("COMMAND_FILE changed! mtime_ns=" + str(mtime_ns))
                            debug_log("Command read: " + (cmd[:200] if cmd else "empty"))

                            tool_id = None
                            job_id = None
                            if cmd:
                                if cmd.startswith("run:"):
                                    parts = cmd.split(":")
                                    if len(parts) >= 2 and parts[1]:
                                        tool_id = parts[1]
                                    if len(parts) >= 3 and parts[2]:
                                        job_id = parts[2]
                                elif cmd != "cancel":
                                    tool_id = cmd

                            if tool_id:
                                debug_log("Command detected, tool_id=" + tool_id)

                                # Bring Revit to front
                                try:
                                    uiapp = uiapp_ref
                                    hwnd = int(uiapp.MainWindowHandle) if uiapp and getattr(uiapp, 'MainWindowHandle', None) else 0
                                    if hwnd:
                                        user32 = ctypes.windll.user32
                                        user32.ShowWindow(hwnd, 9)
                                        user32.SetForegroundWindow(hwnd)
                                except:
                                    pass
                                
                                with pending_lock:
                                    pending_jobs.append({
                                        "tool_id": tool_id,
                                        "job_id": job_id,
                                        "enqueue_time": _time.time(),
                                    })
                                debug_log("Job queued: tool_id={0} job_id={1}".format(tool_id, job_id))
                                debug_log("Pending jobs count: {0}".format(len(pending_jobs)))
                                
                                try:
                                    event.Raise()
                                    debug_log("Event raised successfully")
                                except Exception as e:
                                    debug_log("Event raise failed: {0}".format(str(e)))
                                
                                # Clear command file AFTER raising event to avoid race condition
                                with io.open(COMMAND_FILE, 'w', encoding='utf-8') as f:
                                    f.write(u"")
                                debug_log("Command file cleared")
                except Exception as e:
                    debug_log("ERROR in monitor: " + str(e))
                try:
                    _time.sleep(0.5)
                except Exception:
                    pass

        thread = _threading.Thread(target=monitor)
        sys.eom_hub_monitor_thread = thread
        thread.daemon = True
        thread.start()
        
        # Write status immediately
        write_status()

        try:
            debug_log("TOOL_SCRIPTS count=" + str(len(TOOL_SCRIPTS)))
            sample_keys = list(TOOL_SCRIPTS.keys())[:10]
            debug_log("TOOL_SCRIPTS sample=" + ", ".join(sample_keys))
        except Exception:
            pass

    except Exception as e:
        try:
            debug_log("START_MONITOR_ERROR: " + str(e))
        except Exception:
            pass


def main():
    session_id = _get_session_id()

    # Start command monitor
    start_command_monitor()

    # If Hub already running for this session, just focus and exit
    hub_session_path = _get_hub_session_path(session_id)
    if hub_session_path and os.path.exists(hub_session_path):
        is_hub_running()
        return

    hub_exe = find_hub_exe()
    if hub_exe:
        try:
            subprocess.Popen([hub_exe, "--session={0}".format(session_id)], close_fds=True)
        except Exception:
            try:
                os.startfile(hub_exe)
            except Exception:
                pass
    else:
        # Fallback: show message that Hub not found
        try:
            from pyrevit import forms
            forms.alert(
                u"EOMHub.exe не найден.\n\n"
                u"Соберите Hub командой:\n"
                u"cd C:\\Users\\anton\\EOMTemplateTools\\EOMHub\n"
                u".\\build.ps1"
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
