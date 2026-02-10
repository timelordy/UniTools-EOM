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

    env_override = os.environ.get("EOM_HUB_EXE_PATH")
    if env_override and os.path.exists(env_override):
        return env_override

    canonical = os.path.join(extension_dir, "bin", "EOMHub.exe")
    if os.path.exists(canonical):
        return canonical

    appdata_fallback = os.path.join(
        os.environ.get("APPDATA", ""),
        "pyRevit",
        "Extensions",
        "EOMTemplateTools.extension",
        "bin",
        "EOMHub.exe",
    )
    if os.path.exists(appdata_fallback):
        return appdata_fallback

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
     
    try:
        global _EOM_MONITOR_STARTED, _EOM_HUB_EVENT, _EOM_HUB_HANDLER
        # Add lib to path
        script_dir = _os.path.dirname(__file__)
        extension_dir = _os.path.dirname(_os.path.dirname(_os.path.dirname(script_dir)))
        lib_dir = _os.path.join(extension_dir, "lib")
        if lib_dir not in sys.path:
            sys.path.insert(0, lib_dir)

        from Autodesk.Revit.UI import IExternalEventHandler, ExternalEvent
        import tempfile

        TEMP_DIR = tempfile.gettempdir()
        DEBUG_LOG = _os.path.join(TEMP_DIR, "eom_debug.log")

        def debug_log(msg):
            try:
                with io.open(DEBUG_LOG, 'a', encoding='utf-8') as f:
                    f.write(u"{0}: {1}\n".format(_time.time(), msg))
            except:
                pass

        if _EOM_MONITOR_STARTED:
            debug_log("Monitor already running; skip new start")
            return
        _EOM_MONITOR_STARTED = True

        session_id = _get_session_id()
        # Use fixed filenames for simpler communication with Hub
        COMMAND_FILE = _os.path.join(TEMP_DIR, "eom_hub_command.txt")
        STATUS_FILE = _os.path.join(TEMP_DIR, "eom_hub_status.json")
        RESULT_FILE = _os.path.join(TEMP_DIR, "eom_hub_result.json")
        debug_log("Monitor init")
        debug_log("TEMP_DIR=" + TEMP_DIR)
        debug_log("SESSION_ID=" + str(session_id))
        debug_log("COMMAND_FILE=" + COMMAND_FILE)
        debug_log("STATUS_FILE=" + STATUS_FILE)
        debug_log("RESULT_FILE=" + RESULT_FILE)

        def write_result_json(payload):
            """Write result JSON atomically when possible."""
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

        # Save references before globals cleanup
        script_path_self = __file__
        uiapp_ref = None
        try:
            uiapp_ref = __revit__  # noqa: F821
        except Exception:
            uiapp_ref = None
        
        # Tool ID -> script path mapping
        # Dynamic scanning of EOM.tab
        TOOL_SCRIPTS = {}
        
        try:
            # Find extension root
            script_dir = _os.path.dirname(__file__)
            # script_dir = .../EOMTemplateTools.extension/EOM.tab/01_Хаб.panel/Hub.pushbutton
            tab_dir = _os.path.dirname(_os.path.dirname(script_dir))
            
            if _os.path.exists(tab_dir):
                for panel_name in _os.listdir(tab_dir):
                    if not panel_name.endswith(".panel"):
                        continue
                    panel_path = _os.path.join(tab_dir, panel_name)
                    
                    for tool_name in _os.listdir(panel_path):
                        if not tool_name.endswith(".pushbutton"):
                            continue
                        
                        # Skip Hub itself to prevent recursion loop if called
                        if "Hub" in tool_name:
                            continue
                            
                        tool_path = _os.path.join(panel_path, tool_name)
                        script_file = _os.path.join(tool_path, "script.py")
                        
                        if _os.path.exists(script_file):
                            # ID is the folder name without extension
                            t_id = tool_name.replace(".pushbutton", "")
                            TOOL_SCRIPTS[t_id] = script_file
                            
                            # Also support legacy IDs if needed or specific mappings
                            # For example, if we want "lights_center" to map to "СветПоЦентру"
                            # We can keep the hardcoded list below as fallback/alias
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
            "kitchen_block": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"02_КухняБлок.pushbutton", "script.py"),
            "ac_sockets": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"04_Кондиционеры.pushbutton", "script.py"),
            "wet_zones": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"05_ВлажныеЗоны.pushbutton", "script.py"),
            "low_voltage": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"06_Слаботочка.pushbutton", "script.py"),
            "shdup": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"07_ШДУП.pushbutton", "script.py"),
            "storage_rooms": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"08_Кладовые.pushbutton", "script.py"),
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
        last_cmd = [""]
        pending_jobs = []
        needs_raise = [False]
        pending_lock = _threading.Lock()

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

        def process_tool(uiapp, doc, tool_id=None, job_id=None):
            """Execute tool script and capture output."""
            tool_id = tool_id or "unknown"
            job_id = job_id or "job_{0}_{1}".format(tool_id, int(_time.time()))
            script_path = TOOL_SCRIPTS.get(tool_id)
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
                    return

                # Write "running" marker
                try:
                    running_marker = {
                        "job_id": job_id,
                        "tool_id": tool_id,
                        "status": "running",
                        "message": u"Выполняется в Revit...",
                        "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 0},
                    }
                    write_result_json(running_marker)
                except:
                    pass

                # Capture stdout/stderr
                import sys
                import io

                old_stdout = sys.stdout
                old_stderr = sys.stderr
                captured_stdout = io.StringIO()
                captured_stderr = io.StringIO()
                
                sys.stdout = captured_stdout
                sys.stderr = captured_stderr
                
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
                
                write_result_json(result)
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
                        else:
                            tool_id = job[0] if job and len(job) > 0 else None
                            job_id = job[1] if job and len(job) > 1 else None

                        process_tool(uiapp, doc, tool_id=tool_id, job_id=job_id)
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
                     
                    # Monitor commands from Hub
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
                                    })
                                debug_log("Job queued: tool_id={0} job_id={1}".format(tool_id, job_id))
                                
                                # Clear command file
                                with io.open(COMMAND_FILE, 'w', encoding='utf-8') as f:
                                    f.write(u"")
                                
                                try:
                                    event.Raise()
                                    needs_raise[0] = False
                                    debug_log("Event raised!")
                                except Exception:
                                    needs_raise[0] = True
                                    debug_log("Event raise failed, will retry")

                    if needs_raise[0]:
                        with pending_lock:
                            has_pending = bool(pending_jobs)
                        if has_pending:
                            try:
                                event.Raise()
                                needs_raise[0] = False
                                debug_log("Event raised (retry)")
                            except Exception:
                                pass
                except Exception as e:
                    debug_log("ERROR in monitor: " + str(e))
                try:
                    _time.sleep(0.5)
                except Exception:
                    pass

        thread = _threading.Thread(target=monitor)
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

