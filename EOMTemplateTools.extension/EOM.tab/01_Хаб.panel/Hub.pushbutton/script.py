# -*- coding: utf-8 -*-
"""UniTools Hub - Web interface launcher with file-based communication."""

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
import socket

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

HUB_DOCKABLE_PANE_ID = "59F3CD26-2CA0-4D4B-91F3-71B3FBDA2E57"
HUB_WINDOW_TITLES = (
    u"UniTools Hub",
    u"UniTools EOM",
    u"EOM Hub",
)

_EOM_DEBUG_LOG_PATH = None
_LAST_DOCKABLE_ERROR = None
_DOCKABLE_ALERT_SHOWN = False
_MERGE_SUMMARY_FALLBACK_WARNED = False


def _resolve_debug_log_path():
    global _EOM_DEBUG_LOG_PATH
    if _EOM_DEBUG_LOG_PATH:
        return _EOM_DEBUG_LOG_PATH
    try:
        base = os.environ.get("USERPROFILE") or os.environ.get("TEMP") or tempfile.gettempdir()
    except Exception:
        base = tempfile.gettempdir()
    path = os.path.join(base, "eom_debug.log")
    _EOM_DEBUG_LOG_PATH = path
    return path


def _log_debug(msg):
    """Write debug messages early in the lifecycle (before monitor starts)."""
    try:
        import io as _io
        from time import strftime

        path = _resolve_debug_log_path()
        text = _to_unicode(msg)
        line = u"[{0}] {1}\n".format(strftime("%Y-%m-%d %H:%M:%S"), text)
        with _io.open(path, "a", encoding="utf-8") as f:
            f.write(line)
            try:
                f.flush()
            except Exception:
                pass
    except Exception:
        pass


_log_debug(u"Hub launcher script loaded from: {0}".format(_to_unicode(__file__)))


def _get_revit_version():
    """Return Revit version number as text, or None."""
    try:
        uiapp = __revit__
        if not uiapp:
            return None
        app = getattr(uiapp, "Application", None)
        if not app:
            return None
        version = getattr(app, "VersionNumber", None)
        if version:
            return _to_unicode(version)
    except Exception:
        return None
    return None


def _get_expected_addin_dir():
    version = _get_revit_version()
    if not version:
        return None
    try:
        base = os.environ.get("APPDATA") or ""
        if not base:
            return None
        return os.path.join(base, "Autodesk", "Revit", "Addins", version, "EOMHubDockablePane")
    except Exception:
        return None


def _prompt_missing_dockable_pane():
    """Show a one-time alert explaining how to install the dockable pane add-in."""
    global _DOCKABLE_ALERT_SHOWN
    if _DOCKABLE_ALERT_SHOWN:
        return
    _DOCKABLE_ALERT_SHOWN = True

    version = _get_revit_version()
    addin_dir = _get_expected_addin_dir()
    missing_parts = []
    if addin_dir:
        try:
            dll_path = os.path.join(addin_dir, "EOMHub.DockablePane.dll")
            addin_path = os.path.join(addin_dir, "EOMHub.DockablePane.addin")
            if not os.path.exists(dll_path):
                missing_parts.append(u"DLL")
            if not os.path.exists(addin_path):
                missing_parts.append(u".addin")
        except Exception:
            pass

    lines = [
        u"Не удалось показать док-панель UniTools Hub внутри Revit.",
        u"Убедитесь, что аддин EOMHubDockablePane установлен для текущей версии Revit и затем перезапустите Revit.",
    ]
    if addin_dir:
        lines.append(u"Ожидаемая папка: {0}".format(_to_unicode(addin_dir)))
        if missing_parts:
            lines.append(u"Отсутствуют файлы: {0}".format(", ".join(missing_parts)))
    build_hint_version = version or u"2022"
    lines.append(
        u"Сборка: dotnet build EOMHub/RevitDockablePane -c Release -p:REVIT_API_PATH=\"C:\\Program Files\\Autodesk\\Revit {0}\"".format(
            build_hint_version
        )
    )
    lines.append(u"После сборки скопируйте DLL и .addin в указанную папку.")
    if _LAST_DOCKABLE_ERROR:
        lines.append(u"Техническая ошибка: {0}".format(_to_unicode(_LAST_DOCKABLE_ERROR)))

    message = u"\n\n".join(lines)
    _log_debug(message)
    try:
        from pyrevit import forms

        forms.alert(message, title=u"UniTools Hub", warn_icon=True)
    except Exception:
        pass


def _show_dockable_pane():
    """Try to show the WebView2 dockable pane if the add-in is installed."""
    global _LAST_DOCKABLE_ERROR
    try:
        from Autodesk.Revit.UI import DockablePaneId
        from System import Guid

        uiapp = __revit__  # pyRevit injects UIApplication
        if not uiapp:
            _LAST_DOCKABLE_ERROR = RuntimeError("UIApplication reference is missing")
            return False
        pane_id = DockablePaneId(Guid(HUB_DOCKABLE_PANE_ID))
        pane = uiapp.GetDockablePane(pane_id)
        if pane:
            pane.Show()
            _LAST_DOCKABLE_ERROR = None
            return True
    except Exception as e:
        _LAST_DOCKABLE_ERROR = e
        _log_debug(u"DockablePane show failed: {0}".format(_to_unicode(e)))
    return False


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


