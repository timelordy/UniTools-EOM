# -*- coding: utf-8 -*-
"""EOM Hub - Главный файл приложения с Web интерфейсом."""
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

# Import API modules - handle both package and standalone execution
try:
    from .api import tools as api_tools  # noqa: F401
except ImportError:
    # Running as standalone script
    _src_dir = Path(__file__).parent
    if str(_src_dir) not in sys.path:
        sys.path.insert(0, str(_src_dir))
    from api import tools as api_tools  # noqa: F401

# Глобальная переменная для хранения порта
_server_port = None


def is_port_in_use(port: int) -> bool:
    """Проверяет, занят ли порт."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True


def find_free_port(start_port: int = 8090, max_attempts: int = 50) -> int:
    """Находит свободный порт, начиная с start_port."""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    raise RuntimeError(f"Не удалось найти свободный порт в диапазоне {start_port}-{start_port + max_attempts - 1}")


def cleanup():
    """Освобождает ресурсы при завершении приложения."""
    global _server_port
    print("Завершение EOM Hub...")
    _clear_hub_session_file()
    print("EOM Hub завершён")


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
        hwnd = user32.FindWindowW(None, "EOM Hub")
        if hwnd:
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    except Exception:
        pass


def start_app(dev_mode: bool = False) -> None:
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
    
    try:
        _server_port = find_free_port(8090)
        print(f"EOM Hub запущен на порту: {_server_port}")
    except RuntimeError as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    os.environ["EOM_HUB_PORT"] = str(_server_port)
    _write_hub_session_file(_server_port)
    
    eel.init(str(web_folder))

    # Патчим bottle после инициализации eel
    try:
        import bottle
        bottle.json_dumps = _patched_dumps
    except Exception:
        pass

    threading.Thread(target=set_window_topmost, daemon=True).start()
    
    try:
        eel.start(
            "index.html",
            size=(600, 900),
            position=None,
            port=_server_port,
            mode="chrome",
            block=True,
            cmdline_args=[
                f"--app=http://localhost:{_server_port}/index.html",
                "--no-first-run",
                "--disable-http-cache",
            ],
        )
    except KeyboardInterrupt:
        print("\nПрерывание...")
    finally:
        cleanup()


def main():
    """Main entry point."""
    dev = "--dev" in sys.argv
    start_app(dev_mode=dev)


if __name__ == "__main__":
    main()
