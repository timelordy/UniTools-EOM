# -*- coding: utf-8 -*-
"""UniTools Hub - Главный файл приложения с Web интерфейсом."""
from __future__ import annotations

import sys
import os
import uuid
import tempfile
import threading
import time
import socket
import atexit
import signal
import json
from pathlib import Path

# Force UTF-8 encoding (only if stdout/stderr exist)
if sys.stdout is not None and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr is not None and hasattr(sys.stderr, 'encoding') and sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import eel

# Патчим json.dumps для корректной сериализации кириллицы
_original_dumps = json.dumps
def _patched_dumps(*args, **kwargs):
    """Патч для json.dumps с ensure_ascii=False по умолчанию."""
    if 'ensure_ascii' not in kwargs:
        kwargs['ensure_ascii'] = False
    return _original_dumps(*args, **kwargs)

json.dumps = _patched_dumps

# Патчим bottle
try:
    import bottle
    bottle.json_dumps = _patched_dumps
except Exception:
    pass


# --- Session binding (Hub <-> Revit) ---
def _get_arg_value(argv, key):
    key_eq = key + "="
    for idx, arg in enumerate(argv):
        if arg == key and idx + 1 < len(argv):
            return argv[idx + 1]
        if arg.startswith(key_eq):
            return arg.split("=", 1)[1]
    return None


def _get_arg_int(argv, key) -> int | None:
    value = _get_arg_value(argv, key)
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _init_session_id():
    session_id = os.environ.get("EOM_SESSION_ID")
    if not session_id:
        session_id = _get_arg_value(sys.argv, "--session") or _get_arg_value(sys.argv, "--session-id")
    if not session_id:
        session_id = str(uuid.uuid4())
    os.environ["EOM_SESSION_ID"] = session_id
    return session_id


def _get_temp_root() -> str:
    return os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()


def _get_hub_session_path() -> str | None:
    if not SESSION_ID:
        return None
    return os.path.join(_get_temp_root(), f"eom_hub_session_{SESSION_ID}.json")