def _build_time_savings_summary(tool_id):
    """Return dict with normalized time-saving info for the tool, or None."""
    avg_minutes, min_minutes, max_minutes = _get_time_savings_for_tool(tool_id)

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

    if avg_minutes is None and min_minutes is None and max_minutes is None:
        return None

    summary = {}
    if avg_minutes is not None:
        summary["time_saved_minutes"] = avg_minutes
    if min_minutes is not None:
        summary["time_saved_minutes_min"] = min_minutes
    if max_minutes is not None:
        summary["time_saved_minutes_max"] = max_minutes
    return summary


def _merge_summary_dicts(*summaries):
    """Return a shallow copy that merges multiple summary dicts."""
    merged = {}
    for summary in summaries:
        if isinstance(summary, dict):
            try:
                for key, value in summary.items():
                    merged[key] = value
            except Exception:
                continue
    return merged


def _fallback_merge_summary_dicts(*summaries):
    """Fallback merger used when IronPython loses reference to _merge_summary_dicts."""
    merged = {}
    for summary in summaries:
        if isinstance(summary, dict):
            try:
                for key, value in summary.items():
                    merged[key] = value
            except Exception:
                continue

    warned = False
    try:
        warned = bool(globals().get("_MERGE_SUMMARY_FALLBACK_WARNED", False))
    except Exception:
        warned = False

    if not warned:
        try:
            globals()["_MERGE_SUMMARY_FALLBACK_WARNED"] = True
        except Exception:
            pass
        try:
            log_fn = globals().get("_log_debug")
            if callable(log_fn):
                log_fn(u"WARNING: _merge_summary_dicts missing; using fallback merger.")
        except Exception:
            pass
    return merged


def _merge_summary_dicts_safe(*summaries):
    """Call _merge_summary_dicts if available, otherwise fallback."""
    merge_func = globals().get("_merge_summary_dicts")
    if callable(merge_func):
        try:
            return merge_func(*summaries)
        except Exception as merge_err:
            try:
                log_fn = globals().get("_log_debug")
                if callable(log_fn):
                    log_fn(u"merge_summary_dicts error: {0}".format(_to_unicode(merge_err)))
            except Exception:
                pass
    return _fallback_merge_summary_dicts(*summaries)


def _resolve_merge_summary_func():
    """Return best-available summary merge callable to avoid NameError."""
    merge_fn = globals().get("_merge_summary_dicts_safe")
    if callable(merge_fn):
        return merge_fn
    merge_fn = globals().get("_merge_summary_dicts")
    if callable(merge_fn):
        return merge_fn
    try:
        log_fn = globals().get("_log_debug")
        if callable(log_fn):
            log_fn(u"WARNING: merge summary helpers missing; using fallback merger.")
    except Exception:
        pass
    return _fallback_merge_summary_dicts


def _get_merge_summary_callable():
    """Resolve merge helper without raising if resolver symbol is missing."""
    resolver = globals().get("_resolve_merge_summary_func")
    if callable(resolver):
        try:
            merge_fn = resolver()
            if callable(merge_fn):
                return merge_fn
        except Exception as resolver_err:
            try:
                log_fn = globals().get("_log_debug")
                if callable(log_fn):
                    log_fn(u"WARNING: merge summary resolver failed: {0}".format(_to_unicode(resolver_err)))
            except Exception:
                pass

    for fallback_name in ("_merge_summary_dicts_safe", "_merge_summary_dicts"):
        fallback = globals().get(fallback_name)
        if callable(fallback):
            return fallback

    try:
        log_fn = globals().get("_log_debug")
        if callable(log_fn):
            log_fn(u"WARNING: merge summary helpers missing entirely; using fallback merger.")
    except Exception:
        pass
    return _fallback_merge_summary_dicts


def _get_session_id():
    global SESSION_ID
    if SESSION_ID:
        return SESSION_ID
    session_id = os.environ.get("EOM_SESSION_ID")
    if not session_id:
        try:
            temp_dir = os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
            status_files = [
                os.path.join(temp_dir, "eom_hub_status.json"),
            ]
            root_temp = _get_root_temp_dir(temp_dir)
            if root_temp and root_temp != temp_dir:
                status_files.append(os.path.join(root_temp, "eom_hub_status.json"))

            for status_file in status_files:
                if not os.path.exists(status_file):
                    continue
                try:
                    with io.open(status_file, "r", encoding="utf-8") as f:
                        status_data = json.load(f)
                    status_session = status_data.get("sessionId")
                    if status_session:
                        session_id = _to_unicode(status_session)
                        break
                except Exception:
                    continue
        except Exception:
            pass
    if not session_id:
        session_id = str(uuid.uuid4())
        os.environ["EOM_SESSION_ID"] = session_id
    else:
        try:
            os.environ["EOM_SESSION_ID"] = _to_unicode(session_id)
        except Exception:
            pass
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


