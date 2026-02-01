# -*- coding: utf-8 -*-
"""EOM Hub API - Tools endpoints для коммуникации с Revit."""
from __future__ import annotations

from typing import Any, Optional

import os
import json
import time
import tempfile
import base64
import uuid
from pathlib import Path
import datetime

try:
    import eel  # type: ignore
except Exception:
    eel = None


def _expose(func):
    """Decorator shim when eel isn't available in lint/CI environments."""
    if eel is None:
        return func
    return eel.expose(func)

# === LOGGING ===
LOG_FILE = os.path.join(os.environ.get("TEMP", tempfile.gettempdir()), "eom_hub_debug.log")

def log(message: str):
    """Write debug message to log file."""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

log("=" * 60)
log("EOM Hub API started")
log(f"Log file: {LOG_FILE}")

def _get_temp_root() -> str:
    return os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()


def _get_session_id() -> str:
    return os.environ.get("EOM_SESSION_ID", "")


def _get_status_file() -> str:
    return os.path.join(_get_temp_root(), "eom_hub_status.json")


def _get_command_file() -> str:
    return os.path.join(_get_temp_root(), "eom_hub_command.txt")


def _get_command_file_for_job(job_id: str) -> str:
    # One command file per job to support queueing.
    # Revit monitor scans TEMP for these files.
    return os.path.join(_get_temp_root(), f"eom_hub_command_{job_id}.txt")


def _get_result_file() -> str:
    return os.path.join(_get_temp_root(), "eom_hub_result.json")


def _get_result_file_for_job(job_id: str) -> str:
    # One result file per job to avoid job_id collisions.
    return os.path.join(_get_temp_root(), f"eom_hub_result_{job_id}.json")


def _get_savings_file() -> str:
    return os.path.join(_get_temp_root(), "eom_time_savings.json")


def _get_tab_path_from_revit_status() -> Optional[Path]:
    status_file = _get_status_file()
    if not os.path.exists(status_file):
        return None
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            status = json.load(f)
    except Exception:
        return None
    script_path = status.get("scriptPath")
    if not isinstance(script_path, str) or not script_path:
        return None
    try:
        p = Path(script_path)
        tab_path = p.parent.parent.parent
        return tab_path if tab_path.exists() else None
    except Exception:
        return None


def _get_pyrevit_tab_path() -> Optional[Path]:
    appdata = os.environ.get("APPDATA") or ""
    if not appdata:
        return None
    p = Path(appdata) / "pyRevit" / "Extensions" / "EOMTemplateTools.extension" / "EOM.tab"
    return p if p.exists() else None


def _get_tab_search_paths() -> list[Path]:
    paths: list[Path] = []

    # If Revit is running, use the actual extension path from its status file.
    status_tab = _get_tab_path_from_revit_status()
    if status_tab is not None:
        paths.append(status_tab)

    # Prefer installed pyRevit extension so Hub runs the same scripts
    # as the pyRevit ribbon buttons.
    pyrevit_tab = _get_pyrevit_tab_path()
    if pyrevit_tab is not None:
        paths.append(pyrevit_tab)

    # Repo checkout (dev) fallback.
    paths.append(Path(__file__).parent.parent.parent.parent / "EOMTemplateTools.extension" / "EOM.tab")

    # Local hardcoded dev path fallback (keep last).
    paths.append(Path(r"C:\\Users\\anton\\EOMTemplateTools\\EOMTemplateTools.extension\\EOM.tab"))

    # De-dup while preserving order.
    unique: list[Path] = []
    seen = set()
    for p in paths:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique


