"""Keep the recommender running, with no window anyone could close.

    pythonw -m reco.supervise [--standby]      # started by scripts/swap_server.ps1, not by hand

On 14 Nov, 18:53 UTC the server was running in a console window of its own; the window was closed and
nobody answered for four minutes (on-time 73 % in that quarter of an hour, from first to third on the
board). So the live server has no window at all: this supervisor is started with pythonw (no console),
runs `python -m reco.serve` as a hidden child that writes $SKORE_LOGS_DIR/serve.log itself (--log), and
starts it again two seconds after it exits, for whatever reason. Neither can receive a Ctrl+C.

To see it: Task Manager → Details → pythonw.exe (this) and python.exe (the server), or the log.
To replace or restart it: scripts/swap_server.ps1. To stop it for good: end the pythonw process first.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from reco.rawtree import LOGS, ROOT


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / "serve.log"
    python = Path(sys.executable)
    if python.name.lower() == "pythonw.exe":       # the server is a console program: it gets python.exe, hidden
        python = python.with_name("python.exe")
    args = [str(python), "-u", "-m", "reco.serve", "--log", str(log)] + [a for a in sys.argv[1:] if a == "--standby"]
    while True:
        try:
            code = subprocess.call(args, cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception as e:
            code = f"could not start: {str(e)[:200]}"
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} server exited ({code}) - starting it again in 2 s\n")
        args = [a for a in args if a != "--standby"]        # after a crash nobody is there to give the GO
        time.sleep(2)


if __name__ == "__main__":
    main()