def _normalize_fs_path(path):
    """Normalize path for stable comparisons across Win/Py2/Py3."""
    if not path:
        return None
    try:
        p = _to_unicode(path)
    except Exception:
        try:
            p = unicode(path)
        except Exception:
            p = str(path)
    try:
        return os.path.normcase(os.path.abspath(p))
    except Exception:
        return None


def _is_hub_session_alive(hub_session_path, expected_exe=None):
    """Return True only for reachable sessions bound to canonical headless EOMHub.exe."""
    if not hub_session_path or not os.path.exists(hub_session_path):
        return False

    expected_norm = _normalize_fs_path(expected_exe) if expected_exe else None

    try:
        with io.open(hub_session_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        # Validate session-file exe binding early.
        if expected_norm:
            actual_norm = _normalize_fs_path(payload.get("exePath"))
            if actual_norm and actual_norm != expected_norm:
                _log_debug(
                    u"Session exe mismatch: expected={0} actual={1}".format(
                        _to_unicode(expected_norm),
                        _to_unicode(actual_norm),
                    )
                )
                return False

        port = payload.get("hubPort")
        if not port:
            return False
        try:
            port = int(port)
        except Exception:
            return False
        if port <= 0:
            return False

        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.settimeout(0.25)
        try:
            is_reachable = probe.connect_ex(("127.0.0.1", port)) == 0
        finally:
            try:
                probe.close()
            except Exception:
                pass

        if not is_reachable:
            return False

        # Require process identity + command line check to avoid reusing non-headless UI process.
        pid_raw = payload.get("pid")
        try:
            session_pid = int(pid_raw)
        except Exception:
            _log_debug(u"Session file has no valid pid; forcing headless relaunch")
            return False

        import subprocess as _sub

        ps_cmd = (
            "Get-CimInstance Win32_Process -Filter \"Name='EOMHub.exe'\" -ErrorAction SilentlyContinue | "
            "Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"
        )
        try:
            out = _sub.check_output(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                stderr=_sub.STDOUT,
            )
        except Exception as proc_err:
            _log_debug(u"Failed to inspect EOMHub.exe process list: {0}".format(_to_unicode(proc_err)))
            return False

        if not out:
            return False

        try:
            proc_payload = json.loads(out.decode("utf-8", "ignore"))
        except Exception:
            try:
                proc_payload = json.loads(_to_unicode(out))
            except Exception:
                return False

        rows = proc_payload if isinstance(proc_payload, list) else ([proc_payload] if proc_payload else [])
        proc_row = None
        for row in rows:
            try:
                if int(row.get("ProcessId") or row.get("Id") or -1) == session_pid:
                    proc_row = row
                    break
            except Exception:
                continue

        if not proc_row:
            _log_debug(u"Session pid not found among running EOMHub.exe processes: {0}".format(_to_unicode(session_pid)))
            return False

        proc_exe_norm = _normalize_fs_path(proc_row.get("ExecutablePath") or proc_row.get("Path"))
        if expected_norm and proc_exe_norm and proc_exe_norm != expected_norm:
            _log_debug(
                u"Session pid exe mismatch: pid={0} expected={1} actual={2}".format(
                    _to_unicode(session_pid),
                    _to_unicode(expected_norm),
                    _to_unicode(proc_exe_norm),
                )
            )
            return False

        proc_cmdline = _to_unicode(proc_row.get("CommandLine") or "")
        if u"--headless" not in proc_cmdline.lower():
            _log_debug(u"Session pid is non-headless; terminating pid={0}".format(_to_unicode(session_pid)))
            try:
                _sub.call(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-Command",
                        "Stop-Process -Force -Id {0} -ErrorAction SilentlyContinue".format(session_pid),
                    ]
                )
            except Exception:
                pass
            return False

        return True
    except Exception:
        return False