def _get_tools_config() -> dict:
    # Hardcoded config to ensure strict filtering in frozen builds
    config = {
      "tools": {
        "lights_center": {
          "id": "lights_center",
          "name": "Свет по центрам",
          "icon": "💡",
          "description": "Размещение светильников по центрам помещений",
          "category": "lighting",
          "time_saved": 15,
          "script_path": "02_Освещение.panel/СветПоЦентру.pushbutton/script.py"
        },
        "lights_elevator": {
          "id": "lights_elevator",
          "name": "Свет в лифтах",
          "icon": "🛗",
          "description": "Освещение лифтовых холлов",
          "category": "lighting",
          "time_saved": 8,
          "script_path": "02_Освещение.panel/СветВЛифтах.pushbutton/script.py"
        },
        "panel_door": {
          "id": "panel_door",
          "name": "Щит над дверью",
          "icon": "📦",
          "description": "Установка квартирного щита над входной дверью",
          "category": "panels",
          "time_saved": 10,
          "script_path": "03_ЩитыВыключатели.panel/ЩитНадДверью.pushbutton/script.py"
        },
        "switches_doors": {
          "id": "switches_doors",
          "name": "Выключатели",
          "icon": "🔘",
          "description": "Авто-размещение выключателей у дверей",
          "category": "panels",
          "time_saved": 30,
          "script_path": "03_ЩитыВыключатели.panel/ВыключателиУДверей.pushbutton/script.py"
        },
        "sockets_general": {
          "id": "sockets_general",
          "name": "Общие розетки",
          "icon": "🔌",
          "description": "Проверка и настройка параметров розеток",
          "category": "sockets",
          "time_saved": 5,
          "script_path": "04_Розетки.panel/01_Общие.pushbutton/script.py"
        },
        "kitchen_block": {
          "id": "kitchen_block",
          "name": "Кухня: Гарнитур",
          "icon": "🍳",
          "description": "Розетки для встроенной кухонной техники",
          "category": "sockets",
          "time_saved": 25,
          "script_path": "04_Розетки.panel/02_КухняБлок.pushbutton/script.py"
        },
        "wet_zones": {
          "id": "wet_zones",
          "name": "Мокрые зоны",
          "icon": "💧",
          "description": "Розетки в санузлах (стиральные и пр.)",
          "category": "sockets",
          "time_saved": 10,
          "script_path": "04_Розетки.panel/05_ВлажныеЗоны.pushbutton/script.py"
        },
        "low_voltage": {
          "id": "low_voltage",
          "name": "Слаботочка",
          "icon": "📡",
          "description": "ТВ и Интернет розетки",
          "category": "sockets",
          "time_saved": 15,
          "script_path": "04_Розетки.panel/06_Слаботочка.pushbutton/script.py"
        },
        "shdup": {
          "id": "shdup",
          "name": "ШДУП",
          "icon": "⚡",
          "description": "Шина дополнительного уравнивания потенциалов",
          "category": "sockets",
          "time_saved": 5,
          "script_path": "04_Розетки.panel/07_ШДУП.pushbutton/script.py"
        },
        "magic_button": {
          "id": "magic_button",
          "name": "Волшебная кнопка",
          "icon": "✨",
          "description": "Полная автоматизация размещения всех элементов",
          "category": "automation",
          "time_saved": 60,
          "script_path": "10_АвтоРазмещение.panel/00_ВолшебнаяКнопка.pushbutton/script.py"
        }
      },
      "categories": {
        "lighting": {
          "id": "lighting",
          "name": "Освещение",
          "icon": "💡",
          "order": 1
        },
        "panels": {
          "id": "panels",
          "name": "Щиты и выключатели",
          "icon": "🔘",
          "order": 2
        },
        "sockets": {
          "id": "sockets",
          "name": "Розетки",
          "icon": "🔌",
          "order": 3
        },
        "automation": {
          "id": "automation",
          "name": "Автоматизация",
          "icon": "✨",
          "order": 4
        }
      },
      "dangerous_tools": ["magic_button"],
      "warning_messages": {
        "magic_button": "Волшебная кнопка разместит ВСЁ оборудование автоматически. Рекомендуется сохранить проект."
      }
    }

    # Now we just need to resolve script paths to verification
    # But since we are strictly using this list, we assume these paths exist in EOM.tab
    # We still need to find tab_path to allow verifying existence if we wanted, 
    # OR we just pass the relative paths and let run_tool handle it.
    # run_tool looks up script_path from this config.
    # But get_tools_list needs to return valid tools.
    
    # Let's ensure 'tools' has all needed fields.
    # We can skip the 'scan' part entirely. 
    # The frontend only needs id, name, description, category, icon.
    
    return config


@_expose
def get_tools_list():
    try:
        config = _get_tools_config()
        tools_dict = config.get("tools", {})
        tools_list = list(tools_dict.values())
        
        # Sort by category order then name
        # We need scanning categories to filter/sort properly
        categories = config.get("categories", {})
        
        def sort_key(tool):
            cat_id = tool.get("category", "")
            cat_order = 99
            if cat_id in categories:
                cat_order = categories[cat_id].get("order", 99)
            return (cat_order, tool.get("name", ""))
            
        tools_list.sort(key=sort_key)
        
        log(f"get_tools_list: tools_count={len(tools_list)}")
        return {"success": True, "tools": tools_list}
    except Exception as e:
        log(f"get_tools_list ERROR: {e}")
        return {"success": False, "error": str(e), "tools": []}


@_expose
def get_tools_config():
    return _get_tools_config()


