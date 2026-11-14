# Skore Money · RawTree real-time recommendation challenge

**Datathon FME 2026 · 14–15 November · UPC Barcelona** — team `team_06` (Hugo Juanola, Javier Aranda).

Shoppers arrive at an online store about three times per second. For each one we have 3 seconds to choose
the 10 products they will see; a hidden model simulates whether they click and buy. Everything — requests,
answers, feedback, history — lives in [RawTree](https://rawtree.com), Tinybird's schema-free analytics database.

- Challenge page: <https://datathon.rawtree.dev> · Leaderboard: <https://datathon.rawtree.dev/leaderboard>
- Official starter kit: <https://github.com/rawtreedb/datathon-fme-2026>

## Repository map

| Path | What |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Entry point for AI agents and newcomers: mission, deadlines, rules, commands |
| [`docs/challenge.md`](docs/challenge.md) | Rules, timeline and scoring |
| [`docs/data.md`](docs/data.md) | Data dictionary and measured profile of every table |
| [`docs/rawtree.md`](docs/rawtree.md) | RawTree cheat sheet |
| [`docs/event.md`](docs/event.md) | Team, links and event schedule |
| [`docs/sources/`](docs/sources/README.md) | Official material, verbatim |
| [`starter/`](starter/) | Official starter kit (baseline recommender, SQL examples, offline evaluation notebook) |
| [`scripts/`](scripts/) | `rt.py` (SQL from the shell) and `leaderboard.py` |

## Quick start

```bash
cp .env.example .env     # fill in TEAM_ID and RAWTREE_API_KEY — never commit this file

python3 scripts/rt.py "SELECT count() FROM shop.requests"     # query RawTree
python3 scripts/leaderboard.py                                # public leaderboard
uv run --with requests python starter/recommender.py          # run the baseline against the live stream
```

## Key dates (Barcelona time)

- **Sat 10:00 → Sun 10:00** — practice round, public leaderboard, does not count.
- **Sun 10:00 → 12:00** — final round, the only scored window.
- **Sun 14:00** — presentation and demo to the jury.