def _kill_duplicate_hub_processes(expected_exe):
    """Best-effort cleanup: kill extra EOMHub.exe instances.

    We observed cases where multiple EOMHub.exe were started for one Revit session,
    producing stale session files / UI disconnect.
    """
    if not expected_exe:
        return
    try:
        expected_norm = _normalize_fs_path(expected_exe)
        if not expected_norm:
            return
    except Exception:
        return

    try:
        import subprocess as _sub
        out = _sub.check_output(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-Process EOMHub -ErrorAction SilentlyContinue | Select-Object Id,Path | ConvertTo-Json -Compress",
            ],
            stderr=_sub.STDOUT,
        )
        if not out:
            return
        try:
            payload = json.loads(out.decode("utf-8", "ignore"))
        except Exception:
            return

        procs = payload if isinstance(payload, list) else ([payload] if payload else [])
        matching = []
        for p in procs:
            try:
                if _normalize_fs_path(p.get("Path")) == expected_norm:
                    matching.append(int(p.get("Id")))
            except Exception:
                continue

        if len(matching) <= 1:
            return

        # Keep the most recent PID (heuristic: max pid), kill the rest.
        keep_pid = max(matching)
        kill_pids = [pid for pid in matching if pid != keep_pid]
        if not kill_pids:
            return

        _log_debug(u"Killing duplicate EOMHub.exe processes: {0}".format(
            u", ".join([_to_unicode(x) for x in kill_pids])
        ))
        cmd = "Stop-Process -Force -Id " + ",".join([str(x) for x in kill_pids])
        _sub.call(["powershell.exe", "-NoProfile", "-Command", cmd])
    except Exception:
        return


def find_hub_exe():
    """Find canonical EOMHub.exe path (single source of truth)."""
    script_dir = _to_unicode(os.path.dirname(__file__))
    # script_dir = .../EOMTemplateTools.extension/EOM.tab/01_Хаб.panel/Hub.pushbutton
    extension_dir = _to_unicode(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))

    env_override = os.environ.get("EOM_HUB_EXE_PATH")
    if env_override and os.path.exists(env_override):
        return env_override

    canonical = os.path.join(extension_dir, "bin", "EOMHub.exe")
    if os.path.exists(canonical):
        return canonical

    return None


def _find_hub_window():
    """Return handle to any known Hub window title."""
    try:
        user32 = ctypes.windll.user32
    except Exception:
        return None

    for title in HUB_WINDOW_TITLES:
        try:
            hwnd = user32.FindWindowW(None, title)
        except Exception:
            hwnd = None
        if hwnd and hwnd != 0:
            return hwnd
    return None


def _hide_hub_window():
    """Hide standalone Hub window if it appears; WPF dockable pane remains active."""
    try:
        user32 = ctypes.windll.user32
        hwnd = _find_hub_window()
        if hwnd and hwnd != 0:
            user32.ShowWindow(hwnd, 0)  # SW_HIDE
            return True
    except Exception:
        pass
    return False


def _schedule_hub_window_hide(duration_sec=4.0, poll_interval_sec=0.2):
    """Hide standalone Hub window for a short period to catch late window creation."""

    def _worker():
        try:
            end_ts = time.time() + max(float(duration_sec), 0.2)
        except Exception:
            end_ts = time.time() + 4.0

        while time.time() <= end_ts:
            try:
                _hide_hub_window()
            except Exception:
                pass
            try:
                time.sleep(max(float(poll_interval_sec), 0.05))
            except Exception:
                break

    try:
        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()
    except Exception:
        _hide_hub_window()


