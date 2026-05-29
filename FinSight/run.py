"""
FinSight Launcher
一键启动后端 (FastAPI) + 前端 (Vite)
"""
import os
import sys
import time
import subprocess
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

PYTHON = r"C:\Users\fanghongjiang\.workbuddy\binaries\python\envs\finsight\Scripts\python.exe"
NODE = r"C:\Users\fanghongjiang\.workbuddy\binaries\node\versions\22.12.0\node.exe"


def print_banner():
    print("=" * 50)
    print("  FinSight Launcher")
    print("=" * 50)
    print()


def start_backend():
    print("[*] Starting backend (FastAPI :8001) ...")
    proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    return proc


def start_frontend():
    print("[*] Starting frontend (Vite :3000) ...")
    proc = subprocess.Popen(
        [NODE, "node_modules/vite/bin/vite.js"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    return proc


def tail_output(proc, name):
    for line in iter(proc.stdout.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            print(f"[{name}] {text}")


def main():
    print_banner()

    backend = start_backend()
    frontend = start_frontend()

    print("\n[*] Waiting for services to start (8s) ...\n")
    time.sleep(8)

    webbrowser.open("http://localhost:3000")

    print("\n[*] Both services are running!")
    print("    Backend:  http://localhost:8001")
    print("    Frontend: http://localhost:3000")
    print("    API Docs: http://localhost:8001/docs")
    print("\n    Press Ctrl+C to stop all services.\n")

    try:
        import threading
        t1 = threading.Thread(target=tail_output, args=(backend, "backend"), daemon=True)
        t2 = threading.Thread(target=tail_output, args=(frontend, "frontend"), daemon=True)
        t1.start()
        t2.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down ...")
    finally:
        backend.terminate()
        frontend.terminate()
        print("[*] Done.")


if __name__ == "__main__":
    main()
