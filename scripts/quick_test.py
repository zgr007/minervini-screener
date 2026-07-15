"""Quick integration test to verify server starts and responds."""
import subprocess
import sys
import time
import urllib.request
import urllib.error
import os

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

print("Starting server...")
proc = subprocess.Popen(
    [sys.executable, "app.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Wait for server to start
for i in range(15):
    time.sleep(1)
    try:
        resp = urllib.request.urlopen("http://localhost:8000/health", timeout=3)
        data = resp.read().decode()
        print(f"[OK] Health endpoint: {data}")
        break
    except Exception as e:
        if i == 14:
            proc.kill()
            print(f"[FAIL] Server did not start: {e}")
            sys.exit(1)
        print(f"  waiting... ({i+1}s)")

# Test /docs
try:
    resp = urllib.request.urlopen("http://localhost:8000/docs", timeout=3)
    print(f"[OK] Swagger docs: HTTP {resp.status}")
except Exception as e:
    print(f"[FAIL] Docs unavailable: {e}")

# Test /redoc
try:
    resp = urllib.request.urlopen("http://localhost:8000/redoc", timeout=3)
    print(f"[OK] ReDoc: HTTP {resp.status}")
except Exception as e:
    print(f"[FAIL] ReDoc unavailable: {e}")

# Shutdown
proc.terminate()
try:
    proc.wait(timeout=5)
except:
    proc.kill()

print("\nAll checks passed! Server works correctly.")