def is_hub_running():
    """Check if Hub is running and activate window."""
    try:
        user32 = ctypes.windll.user32
        hwnd = _find_hub_window()
        if hwnd and hwnd != 0:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
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
        get_merge_summary_callable = _get_merge_summary_callable
        fallback_merge_summary_dicts = _fallback_merge_summary_dicts
        build_time_savings_summary = _build_time_savings_summary
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

        def read_latest_time_savings_summary(tool_key):
            """Read latest time-savings entry for tool from jsonl logs in TEMP_DIR."""
            if not tool_key:
                return None

            candidates = []
            try:
                candidates.append(_os.path.join(TEMP_DIR, u"eom_time_savings_log.jsonl"))
            except Exception:
                pass
            try:
                if ROOT_TEMP_DIR and ROOT_TEMP_DIR != TEMP_DIR:
                    candidates.append(_os.path.join(ROOT_TEMP_DIR, u"eom_time_savings_log.jsonl"))
            except Exception:
                pass

            last_entry = None
            for path in candidates:
                try:
                    if not path or not _os.path.exists(path):
                        continue
                    with io.open(path, 'r', encoding='utf-8') as f:
                        for raw in f:
                            line = raw.strip()
                            if not line:
                                continue
                            try:
                                entry = _json.loads(line)
                            except Exception:
                                continue
                            if not isinstance(entry, dict):
                                continue
                            try:
                                entry_tool = entry.get('tool_key')
                            except Exception:
                                entry_tool = None
                            if entry_tool == tool_key:
                                last_entry = entry
                except Exception:
                    continue

            if not isinstance(last_entry, dict):
                return None

            summary = {}
            try:
                avg = last_entry.get('minutes')
                mn = last_entry.get('minutes_min')
                mx = last_entry.get('minutes_max')
                cnt = last_entry.get('count')
                if isinstance(avg, (int, float)):
                    summary['time_saved_minutes'] = float(avg)
                if isinstance(mn, (int, float)):
                    summary['time_saved_minutes_min'] = float(mn)
                if isinstance(mx, (int, float)):
                    summary['time_saved_minutes_max'] = float(mx)
                if isinstance(cnt, (int, float)):
                    summary['placed'] = int(cnt)
            except Exception:
                return None

            return summary if summary else None

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
                        if u"Hub" in base or u"Хаб" in base:
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
            "floor_panel_niches": _os.path.join(extension_dir, u"EOM.tab", u"03_ЩитыВыключатели.panel", u"ЩЭВНишах.pushbutton", u"script.py"),
            "entrance_numbering": _os.path.join(extension_dir, u"Разработка.tab", u"03_ЩитыВыключатели_Dev.panel", u"НумерацияПодъезда.pushbutton", u"script.py"),
            "sockets_general": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"01_Общие.pushbutton", u"script.py"),
            "kitchen_block": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"02_КухняБлок.pushbutton", u"script.py"),
            "kitchen_general": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"02_КухняБлок.pushbutton", u"script.py"),
            "ac_sockets": _os.path.join(extension_dir, u"Разработка.tab", u"04_Розетки.panel", u"04_Кондиционеры.pushbutton", u"script.py"),
            "wet_zones": _os.path.join(extension_dir, u"EOM.tab", u"04_Розетки.panel", u"05_МокрыеТочки.pushbutton", u"script.py"),
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
        active_job = {
            "job_id": None,
            "tool_id": None,
            "started_at": 0.0,
            "cancel_requested_at": 0.0,
        }
        active_job_lock = _threading.Lock()
        cancelled_job_ids = {}
        cancelled_job_ids_lock = _threading.Lock()

        def _build_cancelled_result(job_id, tool_id, message=None):
            payload = {
                "job_id": job_id,
                "tool_id": tool_id or "unknown",
                "status": "cancelled",
                "executionTime": 0,
                "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 0},
                "details": [],
                "timestamp": _time.time(),
            }
            if message:
                payload["message"] = message
            return payload

        def _clear_active_job(job_id):
            try:
                with active_job_lock:
                    if str(active_job.get("job_id") or "") == str(job_id):
                        active_job["job_id"] = None
                        active_job["tool_id"] = None
                        active_job["started_at"] = 0.0
                        active_job["cancel_requested_at"] = 0.0
            except Exception:
                pass

        def _is_job_cancelled(job_id):
            if not job_id:
                return False
            try:
                with cancelled_job_ids_lock:
                    return str(job_id) in cancelled_job_ids
            except Exception:
                return False

        def _mark_job_cancelled(job_id, ts):
            if not job_id:
                return
            try:
                with cancelled_job_ids_lock:
                    cancelled_job_ids[str(job_id)] = float(ts or 0)
            except Exception:
                pass

        def _unmark_job_cancelled(job_id):
            if not job_id:
                return
            try:
                with cancelled_job_ids_lock:
                    cancelled_job_ids.pop(str(job_id), None)
            except Exception:
                pass

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

            if cmd == "cancel":
                action = "cancel"
            elif cmd.startswith("run:cancel"):
                action = "cancel"
                parts = cmd.split(":")
                if len(parts) >= 3 and parts[2]:
                    job_id = parts[2]
                if len(parts) >= 4 and parts[3]:
                    mode = parts[3]
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
                    cancel_job_id = data.get("job_id")
                    cancel_ts = _time.time()
                    cancelled_pending = []

                    if cancel_job_id:
                        _mark_job_cancelled(cancel_job_id, cancel_ts)
                    with pending_lock:
                        if cancel_job_id:
                            keep = []
                            for job in pending_jobs:
                                if str(job.get("job_id") or "") == str(cancel_job_id):
                                    cancelled_pending.append(job)
                                else:
                                    keep.append(job)
                            pending_jobs[:] = keep
                        else:
                            cancelled_pending = list(pending_jobs)
                            pending_jobs[:] = []
                            last_cancel_time[0] = cancel_ts

                    for pending_job in cancelled_pending:
                        try:
                            cancelled_payload = _build_cancelled_result(
                                pending_job.get("job_id"),
                                pending_job.get("tool_id"),
                                u"Задача отменена до запуска",
                            )
                            write_result_json(cancelled_payload)
                            write_job_result_json(pending_job.get("job_id"), cancelled_payload)
                        except Exception:
                            pass

                    active_job_id = None
                    active_tool_id = None
                    with active_job_lock:
                        current_job_id = active_job.get("job_id")
                        if current_job_id and (not cancel_job_id or str(current_job_id) == str(cancel_job_id)):
                            active_job["cancel_requested_at"] = cancel_ts
                            active_job_id = current_job_id
                            active_tool_id = active_job.get("tool_id")

                    if active_job_id:
                        try:
                            cancel_marker = {
                                "job_id": active_job_id,
                                "tool_id": active_tool_id or "unknown",
                                "status": "running",
                                "message": u"Отмена запрошена. Ожидание остановки...",
                                "cancelRequested": True,
                                "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 0},
                                "timestamp": cancel_ts,
                            }
                            write_result_json(cancel_marker)
                            write_job_result_json(active_job_id, cancel_marker)
                        except Exception:
                            pass

                    debug_log(
                        u"Cancellation requested job_id={0} pending_cancelled={1} active={2}".format(
                            _to_unicode(cancel_job_id),
                            len(cancelled_pending),
                            bool(active_job_id),
                        )
                    )
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

        _status_cache = {
            "connected": False,
            "document": None,
            "documentPath": None,
            "revitVersion": None,
        }

        def write_status():
            """Write status file for Hub.

            Note: monitor loop runs in a background thread where direct Revit API
            access can intermittently fail. We keep last known UI state in cache
            and always refresh timestamp so Hub status doesn't become stale.
            """
            try:
                uiapp = uiapp_ref
                uidoc = uiapp.ActiveUIDocument if uiapp else None
                doc = uidoc.Document if uidoc else None

                _status_cache["connected"] = doc is not None
                _status_cache["document"] = getattr(doc, "Title", None) if doc else None
                _status_cache["documentPath"] = getattr(doc, "PathName", None) if doc else None
                _status_cache["revitVersion"] = getattr(uiapp.Application, "VersionNumber", None) if uiapp else None
            except Exception:
                pass

            try:
                status = {
                    "connected": bool(_status_cache.get("connected", False)),
                    "document": _status_cache.get("document"),
                    "documentPath": _status_cache.get("documentPath"),
                    "revitVersion": _status_cache.get("revitVersion"),
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
                pass

        try:
            string_types = (basestring,)
        except Exception:
            string_types = (str,)

        def emit_result_to_output(doc, tool_id, job_id, result):
            """Print Hub job result into pyRevit output window."""
            try:
                if not isinstance(result, dict):
                    return

                status = _to_unicode(result.get("status") or "unknown")
                execution_time = result.get("executionTime")
                stats = result.get("stats") if isinstance(result.get("stats"), dict) else None
                summary = result.get("summary") if isinstance(result.get("summary"), dict) else None
                details = result.get("details") if isinstance(result.get("details"), list) else []
                message = result.get("error") or result.get("message")

                print(u"\n" + (u"=" * 72))
                print(u"UniTools Hub — результат запуска")

                try:
                    doc_title = _to_unicode(getattr(doc, "Title", None) or u"(без документа)")
                except Exception:
                    doc_title = u"(без документа)"

                print(u"Документ: {0}".format(doc_title))
                print(u"Инструмент: {0}".format(_to_unicode(tool_id or "unknown")))
                print(u"Задача: {0}".format(_to_unicode(job_id or "")))
                print(u"Статус: {0}".format(status))

                if isinstance(execution_time, (int, float)):
                    print(u"Время: {0} сек".format(round(float(execution_time), 2)))

                if stats:
                    print(
                        u"Статистика: всего={0}, успешно={1}, пропущено={2}, ошибки={3}".format(
                            stats.get("total", 0),
                            stats.get("processed", 0),
                            stats.get("skipped", 0),
                            stats.get("errors", 0),
                        )
                    )

                if isinstance(message, string_types) and _to_unicode(message).strip():
                    print(u"Сообщение: {0}".format(_to_unicode(message).strip()))

                if summary:
                    print(u"Сводка:")
                    try:
                        print(_to_unicode(_json.dumps(summary, ensure_ascii=False, indent=2)))
                    except Exception:
                        print(_to_unicode(summary))

                if details:
                    print(u"Логи:")
                    for idx, item in enumerate(details[:40]):
                        try:
                            status_value = _to_unicode(item.get("status") or "info") if isinstance(item, dict) else u"info"
                            msg_value = _to_unicode(item.get("message") or "") if isinstance(item, dict) else _to_unicode(item)
                            print(u"  [{0}] {1}".format(status_value, msg_value))
                        except Exception:
                            continue
                    if len(details) > 40:
                        print(u"  ... еще строк: {0}".format(len(details) - 40))

                print(u"=" * 72)
            except Exception as output_err:
                try:
                    debug_log(u"emit_result_to_output failed: " + _to_unicode(output_err))
                except Exception:
                    pass

        def process_tool(uiapp, doc, tool_id=None, job_id=None, enqueue_time=None):
            """Execute tool script and capture output."""
            tool_id = tool_id or "unknown"
            job_id = job_id or "job_{0}_{1}".format(tool_id, int(_time.time()))
            enqueue_time = enqueue_time or _time.time()
            script_path = TOOL_SCRIPTS.get(tool_id)

            try:
                with active_job_lock:
                    active_job["job_id"] = job_id
                    active_job["tool_id"] = tool_id
                    active_job["started_at"] = _time.time()
                    active_job["cancel_requested_at"] = 0.0
            except Exception:
                pass

            merge_summary = fallback_merge_summary_dicts
            try:
                maybe_merge = get_merge_summary_callable()
                if callable(maybe_merge):
                    merge_summary = maybe_merge
            except Exception as merge_resolve_err:
                try:
                    debug_log(u"merge summary resolver failed: " + _to_unicode(merge_resolve_err))
                except Exception:
                    pass
            
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
                    emit_result_to_output(doc, tool_id, job_id, result)
                    _clear_active_job(job_id)
                    return

                # Check cancellation before execution.
                if enqueue_time < last_cancel_time[0] or _is_job_cancelled(job_id):
                    result = _build_cancelled_result(job_id, tool_id, u"Задача отменена до запуска")
                    write_result_json(result)
                    write_job_result_json(job_id, result)
                    emit_result_to_output(doc, tool_id, job_id, result)
                    _unmark_job_cancelled(job_id)
                    _clear_active_job(job_id)
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

                time_savings_summary = read_latest_time_savings_summary(tool_id)
                if time_savings_summary is None:
                    try:
                        if callable(build_time_savings_summary):
                            time_savings_summary = build_time_savings_summary(tool_id)
                    except Exception as ts_err:
                        try:
                            debug_log(u"time savings summary failed: " + _to_unicode(ts_err))
                        except Exception:
                            pass

                hub_summary = merge_summary(time_savings_summary)
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
                        hub_summary = merge_summary(
                            hub_summary,
                            {
                                "runner": "pyrevit_command",
                                "command": _to_unicode(pyrevit_info),
                            },
                        )

                        # pyRevit command executes in a separate command context,
                        # so EOM_HUB_RESULT is not available via script_globals.
                        # Pull latest persisted time-saving metrics after command run.
                        try:
                            latest_summary = read_latest_time_savings_summary(tool_id)
                            if latest_summary is None and callable(build_time_savings_summary):
                                latest_summary = build_time_savings_summary(tool_id)
                            if isinstance(latest_summary, dict):
                                hub_summary = merge_summary(hub_summary, latest_summary)
                        except Exception as summary_err:
                            try:
                                debug_log(u"post-command time summary failed: " + _to_unicode(summary_err))
                            except Exception:
                                pass
                    else:
                        if not isinstance(hub_summary, dict):
                            hub_summary = {}
                        hub_summary.setdefault("runner", "direct")

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

                        def _is_cancel_requested_for_this_job():
                            try:
                                with active_job_lock:
                                    if str(active_job.get("job_id") or "") != str(job_id):
                                        return False
                                    return bool(active_job.get("cancel_requested_at") or 0) or _is_job_cancelled(job_id)
                            except Exception:
                                return False

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
                            'EOM_IS_CANCELLED': lambda: (last_cancel_time[0] > execution_start) or _is_cancel_requested_for_this_job(),
                        }

                        class _HubCancelException(SystemExit):
                            pass

                        def _cancel_trace(frame, event, arg):
                            if event != 'line':
                                return _cancel_trace
                            if _is_cancel_requested_for_this_job():
                                raise _HubCancelException('Cancelled by user')
                            return _cancel_trace

                        # Read script as UTF-8
                        with io.open(script_path, 'r', encoding='utf-8') as f:
                            script_code = f.read()

                        # EXECUTE
                        old_trace = None
                        try:
                            old_trace = sys.gettrace()
                        except Exception:
                            old_trace = None

                        try:
                            try:
                                sys.settrace(_cancel_trace)
                            except Exception:
                                pass
                            exec(script_code, script_globals)
                        finally:
                            try:
                                sys.settrace(old_trace)
                            except Exception:
                                pass

                        try:
                            maybe_summary = script_globals.get('EOM_HUB_RESULT')
                            if isinstance(maybe_summary, dict):
                                hub_summary = merge_summary(hub_summary, maybe_summary)
                        except Exception:
                            pass

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
                emit_result_to_output(doc, tool_id, job_id, result)
                debug_log(u"process_tool finished status=" + result.get("status", "unknown"))

                _unmark_job_cancelled(job_id)
                _clear_active_job(job_id)

                try:
                    _schedule_hub_window_hide(duration_sec=1.0, poll_interval_sec=0.2)
                except Exception:
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
                emit_result_to_output(doc, tool_id, job_id, result)
                _unmark_job_cancelled(job_id)
                _clear_active_job(job_id)

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
                job = None
                try:
                    debug_log(u"ApplyHandler.Execute called")
                    uidoc = uiapp.ActiveUIDocument if uiapp else None
                    doc = uidoc.Document if uidoc else None
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
                    try:
                        if isinstance(job, dict):
                            failed_job_id = job.get("job_id")
                            failed_tool_id = job.get("tool_id") or "unknown"
                            if failed_job_id:
                                failed_result = {
                                    "job_id": failed_job_id,
                                    "tool_id": failed_tool_id,
                                    "status": "error",
                                    "message": u"Сбой обработки задания в Revit monitor",
                                    "error": _to_unicode(e),
                                    "stats": {"total": 0, "processed": 0, "skipped": 0, "errors": 1},
                                    "timestamp": _time.time(),
                                }
                                write_result_json(failed_result)
                                write_job_result_json(failed_job_id, failed_result)
                    except Exception:
                        pass

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


