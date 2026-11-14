"""Process priority: the serving loop goes first, offline jobs give way.

On 14 Nov a training run and a test script on the same laptop made the live loop miss 25 % of its
answers. Offline scripts now call `background()` and the server calls `foreground()`. Best effort:
if the operating system refuses, nothing breaks.
"""
from __future__ import annotations

import os
import sys

_WINDOWS_CLASS = {"high": 0x00000080, "below_normal": 0x00004000}


def _set(level: str) -> None:
    try:
        if sys.platform == "win32":
            import ctypes

            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetPriorityClass(handle, _WINDOWS_CLASS[level])
        elif level == "below_normal":
            os.nice(10)
    except Exception:
        pass


def foreground() -> None:
    _set("high")


def stay_awake() -> None:
    """Ask Windows not to put the machine to sleep while this process runs (what a video player does).
    It does not survive closing the lid or a forced restart: see docs/final-round.md."""
    try:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    except Exception:
        pass


def background() -> None:
    _set("below_normal")
