"""The experiment runner (spec §11.3): evaluate product x config x conversation
x turn, caching every call in SQLite so re-runs are free and drift re-runs are
surgical. Populates a per-turn `scores` table; metrics.py aggregates it.
"""
from __future__ import annotations
import hashlib, json, sqlite3, time, random, pathlib
from dataclasses import asdict
from .schema import Conversation
from . import policies
from .products import registry
from .corpora import base

CACHE_DIR = pathlib.Path(__file__).resolve().parents[1] / "cache"

SCHEMA = """
CREATE TABLE IF NOT EXISTS scores (
  key TEXT PRIMARY KEY, product TEXT, version TEXT, config TEXT,
  corpus TEXT, conv_id TEXT, label TEXT, family TEXT,
  turn INTEGER, n_turns INTEGER, harm_turn INTEGER,
  blocked INTEGER, r REAL, latency_ms REAL, cost_units REAL, coverage REAL,
  ts REAL, raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_pc ON scores(product, config, corpus);
"""


def shard_path(product: str) -> pathlib.Path:
    """Each product writes to its OWN sqlite file, so concurrent runs never
    lock each other. Reads union all shards (see metrics.per_turn_df)."""
    return CACHE_DIR / f"scores_{product}.sqlite"


def all_shards() -> list[pathlib.Path]:
    return sorted(p for p in CACHE_DIR.glob("scores_*.sqlite")
                  if "legacy_backup" not in p.name)


def _db(product: str) -> sqlite3.Connection:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(shard_path(product), timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    # one writer per shard, so WAL is safe here and lets export read concurrently
    if con.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":
        try:
            con.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass
    con.executescript(SCHEMA)
    return con


def _key(product, version, config, conv_id, turn, unit) -> str:
    h = hashlib.sha1(unit.encode("utf-8")).hexdigest()[:12]
    return hashlib.sha1(f"{product}|{version}|{config}|{conv_id}|{turn}|{h}"
                        .encode()).hexdigest()


def _score_with_retry(product, unit, source, tries=4):
    for i in range(tries):
        try:
            return registry.score(product, unit, source)
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(min(2 ** i, 8))
    raise RuntimeError("unreachable")


def run(products, configs, corpora, n=None, max_turns=None, k=3, seed=0,
        source="INPUT", verbose=True):
    rng = random.Random(seed)
    total_calls = cached = 0
    # one shard connection PER PRODUCT -> concurrent product runs never lock
    for product in products:
        con = _db(product)
        ver = registry.version(product)
        for corpus in corpora:
            convs = base.load_normalized(corpus)
            if n:
                rng_c = random.Random(seed)
                rng_c.shuffle(convs)
                convs = convs[:n]
            for conv in convs:
                users = conv.user_turns()
                T = len(users) if not max_turns else min(len(users), max_turns)
                for t in range(1, T + 1):
                    for config in configs:
                        unit = policies.apply(config, users[:t], k)
                        key = _key(product, ver, config, conv.conv_id, t, unit)
                        if con.execute("SELECT 1 FROM scores WHERE key=?", (key,)).fetchone():
                            cached += 1
                            continue
                        s = _score_with_retry(product, unit, source)
                        con.execute(
                            "INSERT OR REPLACE INTO scores VALUES "
                            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (key, product, ver, config, corpus, conv.conv_id,
                             conv.label, conv.family, t, len(users), conv.harm_turn,
                             int(s.blocked), float(s.r), s.latency_ms, s.cost_units,
                             s.coverage if s.coverage is not None else -1.0, time.time(),
                             json.dumps(s.raw, ensure_ascii=False) if s.raw else None))
                        total_calls += 1
                con.commit()
            if verbose:
                print(f"  done {product:20} on {corpus:24} "
                      f"(+{total_calls} new / {cached} cached)")
        con.commit(); con.close()
    return {"new_calls": total_calls, "cached": cached}