@_expose
def get_revit_status():
    status_file = _get_status_file()
    log(f"get_revit_status: status_file={status_file}")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                status = json.load(f)
            age = time.time() - status.get("timestamp", 0)
            log(f"get_revit_status: status age={age:.2f}s")
            if age < 10:
                return {
                    "connected": True,
                    "document": status.get("document"),
                    "documentPath": status.get("documentPath"),
                    "revitVersion": status.get("revitVersion"),
                    "sessionId": _get_session_id(),
                }
        except: pass
    return {"connected": False, "document": None, "sessionId": _get_session_id()}


@_expose
def run_tool(tool_id: str, job_id: Optional[str] = None):
    log(f"run_tool called: tool_id={tool_id}, job_id={job_id}")
    log(f"run_tool: temp_root={_get_temp_root()}, session_id={_get_session_id()}")

    try:
        status = get_revit_status()
    except Exception:
        status = {"connected": False}

    if not status.get("connected"):
        return {
            "success": False,
            "error": "Revit не готов. Откройте проект и нажмите кнопку Hub в Revit, затем повторите.",
        }

    if not job_id:
        # Генерируем уникальный job_id с микросекундами (без tool_id, чтобы избежать недопустимых символов в файле)
        job_id = f"job_{int(time.time() * 1000000)}_{uuid.uuid4().hex[:8]}"

    # At runtime job_id is always set here.
    assert job_id is not None

    # One command file per job (prevents overwriting when user queues many tools).
    command_file = _get_command_file_for_job(job_id)
    command = f"run:{tool_id}:{job_id}"

    # FIX: Clear old legacy result file to prevent reading stale data
    legacy_result_file = _get_result_file()
    try:
        if os.path.exists(legacy_result_file):
            os.remove(legacy_result_file)
            log(f"Cleared old legacy result file")
    except Exception as e:
        log(f"Failed to clear result file: {e}")

    log(f"Command file: {command_file}")
    log(f"Command: {command}")

    try:
        with open(command_file, "w", encoding="utf-8") as f:
            f.write(command)
        try:
            os.utime(command_file, None)
        except Exception:
            pass
        log(f"Command written successfully")
        if os.path.exists(command_file):
            log(f"Verified: file exists, size={os.path.getsize(command_file)}")
        try:
            queued = {
                "status": "pending",
                "message": "Команда поставлена в очередь",
                "tool_id": tool_id,
                "job_id": job_id,
                "stats": {"processed": 0, "skipped": 0, "errors": 0, "total": 0},
                "timestamp": time.time(),
            }

            # Write per-job result (primary).
            result_file = _get_result_file_for_job(job_id)
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(queued, f, ensure_ascii=False, indent=2)

            # Also update legacy "last result" file for backwards compatibility / UI that expects it.
            legacy_result_file = _get_result_file()
            with open(legacy_result_file, "w", encoding="utf-8") as f:
                json.dump(queued, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log(f"ERROR writing queued result: {e}")
        return {"success": True, "job_id": job_id, "tool_id": tool_id, "message": "Команда отправлена в Revit"}
    except Exception as e:
        log(f"ERROR writing command: {e}")
        return {"success": False, "error": str(e)}


@_expose
def get_job_result(job_id: str):
    # Prefer per-job result file.
    result_file = _get_result_file_for_job(job_id)
    log(f"get_job_result: job_id={job_id}, result_file={result_file}")

    def _validate_and_return(result: dict) -> dict:
        # Check for timeout (10 minutes)
        status = result.get("status")
        if status in ["pending", "running"]:
            timestamp = result.get("timestamp", 0)
            if timestamp > 0 and (time.time() - timestamp > 600):
                result["status"] = "error"
                result["error"] = "Превышено время ожидания (10 мин)"
                result["message"] = "Задача остановлена по таймауту"
        return result

    if os.path.exists(result_file):
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                result = json.load(f)
            return _validate_and_return(result)
        except Exception as e:
            log(f"get_job_result ERROR (per-job): {e}")
            return {"job_id": job_id, "status": "error", "error": str(e)}

    # Fallback to legacy result file if it matches our job_id.
    legacy_result_file = _get_result_file()
    if os.path.exists(legacy_result_file):
        try:
            with open(legacy_result_file, "r", encoding="utf-8") as f:
                legacy = json.load(f)
            if legacy.get("job_id") == job_id:
                return _validate_and_return(legacy)
        except Exception:
            pass

    # Check for timeout if no result file found or if it's still pending
    # Note: This handles the case where the job was queued but never started/finished
    try:
        # We need to know when the job was started. 
        # Since we don't have a central DB, we rely on the client or the file.
        # But if the file doesn't exist, we can't check timestamp.
        # However, run_tool writes the result file immediately with 'pending'.
        # So if we are here, it means the result file is missing OR we are falling back.
        pass
    except:
        pass

    # No result yet.
    log("get_job_result: no result file, returning pending")
    return {"job_id": job_id, "status": "pending", "message": "Задача в очереди на выполнение"}


@_expose
def get_time_savings():
    savings_file = _get_savings_file()
    if os.path.exists(savings_file):
        try:
            with open(savings_file, "r", encoding="utf-8") as f:
                return _normalize_time_savings(json.load(f))
        except: pass
    return {"totalSeconds": 0, "totalSecondsMin": 0, "totalSecondsMax": 0, "executed": {}, "history": []}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_time_savings(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"totalSeconds": 0, "totalSecondsMin": 0, "totalSecondsMax": 0, "executed": {}, "history": []}

    total = _as_float(data.get("totalSeconds", 0))
    total_min = _as_float(data.get("totalSecondsMin", total), total)
    total_max = _as_float(data.get("totalSecondsMax", total), total)
    data["totalSeconds"] = total
    data["totalSecondsMin"] = total_min
    data["totalSecondsMax"] = total_max

    executed = data.get("executed")
    if not isinstance(executed, dict):
        executed = {}
    data["executed"] = executed

    history = data.get("history")
    if not isinstance(history, list):
        history = []

    normalized_history: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        avg = _as_float(item.get("minutes", 0.0), 0.0)
        mn = item.get("minutes_min", None)
        mx = item.get("minutes_max", None)
        if mn is None and mx is None:
            mn_f = avg
            mx_f = avg
        else:
            mn_f = _as_float(mn, avg)
            mx_f = _as_float(mx, avg)
        item["minutes"] = avg
        item["minutes_min"] = mn_f
        item["minutes_max"] = mx_f
        normalized_history.append(item)
    data["history"] = normalized_history

    return data


def _parse_minutes_range(minutes: Any) -> tuple[float, float]:
    if isinstance(minutes, dict):
        if "min" in minutes or "max" in minutes:
            mn = _as_float(minutes.get("min", 0.0), 0.0)
            mx = _as_float(minutes.get("max", mn), mn)
        else:
            mn = _as_float(minutes.get("minutes_min", 0.0), 0.0)
            mx = _as_float(minutes.get("minutes_max", mn), mn)
    else:
        mn = _as_float(minutes, 0.0)
        mx = mn

    if mn < 0:
        mn = 0.0
    if mx < 0:
        mx = 0.0
    if mx < mn:
        mn, mx = mx, mn
    return mn, mx


@_expose
def save_time_savings(data: dict):
    savings_file = _get_savings_file()
    try:
        with open(savings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@_expose
def add_time_saving(tool_id: str, minutes: Any):
    savings: dict[str, Any] = _normalize_time_savings(get_time_savings())
    mn, mx = _parse_minutes_range(minutes)
    avg = (mn + mx) / 2.0

    savings["executed"] = savings.get("executed", {})
    savings["executed"][tool_id] = int(savings["executed"].get(tool_id, 0) or 0) + 1

    savings["totalSeconds"] = _as_float(savings.get("totalSeconds", 0.0), 0.0) + (avg * 60.0)
    savings["totalSecondsMin"] = _as_float(savings.get("totalSecondsMin", 0.0), 0.0) + (mn * 60.0)
    savings["totalSecondsMax"] = _as_float(savings.get("totalSecondsMax", 0.0), 0.0) + (mx * 60.0)

    history = savings.get("history", [])
    if not isinstance(history, list):
        history = []
    history.insert(
        0,
        {
            "tool_id": tool_id,
            "minutes": avg,
            "minutes_min": mn,
            "minutes_max": mx,
            "timestamp": time.time(),
            "time": time.strftime("%H:%M:%S"),
        },
    )
    savings["history"] = history[:100]

    save_time_savings(savings)
    return savings


@_expose
def reset_time_savings():
    data = {
        "totalSeconds": 0,
        "totalSecondsMin": 0,
        "totalSecondsMax": 0,
        "executed": {},
        "history": [
            {
                "tool_id": "RESET",
                "minutes": 0,
                "minutes_min": 0,
                "minutes_max": 0,
                "timestamp": time.time(),
                "time": time.strftime("%H:%M:%S"),
                "message": "Сброс всех данных",
            }
        ],
    }
    save_time_savings(data)
    return data
