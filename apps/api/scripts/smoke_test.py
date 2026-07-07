"""Full smoke test for v2 API + extension readiness."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE = "http://localhost:8000"
API_DIR = Path(__file__).resolve().parents[1]
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" - {detail}" if detail else ""))


def health_ok() -> bool:
    try:
        r = requests.get(f"{BASE}/health", timeout=2)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False


def start_api() -> subprocess.Popen | None:
    if health_ok():
        return None

    print("API not running on port 8000 — starting temporary server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=API_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(45):
        if health_ok():
            print("API ready.\n")
            return proc
        time.sleep(1)

    proc.terminate()
    print("\nFailed to start API within 45s.")
    print("Start manually: cd apps/api && python -m app.main")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Smoke test API + extension")
    parser.add_argument(
        "--no-start-api",
        action="store_true",
        help="Do not auto-start API if it is not running",
    )
    args = parser.parse_args()

    api_proc = None
    if not health_ok():
        if args.no_start_api:
            check("GET /health", False, "API not running on localhost:8000")
            print("\nStart API: cd apps/api && python -m app.main")
            print("Or run: python scripts/smoke_test.py  (auto-starts API)")
            sys.exit(1)
        api_proc = start_api()

    try:
        _run_checks()
    finally:
        if api_proc:
            api_proc.terminate()
            api_proc.wait(timeout=10)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n{'='*50}")
    print(f"TOTAL: {passed} passed, {failed} failed / {len(RESULTS)}")
    if failed:
        print("\nFailed:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name}: {detail}")
    sys.exit(0 if failed == 0 else 1)


def _run_checks():
    # 1 Health
    try:
        r = requests.get(f"{BASE}/health", timeout=10)
        data = r.json()
        check("GET /health", r.status_code == 200 and data.get("status") == "ok", json.dumps(data))
    except Exception as e:
        check("GET /health", False, str(e))
        return

    # 2 Register + login
    email = f"exttest{int(time.time())}@example.com"
    password = "testpass123"
    token = None
    try:
        r = requests.post(f"{BASE}/api/v1/auth/register", json={"email": email, "password": password}, timeout=15)
        token = r.json().get("access_token")
        check("POST /auth/register", r.status_code == 200 and bool(token))
    except Exception as e:
        check("POST /auth/register", False, str(e))

    if not token:
        try:
            r = requests.post(f"{BASE}/api/v1/auth/login", json={"email": email, "password": password}, timeout=15)
            token = r.json().get("access_token")
            check("POST /auth/login", r.status_code == 200 and bool(token))
        except Exception as e:
            check("POST /auth/login", False, str(e))

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # 3 Settings
    try:
        r = requests.get(f"{BASE}/api/v1/settings", headers=headers, timeout=10)
        check("GET /settings", r.status_code == 200, str(r.json().get("recording_quality")))
    except Exception as e:
        check("GET /settings", False, str(e))

    # 4 Analytics
    try:
        r = requests.get(f"{BASE}/api/v1/analytics", headers=headers, timeout=10)
        check("GET /analytics", r.status_code == 200, f"meetings={r.json().get('total_meetings')}")
    except Exception as e:
        check("GET /analytics", False, str(e))

    # 5 Create meeting
    meeting_id = None
    try:
        r = requests.post(
            f"{BASE}/api/v1/meetings",
            headers=headers,
            json={"platform": "google_meet", "title": "Extension Test Meeting"},
            timeout=15,
        )
        meeting_id = r.json().get("id")
        check("POST /meetings", r.status_code == 200 and bool(meeting_id), meeting_id or "")
    except Exception as e:
        check("POST /meetings", False, str(e))

    # 6 Upload small webm-like blob (minimal)
    if meeting_id and token:
        try:
            fake_audio = b"RIFF" + b"\x00" * 100  # not real webm but tests upload path
            files = {"file": ("test.webm", fake_audio, "audio/webm")}
            data = {"meeting_id": meeting_id, "platform": "google_meet"}
            r = requests.post(
                f"{BASE}/api/v1/recordings/upload",
                headers=headers,
                files=files,
                data=data,
                timeout=60,
            )
            check("POST /recordings/upload", r.status_code == 200, r.json().get("message", "")[:60])
        except Exception as e:
            check("POST /recordings/upload", False, str(e))

    # 7 List meetings
    try:
        r = requests.get(f"{BASE}/api/v1/meetings", headers=headers, timeout=10)
        check("GET /meetings", r.status_code == 200, f"count={r.json().get('total')}")
    except Exception as e:
        check("GET /meetings", False, str(e))

    # 8 Extension dist files
    dist = Path(__file__).resolve().parents[3] / "extension" / "dist"
    required = ["manifest.json", "popup.html", "background/service-worker.js", "popup/popup.js", "icons/icon128.png"]
    missing = [f for f in required if not (dist / f).exists()]
    check("Extension dist built", not missing, "missing: " + ", ".join(missing) if missing else "all core files present")


if __name__ == "__main__":
    main()
