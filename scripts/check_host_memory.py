"""Read-only process-memory probe; never changes model/data or opens a DB."""
import ctypes
import json
import os
import platform
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def memory():
    if os.name == "nt":
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")
            ]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return {"resident_mib": round(counters.WorkingSetSize / 2**20, 1), "peak_resident_mib": round(counters.PeakWorkingSetSize / 2**20, 1), "private_commit_mib": round(counters.PrivateUsage / 2**20, 1), "peak_private_commit_mib": round(counters.PeakPagefileUsage / 2**20, 1)}
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"peak_resident_mib": round(peak / (2**20 if sys.platform == "darwin" else 1024), 1)}


stages = [{"phase": "python_start", **memory()}]
from app.main import app
from app.ml.runtime import load_runtime
from app.ml.prediction import score_scenario
from app.core.security import hash_password, verify_password
stages.append({"phase": "full_api_import", **memory()})
runtime = load_runtime()
assert runtime.ready, runtime.reason
stages.append({"phase": "original_model_loaded", **memory()})
def predict():
    return score_scenario("PALO ALTO CA / BRYANT #2", "Level 2", date(2020, 6, 15), "22:00")
assert predict()["probability"] >= 0
stages.append({"phase": "24_hour_prediction", **memory()})
password = secrets.token_urlsafe(20)
encoded = hash_password(password)
with ThreadPoolExecutor(max_workers=4) as pool:
    jobs = [pool.submit(predict), pool.submit(predict)] + [pool.submit(verify_password, password, encoded) for _ in range(2)]
    for job in jobs:
        assert job.result() is not False
stages.append({"phase": "two_concurrent_predictions_and_two_logins", **memory()})
result = {"platform": platform.system(), "python": platform.python_version(), "one_process": True, "artifact_sha256": runtime.artifact_sha256, "history_rows": len(runtime.bundle["history"]), "stages": stages, "limits": "Local OS measurement only; not a Linux cgroup/Render test. No HTTP/database load or arbitrary concurrent-login guarantee."}
print(json.dumps(result, indent=2))

