#!/usr/bin/env python3
"""Wake a human with an alarm when we are no longer first on the public leaderboard (stdlib only).

It only reads https://datathon.rawtree.dev/api/state and plays a sound: it never touches the live
system. Whoever wakes up decides what to change.

    python3 scripts/watch_rank.py --test          # play the alarm once, as it will ring, and exit
    python3 scripts/watch_rank.py                 # watch: one reading every board update (~10 min)
    python3 scripts/watch_rank.py --snooze 30     # silence the alarm for 30 minutes (while you work)

Run it detached from any terminal, keeping the laptop awake:

    systemd-run --user --unit=skore-watch --collect \
        systemd-inhibit --what=sleep:idle --who=skore-watch --why="leaderboard alarm" \
        python3 -u "$PWD/scripts/watch_rank.py"
    journalctl --user -u skore-watch -f           # its readings
    systemctl --user stop skore-watch             # stop it

Alarm when: we are not #1 (practice ranks on the last 60 minutes, so this is not 15-minute noise),
or, during the final (only lights are shown), our light is RED. The alarm unmutes the speakers, sets
them to --volume (100 %) and plays the siren at --gain (8 %, the level chosen), so it sounds the same
whatever the volume was left at; it rings for --ring seconds (or until --snooze), then puts the old
volume back. It
rings again at the next reading if nothing changed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import subprocess
import sys
import time
import urllib.request
import wave
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://datathon.rawtree.dev/api/state"
TZ = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parent.parent
STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "skore-watch"
SNOOZE = STATE / "snooze_until"
SOUND = STATE / "alarm.wav"
SINK = "@DEFAULT_AUDIO_SINK@"


def team_id() -> str:
    if os.environ.get("TEAM_ID"):
        return os.environ["TEAM_ID"]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "TEAM_ID":
                return value.strip()
    return "team_06"


def now() -> str:
    return datetime.now(TZ).strftime("%a %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


# ---------------------------------------------------------------- sound

def make_sound() -> None:
    """A two-tone siren, 4 seconds, written once."""
    STATE.mkdir(parents=True, exist_ok=True)
    if SOUND.exists():
        return
    rate, out = 44100, bytearray()
    for i in range(16):                                   # 16 beeps of 0.25 s
        freq = 1046 if i % 2 == 0 else 784
        n = int(rate * 0.25)
        for k in range(n):
            env = min(1.0, k / 400, (n - k) / 400)        # no clicks at the edges
            x = math.sin(2 * math.pi * freq * k / rate)
            x = max(-1.0, min(1.0, 1.6 * x))              # slightly squared: cuts through a room
            out += struct.pack("<h", int(env * 0.9 * 32767 * x))
    with wave.open(str(SOUND), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(out))


def play(gain: float) -> None:
    subprocess.run(["pw-play", f"--volume={gain}", str(SOUND)], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def notify(title: str, body: str) -> None:
    subprocess.run(["notify-send", "-u", "critical", "-a", "skore-watch", title, body], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def snoozed() -> bool:
    try:
        return time.time() < float(SNOOZE.read_text())
    except (OSError, ValueError):
        return False


def ring(seconds: float, volume: float, gain: float) -> None:
    """Unmute, set the speakers to `volume`, ring at `gain` until `seconds` pass or someone snoozes, restore the volume."""
    before = subprocess.run(["wpctl", "get-volume", SINK], capture_output=True, text=True).stdout
    try:
        subprocess.run(["wpctl", "set-mute", SINK, "0"], check=False)
        subprocess.run(["wpctl", "set-volume", SINK, str(volume)], check=False)
        end = time.time() + seconds
        while time.time() < end and not snoozed():
            play(gain)
    finally:
        parts = before.split()                            # "Volume: 0.40 [MUTED]"
        if len(parts) >= 2:
            subprocess.run(["wpctl", "set-volume", SINK, parts[1]], check=False)
        if "[MUTED]" in before:
            subprocess.run(["wpctl", "set-mute", SINK, "1"], check=False)


# ---------------------------------------------------------------- board

def fetch() -> dict:
    req = urllib.request.Request(URL, headers={"User-Agent": "datathon-agent/watch_rank.py"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def reading(s: dict, me: str) -> tuple[bool, str]:
    """(alarm?, one line describing the board)."""
    if s.get("mode") == "final_running":
        lights = {l["team_id"]: l["green"] for l in s.get("lights") or []}
        if me not in lights:
            return False, "final running, our light is not on the board"
        return (not lights[me]), f"final running, our light is {'GREEN' if lights[me] else 'RED'}"
    teams = s.get("teams") or []
    ids = [t["team_id"] for t in teams]
    if me not in ids:
        return False, f"mode={s.get('mode')}, we are not on the board"
    rank = ids.index(me) + 1
    us = teams[rank - 1]
    other = teams[1] if rank == 1 and len(teams) > 1 else teams[0]
    gap = us["conversion"] - other["conversion"]
    line = (f"#{rank} of {len(teams)}  conv {us['conversion']:.3f}  on_time {us['on_time']:.1f}%  "
            f"{'lead over' if rank == 1 else 'behind'} {other['team_id']} ({other['conversion']:.3f}, "
            f"on_time {other['on_time']:.1f}%) by {abs(gap):.3f}  [{us.get('model_version', '')}]")
    return rank != 1, line


def wait_for_next(s: dict | None, every: float) -> None:
    """Sleep until just after the next board update (at most `every` seconds)."""
    delay = every
    if s and s.get("next_update"):
        delay = s["next_update"] + 30 - time.time()
        delay = max(60.0, min(every, delay))
    time.sleep(delay)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="play the alarm once, at --gain, and exit")
    ap.add_argument("--snooze", type=float, metavar="MIN", help="silence the alarm for MIN minutes and exit")
    ap.add_argument("--every", type=float, default=600, help="seconds between readings at most (default 600)")
    ap.add_argument("--volume", type=float, default=1.0, help="speaker volume while ringing (default 1.0)")
    ap.add_argument("--gain", type=float, default=0.08,
                    help="loudness of the siren itself, 0-1 (default 0.08: the level chosen on 15 Nov)")
    ap.add_argument("--ring", type=float, default=120, help="seconds the alarm rings (default 120)")
    a = ap.parse_args()

    make_sound()
    if a.test:
        play(a.gain)
        return
    if a.snooze is not None:
        SNOOZE.write_text(str(time.time() + a.snooze * 60))
        log(f"alarm snoozed for {a.snooze:g} min")
        return

    me = team_id()
    log(f"watching the board for {me}; alarm if we are not #1")
    failures, s = 0, None
    while True:
        try:
            s = fetch()
            failures = 0
            alarm, line = reading(s, me)
            log(("ALARM  " if alarm else "ok     ") + line)
            if alarm:
                notify("Skore Money: lost first place", line)
                if snoozed():
                    log("snoozed: not ringing")
                else:
                    ring(a.ring, a.volume, a.gain)
        except Exception as e:                            # the watcher must not die
            failures += 1
            log(f"could not read the board ({failures} in a row): {e!r}")
            if failures == 3:
                notify("Skore Money watcher", f"cannot read the leaderboard: {e!r}")
            s = None
        wait_for_next(s, a.every)


if __name__ == "__main__":
    main()
