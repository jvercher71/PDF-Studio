"""
Pytest plugin: PyMuPDF (fitz) C-extension hardening.

Two macOS arm64 + Python 3.12 issues are addressed here:

1. **Pre-import on startup.** The SWIG-generated `_mupdf` C extension
   segfaults during `create_module` when its loader runs from inside
   pytest's AssertionRewritingHook.exec_module. Importing `fitz` while
   this plugin is loaded by pytest's normal plugin loader (which doesn't
   rewrite) seeds `sys.modules` so later test imports become cache
   lookups, sidestepping the crash.

2. **Clean exit on session finish.** A C-extension destructor (somewhere
   in the pymupdf/PySide6/cffi cleanup graph) segfaults during interpreter
   finalization on this platform, even after all tests pass. Pytest's own
   `exitstatus` is already finalized by the time the crash hits, so we
   call `os._exit(...)` from `pytest_sessionfinish` to bypass the broken
   teardown and preserve the real test result.

Registered via pyproject.toml's [tool.pytest.ini_options].addopts:
    addopts = "... -p _pytest_pre_import"
"""

import os

import fitz  # noqa: F401


def pytest_unconfigure(config):
    """
    Run as the very last pytest hook. By this point the terminal summary,
    coverage report, and all other reporters have written their output.
    Force-exit to avoid the C-extension teardown segfault.
    """
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    # exitstatus isn't available here; use the session-tracked code on the
    # config's pluginmanager if present, otherwise fall back to 0 (since
    # if we got this far without pytest already aborting, tests succeeded).
    exitcode = getattr(config, "_pytest_pre_import_exitcode", 0)
    os._exit(int(exitcode))


def pytest_sessionfinish(session, exitstatus):
    # Capture the real exit status; pytest_unconfigure can't see it directly.
    session.config._pytest_pre_import_exitcode = exitstatus