def _launch_hub_headless(hub_exe, session_id):
    """Launch Hub backend in headless mode without opening a standalone UI window."""
    hub_exe = _to_unicode(hub_exe)
    args = [
        hub_exe,
        u"--session={0}".format(_to_unicode(session_id)),
        u"--headless",
    ]

    try:
        temp_root = tempfile.gettempdir()
    except Exception:
        temp_root = None

    # Keep process environment aligned even if we end up launching without explicit env.
    try:
        if temp_root:
            os.environ["TEMP"] = _to_unicode(temp_root)
            os.environ["TMP"] = _to_unicode(temp_root)
        os.environ["EOM_SESSION_ID"] = _to_unicode(session_id)
        os.environ["EOM_HUB_HEADLESS"] = "1"
    except Exception:
        pass

    try:
        launch_env = os.environ.copy()
        subprocess.Popen(args, env=launch_env)
        _log_debug(u"Hub launched headless (explicit env)")
        return True
    except Exception as first_err:
        _log_debug(u"Hub launch with explicit env failed: {0}".format(_to_unicode(first_err)))

    try:
        subprocess.Popen(args)
        _log_debug(u"Hub launched headless (inherited env)")
        return True
    except Exception as second_err:
        _log_debug(u"Hub launch failed: {0}".format(_to_unicode(second_err)))

    return False


