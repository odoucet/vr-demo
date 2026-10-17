"""Verrou GPU partagé (pipeline/gpu.lock) : une seule charge lourde à la fois sur la carte."""
import json
import os
import socket
import time
from contextlib import contextmanager
from pathlib import Path

LOCK = Path(__file__).parent / "gpu.lock"


@contextmanager
def gpu_lock(owner):
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit(f"GPU déjà verrouillé ({LOCK}) : {LOCK.read_text(encoding='utf-8').strip()}\n"
                         "Si ce verrou est orphelin, supprimer le fichier.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"owner": owner, "pid": os.getpid(), "host": socket.gethostname(),
                   "since": time.strftime("%Y-%m-%d %H:%M:%S")}, f)
    try:
        yield
    finally:
        LOCK.unlink(missing_ok=True)
