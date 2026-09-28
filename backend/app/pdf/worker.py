"""
Isolated PDF processing for SIH26237.

Untrusted PDFs (uploaded for registration or investigation) and decrypted plaintext
being marked are parsed by pymupdf (MuPDF, a large C code base) in a separate spawned
process, never in the server process that holds unlocked signing keys:

  - the worker receives only bytes and opaque marker tokens, never keys or paths;
  - each call has a wall-clock timeout; on timeout or crash the pool is torn down and
    recreated, and the request fails closed;
  - on POSIX the worker sets RLIMIT_AS / RLIMIT_CPU. On Windows no memory limit is
    enforced (documented limitation).

This is process isolation, not a sandbox: a MuPDF exploit would run with the server
user's file-system permissions but without access to the server's in-memory keys.
"""

import multiprocessing
import os
import threading
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from concurrent.futures.process import BrokenProcessPool
from typing import Any, Dict, Optional

from app import config


class PdfWorkerError(Exception):
    pass


def _init_worker(memory_mb: int, cpu_seconds: int) -> None:
    for name in list(os.environ):
        if name.startswith("SIH_") and "PASS" in name.upper():
            os.environ.pop(name, None)
    if os.name != "nt":
        try:
            import resource
            limit = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        except (ImportError, ValueError, OSError):
            pass


_pool: Optional[ProcessPoolExecutor] = None
_pool_lock = threading.Lock()


def _get_pool() -> ProcessPoolExecutor:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = ProcessPoolExecutor(
                max_workers=2,
                mp_context=multiprocessing.get_context("spawn"),
                initializer=_init_worker,
                initargs=(config.PDF_WORKER_MEMORY_MB, config.PDF_WORKER_TIMEOUT_SECONDS * 2),
            )
        return _pool


def _discard_pool() -> None:
    global _pool
    with _pool_lock:
        pool, _pool = _pool, None
    if pool is None:
        return
    for proc in list(getattr(pool, "_processes", {}).values()):
        try:
            proc.kill()
        except Exception:
            pass
    pool.shutdown(wait=False, cancel_futures=True)


def shutdown() -> None:
    _discard_pool()


def _call(func_name: str, *args, timeout: Optional[float] = None) -> Dict[str, Any]:
    from app.pdf import ops
    func = getattr(ops, func_name)
    timeout = timeout or config.PDF_WORKER_TIMEOUT_SECONDS
    try:
        future = _get_pool().submit(func, *args)
        return future.result(timeout=timeout)
    except FutureTimeout:
        _discard_pool()
        raise PdfWorkerError("PDF processing timed out")
    except BrokenProcessPool:
        _discard_pool()
        raise PdfWorkerError("PDF worker crashed")
    except PdfWorkerError:
        raise
    except Exception as exc:
        raise PdfWorkerError(f"PDF processing failed ({type(exc).__name__})")


def inspect(pdf_bytes: bytes) -> Dict[str, Any]:
    return _call("inspect", pdf_bytes, config.MAX_PDF_PAGES)


def render_hash(pdf_bytes: bytes) -> str:
    return _call("render_hash", pdf_bytes, config.MAX_PDF_PAGES)["render_hash"]


def mark(pdf_bytes: bytes, token: str) -> Dict[str, Any]:
    return _call("mark", pdf_bytes, token, config.MAX_PDF_PAGES)


def extract(pdf_bytes: bytes) -> Dict[str, Any]:
    return _call("extract", pdf_bytes, config.MAX_PDF_PAGES)