def main():
    session_id = _get_session_id()

    # Do not auto-start on Revit startup. Allow only:
    # 1) explicit runner mode (EOM_HUB_RUN_TOOL_ID)
    # 2) explicit opt-in autostart flag (EOM_HUB_AUTOSTART=1)
    # 3) direct manual execution (this script invoked as __main__)
    run_tool_env = None
    autostart_env = None
    try:
        run_tool_env = os.environ.get("EOM_HUB_RUN_TOOL_ID")
        autostart_env = os.environ.get("EOM_HUB_AUTOSTART")
    except Exception:
        return

    is_manual_click = (__name__ == "__main__")
    autostart_enabled = autostart_env in ("1", "true", "True", "yes", "YES")
    if not run_tool_env and not autostart_enabled and not is_manual_click:
        return

    run_tool_id = run_tool_env
    if run_tool_id:
        run_job_id = os.environ.get("EOM_HUB_RUN_JOB_ID") or u"job_{0}_{1}".format(run_tool_id, int(time.time()))
        _run_job_once(run_tool_id, run_job_id)
        return

    # Start command monitor
    start_command_monitor()

    # Always prefer dockable pane UI.
    pane_shown = _show_dockable_pane()
    if not pane_shown:
        _prompt_missing_dockable_pane()

    hub_exe = find_hub_exe()

    # Avoid multiple EXE instances fighting for the same port/session.
    try:
        _kill_duplicate_hub_processes(hub_exe)
    except Exception:
        pass

    # If Hub already running for this session, do not launch duplicate process.
    hub_session_path = _get_hub_session_path(session_id)
    if _is_hub_session_alive(hub_session_path, expected_exe=hub_exe):
        _log_debug(u"Reusing existing headless Hub session: {0}".format(_to_unicode(hub_session_path)))
        if pane_shown:
            try:
                _schedule_hub_window_hide()
            except Exception:
                pass
        return

    if hub_session_path and os.path.exists(hub_session_path):
        try:
            os.remove(hub_session_path)
        except Exception:
            pass

    if hub_exe:
        _log_debug(u"Launching headless Hub: exe={0} session={1}".format(_to_unicode(hub_exe), _to_unicode(session_id)))
        launched = _launch_hub_headless(hub_exe, session_id)
        if not launched:
            _log_debug(u"Headless launch failed for exe={0} session={1}".format(_to_unicode(hub_exe), _to_unicode(session_id)))
            try:
                from pyrevit import forms
                forms.alert(
                    u"Не удалось запустить UniTools Hub в фоновом режиме.\n"
                    u"Проверьте eom_debug.log и повторите запуск.",
                    title=u"UniTools Hub",
                    warn_icon=True,
                )
            except Exception:
                pass
        elif pane_shown:
            _log_debug(u"Headless Hub launched successfully; scheduling standalone-window hide")
            try:
                _schedule_hub_window_hide(duration_sec=8.0, poll_interval_sec=0.2)
            except Exception:
                pass
    else:
        # Fallback: show message that Hub not found
        try:
            from pyrevit import forms
            forms.alert(
                u"UniTools Hub (EOMHub.exe) не найден.\n\n"
                u"Соберите его командой:\n"
                u"cd C:\\Users\\anton\\EOMTemplateTools\\EOMHub\n"
                u".\\build.ps1",
                title=u"UniTools Hub",
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()





