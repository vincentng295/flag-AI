#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chạy "Cướp Cờ Đáp Án AI" bằng Gunicorn:   python gunicorn.py

- Chỉ dùng 1 worker: toàn bộ phòng/trận đấu nằm trong RAM của tiến trình game, và Socket.IO cần
  mọi request của một người chơi đi vào cùng một tiến trình. Muốn chịu tải hơn thì tăng số luồng
  (GUNICORN_THREADS), KHÔNG tăng số worker.
- worker "gthread": mỗi kết nối WebSocket giữ một luồng, nên GUNICORN_THREADS >= số người chơi + khán giả
  tối đa (mặc định 256). Cần thư viện simple-websocket để WebSocket chạy được ở chế độ threading.
- Host/cổng/.env đọc từ main.py (HOST, PORT, ENV_FILE...). Biến riêng của Gunicorn:
    GUNICORN_THREADS (256)   GUNICORN_LOGLEVEL (info)   GUNICORN_ACCESSLOG (trống = tắt, "-" = bật ra stdout)
    GUNICORN_TIMEOUT (120)   GUNICORN_GRACEFUL (10)     APP_MODULE (main)
- Cloudflare Tunnel chạy ở tiến trình cha (một lần), HTTPS trực tiếp + nạp câu hỏi chạy trong worker.
- Windows không có Gunicorn: tự chuyển sang máy chủ dev của main.py.
"""
import os, sys

# File này tên "gunicorn.py" trùng tên gói gunicorn: bỏ thư mục chứa nó khỏi sys.path khi import gunicorn
# (nếu không `import gunicorn` sẽ nạp chính file này), rồi thêm lại ở cuối để `import main` vẫn chạy.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.getcwd()) != _HERE]
try:
    from gunicorn.app.base import BaseApplication
except ImportError as e:
    BaseApplication = None
    _import_err = e
sys.path.append(_HERE)

import importlib

APP_MODULE = os.getenv("APP_MODULE", "main")


def _num(name, default):
    try:
        return int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


# ---------- hook của Gunicorn ----------
def when_ready(server):
    importlib.import_module(APP_MODULE).startup_master()


def post_worker_init(worker):
    importlib.import_module(APP_MODULE).startup_worker()


def on_exit(server):
    importlib.import_module(APP_MODULE).stop_tunnel()


if BaseApplication is not None:
    class Server(BaseApplication):
        def __init__(self, wsgi_app, options):
            self.options, self.wsgi_app = options, wsgi_app
            super().__init__()

        def load_config(self):
            for k, v in self.options.items():
                self.cfg.set(k, v)

        def load(self):
            return self.wsgi_app


def main():
    mod = importlib.import_module(APP_MODULE)  # nạp .env, tạo app (preload) trước khi đọc HOST/PORT
    if BaseApplication is None:
        if os.name == "nt":
            print("[!] Gunicorn không chạy được trên Windows - dùng máy chủ dev của main.py.")
            mod.run_dev()
            return
        print(f"[!] Chưa cài Gunicorn ({_import_err}). Chạy: pip install -r requirements.txt")
        sys.exit(1)
    try:
        import simple_websocket  # noqa: F401
    except ImportError:
        print("[!] Thiếu simple-websocket: chỉ có long-polling, WebSocket sẽ không dùng được. pip install simple-websocket")
    if _num("GUNICORN_WORKERS", 1) != 1:
        print("[!] Bỏ qua GUNICORN_WORKERS: game giữ trạng thái trong RAM nên chỉ chạy 1 worker (hãy tăng GUNICORN_THREADS).")
    host, port = mod.HOST, mod.PORT
    options = {
        "bind": f"[{host}]:{port}" if ":" in host else f"{host}:{port}",
        "worker_class": "gthread", "workers": 1, "threads": max(8, _num("GUNICORN_THREADS", 256)),
        "preload_app": True,
        "timeout": _num("GUNICORN_TIMEOUT", 120), "graceful_timeout": _num("GUNICORN_GRACEFUL", 10), "keepalive": 30,
        "loglevel": os.getenv("GUNICORN_LOGLEVEL", "info"), "errorlog": "-",
        "accesslog": os.getenv("GUNICORN_ACCESSLOG", "").strip() or None,
        "proc_name": "cuopco",
        "when_ready": when_ready, "post_worker_init": post_worker_init, "on_exit": on_exit,
    }
    if os.path.isdir("/dev/shm"):
        options["worker_tmp_dir"] = "/dev/shm"  # file heartbeat nằm trong RAM, tránh treo khi đĩa chậm/Docker
    Server(mod.app, options).run()


if __name__ == "__main__":
    main()
