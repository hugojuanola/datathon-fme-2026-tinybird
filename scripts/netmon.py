#!/usr/bin/env python3
"""Is it our connection? One line per second: ping to the home router and TCP connect time to RawTree.

    pythonw scripts/netmon.py                # appends to $SKORE_LOGS_DIR/net-YYYYMMDD.log (UTC), runs until stopped;
                                             # pythonw = no window to close (python works too, in a terminal)
    python scripts/netmon.py --report 60     # the last 60 minutes of that log, minute by minute, worst first

When the live loop loses answers, this tells where the time went: a slow or lost ping to the router is the
Wi-Fi (fix: a network cable, or sit next to the router); a clean router with slow RawTree connects is the
line or the internet; both clean means the cause is on this machine. Stdlib only, a few bytes per second.
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "api.rawtree.com"
QUIET = getattr(subprocess, "CREATE_NO_WINDOW", 0)     # run with pythonw: no console of ours, none for ping either


def logs_dir() -> Path:
    folder = os.environ.get("SKORE_LOGS_DIR")
    env = ROOT / ".env"
    if not folder and env.exists():
        for line in env.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "SKORE_LOGS_DIR":
                folder = value.strip()
    return Path(folder) if folder else ROOT / "logs"


def gateway() -> str:
    if sys.platform == "win32":
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object RouteMetric | Select-Object -First 1).NextHop"],
                             capture_output=True, text=True, timeout=30, creationflags=QUIET).stdout.strip()
    else:
        out = subprocess.run("ip route | awk '/default/ {print $3; exit}'", shell=True, capture_output=True, text=True).stdout.strip()
    return out.splitlines()[0] if out else "192.168.1.1"


def ping_ms(host: str) -> float:
    """Round trip to `host` in ms; -1 if no answer within a second."""
    args = ["ping", "-n", "1", "-w", "1000", host] if sys.platform == "win32" else ["ping", "-c", "1", "-W", "1", host]
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=3, creationflags=QUIET).stdout
    except Exception:
        return -1.0
    match = re.search(r"[=<]\s*([\d.]+)\s*ms", out)
    return float(match.group(1)) if match and "TTL" in out.upper() else -1.0


def connect_ms(host: str) -> float:
    """Time to open a TCP connection to `host`:443 in ms (includes the DNS lookup); -1 if it fails in 2 s."""
    t0 = time.time()
    try:
        socket.create_connection((host, 443), timeout=2).close()
        return 1000 * (time.time() - t0)
    except Exception:
        return -1.0


def report(minutes: int) -> None:
    path = logs_dir() / f"net-{time.strftime('%Y%m%d', time.gmtime())}.log"
    rows: dict[str, list[tuple[float, float]]] = {}
    for line in path.read_text().splitlines()[-60 * minutes:]:
        parts = line.split()
        if len(parts) == 3:
            rows.setdefault(parts[0][:5], []).append((float(parts[1]), float(parts[2])))
    print("minute (UTC)  router ping: lost / worst ms / mean ms   RawTree connect: failed / worst ms / mean ms")
    for minute, values in sorted(rows.items()):
        gw = [v[0] for v in values]
        rt = [v[1] for v in values]
        ok_gw, ok_rt = [v for v in gw if v >= 0] or [0.0], [v for v in rt if v >= 0] or [0.0]
        print(f"{minute}         {gw.count(-1.0):>4} / {max(ok_gw):>6.0f} / {sum(ok_gw) / len(ok_gw):>5.0f}"
              f"                     {rt.count(-1.0):>4} / {max(ok_rt):>6.0f} / {sum(ok_rt) / len(ok_rt):>5.0f}")


def main() -> None:
    if "--report" in sys.argv:
        report(int(sys.argv[sys.argv.index("--report") + 1]) if sys.argv[-1].isdigit() else 60)
        return
    folder = logs_dir()
    folder.mkdir(parents=True, exist_ok=True)
    router = gateway()
    print(f"router {router}, RawTree {HOST}: one line per second in {folder}", flush=True)
    while True:
        t0 = time.time()
        line = f"{time.strftime('%H:%M:%S', time.gmtime(t0))} {ping_ms(router):.0f} {connect_ms(HOST):.0f}\n"
        with open(folder / f"net-{time.strftime('%Y%m%d', time.gmtime(t0))}.log", "a") as f:
            f.write(line)
        time.sleep(max(0.0, 1.0 - (time.time() - t0)))


if __name__ == "__main__":
    main()