def _write_hub_session_file(port: int | None) -> None:
    path = _get_hub_session_path()
    if not path:
        return
    data = {
        "sessionId": SESSION_ID,
        "pid": os.getpid(),
        "hubPort": port,
        "exePath": getattr(sys, "executable", "") or "",
        "startedAt": time.time(),
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _clear_hub_session_file() -> None:
    path = _get_hub_session_path()
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


SESSION_ID = _init_session_id()

# Import API modules - robust for source + frozen (PyInstaller) execution.
def _import_api_tools():
    # 1) Frozen build: prefer module name that PyInstaller can reliably bundle.
    if getattr(sys, "frozen", False):
        import importlib
        try:
            return importlib.import_module("src.api.tools")
        except Exception:
            # Fall back to plain 'api' in case spec bundles it differently.
            return importlib.import_module("api.tools")

    # 2) Source run: we can import relatively when launched as a package.
    try:
        from .api import tools as _tools
        return _tools
    except Exception:
        pass

    # 3) Source run (script mode): put src/ and project root on sys.path and import.
    _src_dir = Path(__file__).resolve().parent
    _project_root = _src_dir.parent
    for _p in (str(_src_dir), str(_project_root)):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    try:
        from api import tools as _tools
        return _tools
    except Exception:
        import importlib
        return importlib.import_module("src.api.tools")


api_tools = _import_api_tools()  # noqa: F401


def _json_response(payload, status_code: int = 200) -> str:
    """Return JSON response for REST fallback endpoints."""
    bottle.response.status = status_code
    bottle.response.content_type = "application/json; charset=utf-8"
    return _patched_dumps(payload)


@bottle.get("/api/tools-config")
def api_tools_config_route():
    try:
        return _json_response(api_tools.get_tools_config())
    except Exception as exc:
        return _json_response({"error": str(exc)}, status_code=500)


@bottle.get("/api/revit-status")
def api_revit_status_route():
    try:
        return _json_response(api_tools.get_revit_status())
    except Exception as exc:
        return _json_response({"connected": False, "error": str(exc)}, status_code=500)


@bottle.get("/api/time-savings")
def api_time_savings_route():
    try:
        return _json_response(api_tools.get_time_savings())
    except Exception as exc:
        return _json_response({"error": str(exc)}, status_code=500)


@bottle.get("/api/job-result/<job_id>")
def api_job_result_route(job_id: str):
    try:
        return _json_response(api_tools.get_job_result(job_id))
    except Exception as exc:
        return _json_response({"job_id": job_id, "status": "error", "error": str(exc)}, status_code=500)


@bottle.post("/api/run-tool")
def api_run_tool_route():
    try:
        payload = bottle.request.json or {}
    except Exception:
        payload = {}

    tool_id = payload.get("toolId") or payload.get("tool_id")
    job_id = payload.get("jobId") or payload.get("job_id")

    if not tool_id:
        return _json_response({"success": False, "error": "toolId is required"}, status_code=400)

    try:
        result = api_tools.run_tool(str(tool_id), str(job_id) if job_id else None)
        return _json_response(result)
    except Exception as exc:
        return _json_response({"success": False, "error": str(exc)}, status_code=500)


@bottle.post("/api/reset-time-savings")
def api_reset_time_savings_route():
    try:
        return _json_response(api_tools.reset_time_savings())
    except Exception as exc:
        return _json_response({"error": str(exc)}, status_code=500)


@bottle.post("/api/add-time-saving")
def api_add_time_saving_route():
    try:
        payload = bottle.request.json or {}
    except Exception:
        payload = {}

    tool_id = payload.get("toolId") or payload.get("tool_id")
    minutes = payload.get("minutes")

    if not tool_id or minutes is None:
        return _json_response({"error": "toolId and minutes are required"}, status_code=400)

    try:
        result = api_tools.add_time_saving(str(tool_id), minutes)
        return _json_response(result)
    except Exception as exc:
        return _json_response({"error": str(exc)}, status_code=500)

# Глобальная переменная для хранения порта
_server_port = None
WINDOW_TITLES = ("UniTools Hub", "UniTools EOM", "EOM Hub")


def is_port_in_use(port: int) -> bool:
    """Back-compat wrapper (defaults to localhost)."""
    return is_port_in_use_on_host("127.0.0.1", port)


def is_port_in_use_on_host(host: str, port: int) -> bool:
    """Проверяет, занят ли порт при bind на указанный host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_free_port(host: str, start_port: int = 8090, max_attempts: int = 50) -> int:
    """Находит свободный порт, начиная с start_port, проверяя bind на host."""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use_on_host(host, port):
            return port
    raise RuntimeError(f"Не удалось найти свободный порт в диапазоне {start_port}-{start_port + max_attempts - 1}")


def _resolve_server_host() -> str:
    host = (os.environ.get("EOM_HUB_HOST") or "").strip()
    if not host:
        host = _get_arg_value(sys.argv, "--host") or ""
    host = str(host).strip()
    return host or "127.0.0.1"


def _resolve_server_port() -> int | None:
    env_port = (os.environ.get("EOM_HUB_BIND_PORT") or os.environ.get("EOM_HUB_PORT") or "").strip()
    if env_port:
        try:
            return int(env_port)
        except Exception:
            pass
    return _get_arg_int(sys.argv, "--port")


def cleanup():
    """Освобождает ресурсы при завершении приложения."""
    global _server_port
    print("Завершение UniTools Hub...")
    _clear_hub_session_file()
    print("UniTools Hub завершён")


def signal_handler(signum, frame):
    """Обработчик сигналов завершения."""
    print(f"Получен сигнал {signum}, завершаем...")
    cleanup()
    sys.exit(0)


def set_window_topmost():
    """Устанавливает окно поверх всех."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001

        time.sleep(1)
        hwnd = None
        for title in WINDOW_TITLES:
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                break
        if hwnd:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    except Exception:
        pass


def start_app(dev_mode: bool = False, headless: bool = False) -> None:
    """Запускает приложение с Web интерфейсом."""
    global _server_port
    
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Определяем базовый путь
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
        web_folder = base_path / "frontend" / "dist"
    else:
        project_root = Path(__file__).parent.parent
        web_folder = project_root / "frontend" / ("src" if dev_mode else "dist")
    
    if not web_folder.exists():
        print(f"Ошибка: папка с фронтендом не найдена: {web_folder}")
        print("Запустите сборку фронтенда: npm run build")
        sys.exit(1)
    
    bind_host = _resolve_server_host()
    requested_port = _resolve_server_port()

    try:
        if requested_port is not None:
            if is_port_in_use_on_host(bind_host, requested_port):
                raise RuntimeError(f"Порт {requested_port} уже занят (host={bind_host})")
            _server_port = requested_port
        else:
            _server_port = find_free_port(bind_host, 8090)

        print(f"UniTools Hub запущен: http://{bind_host}:{_server_port}")
    except RuntimeError as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    os.environ["EOM_HUB_HOST"] = str(bind_host)
    os.environ["EOM_HUB_PORT"] = str(_server_port)
    _write_hub_session_file(_server_port)
    
    eel.init(str(web_folder))

    # Патчим bottle после инициализации eel
    try:
        import bottle
        bottle.json_dumps = _patched_dumps
    except Exception:
        pass

    open_browser = not headless
    if open_browser:
        threading.Thread(target=set_window_topmost, daemon=True).start()
    
    try:
        eel.start(
            "index.html",
            size=(600, 900),
            position=None,
            host=bind_host,
            port=_server_port,
            # In headless mode we still run the web server but do NOT open any UI window.
            mode="chrome" if open_browser else False,
            block=True,
            cmdline_args=[
                f"--app=http://127.0.0.1:{_server_port}/index.html",
                "--no-first-run",
                "--disable-http-cache",
            ] if open_browser else [],
        )
    except KeyboardInterrupt:
        print("\nПрерывание...")
    finally:
        cleanup()


def main():
    """Main entry point."""
    dev = "--dev" in sys.argv
    headless_arg = "--headless" in sys.argv
    headless_env = os.environ.get("EOM_HUB_HEADLESS", "").strip().lower() in ("1", "true", "yes")
    start_app(dev_mode=dev, headless=headless_arg or headless_env)


if __name__ == "__main__":
    main()
