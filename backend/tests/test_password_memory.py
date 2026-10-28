"""Concurrent sign-ins keep the existing full Argon2 cost without memory spikes."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.core import security


def test_password_checks_share_a_bounded_memory_slot(monkeypatch):
    lock = threading.Lock()
    state = {"active": 0, "peak": 0}
    def operation(*args):
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        time.sleep(0.02)
        with lock:
            state["active"] -= 1
        return True
    monkeypatch.setattr(type(security._hasher), "verify", operation)
    monkeypatch.setattr(type(security._hasher), "hash", operation)
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(security.verify_password, "value", "hash") for _ in range(3)]
        jobs.append(pool.submit(security.hash_password, "new value"))
        assert all(job.result(timeout=5) for job in jobs)
    assert state["peak"] == 1
    assert security._hasher.memory_cost == 65536 and security._hasher.time_cost == 2
