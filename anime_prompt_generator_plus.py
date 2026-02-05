#!/usr/bin/env python3
"""
Wrapper for anime_prompt_generator_v6_5_1.py that provides a stable GUI API:

- set_data_dir(path): overrides base.get_data_path() to point to user-selected folder
- data_audit(): Found vs Used (referenced in generator source) vs Unused (.txt in data folder)
- Auto-append extra pools: append tags from UNUSED files with per-file probability sliders
- list_genres(): derived from GENRE_WEIGHTS (since base has no list_genres)

Compatible with generator versions that expose:
- generate_prompt(...)
- GENRE_WEIGHTS (dict)
- get_data_path() used by load_list()

This wrapper does NOT modify the base generator logic; it adds extra pools optionally.
"""

from __future__ import annotations

import os
import sys
import random
import re

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TypedDict

import anime_prompt_generator_v6_5_1 as base


def _default_data_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "data")  # type: ignore[attr-defined]
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


_DATA_DIR: str = _default_data_dir()
DATA_DIR: str = _DATA_DIR  # back-compat


def get_data_dir() -> str:
    return _DATA_DIR


def set_data_dir(path: str) -> None:
    global _DATA_DIR, DATA_DIR
    _DATA_DIR = path
    DATA_DIR = path

    # Make base load from our chosen folder
    if hasattr(base, "get_data_path"):
        def _patched_get_data_path() -> str:
            return _DATA_DIR
        base.get_data_path = _patched_get_data_path  # type: ignore

    # Refresh extra pools if the loader is available
    if "_reload_extra_pools" in globals():
        try:
            _reload_extra_pools()
        except Exception:
            pass


# Apply once at import time so it works even before the GUI calls Reload
set_data_dir(_DATA_DIR)


class DataAudit(TypedDict):
    data_dir: str
    found_count: int
    used_count: int
    unused_count: int
    found: List[str]
    used: List[str]
    unused: List[str]

# ---- audit ----
def _scan_used_txt_filenames() -> List[str]:
    try:
        src_path = base.__file__
        with open(src_path, "r", encoding="utf-8") as f:
            src = f.read()
    except Exception:
        return []
    return sorted(set(re.findall(r'["\\\']([A-Za-z0-9_\-]+\.txt)["\\\']', src)))

def _scan_found_txt_filenames(data_dir: str) -> List[str]:
    try:
        return sorted([n for n in os.listdir(data_dir) if n.lower().endswith(".txt")])
    except FileNotFoundError:
        return []

def data_audit(data_dir: Optional[str] = None) -> DataAudit:
    d = data_dir or _DATA_DIR
    found = _scan_found_txt_filenames(d)
    used = sorted(set(found).intersection(_scan_used_txt_filenames()))
    unused = sorted(set(found) - set(used))
    return {
        "data_dir": d,
        "found_count": len(found),
        "used_count": len(used),
        "unused_count": len(unused),
        "found": found,
        "used": used,
        "unused": unused,
    }


# ---- extra pools ----
_EXTRA_POOLS: Dict[str, List[str]] = {}  # filename -> items (unused only)

def _load_list_file(data_dir: str, filename: str) -> List[str]:
    path = os.path.join(data_dir, filename)
    out: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                out.append(s)
    except FileNotFoundError:
        pass
    return out

def _reload_extra_pools() -> None:
    global _EXTRA_POOLS
    audit = data_audit(_DATA_DIR)
    pools: Dict[str, List[str]] = {}
    for fn in audit["unused"]:
        items = _load_list_file(_DATA_DIR, fn)
        if items:
            pools[fn] = items
    _EXTRA_POOLS = pools

def list_extra_pool_files() -> List[str]:
    return sorted(_EXTRA_POOLS.keys())


@dataclass
class ExtraPoolsTuning:
    enabled: bool = False
    master_prob: float = 0.35
    max_extra_tags: int = 2
    per_file_prob: Dict[str, float] = field(default_factory=dict)  # fn -> 0..1


def _dedupe_csv(prompt: str) -> str:
    parts = [p.strip() for p in prompt.split(",") if p.strip()]
    seen = set()
    out = []
    for p in parts:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return ", ".join(out)

def _append_extra_pools(prompt: str, tuning: ExtraPoolsTuning) -> str:
    if not tuning.enabled or not _EXTRA_POOLS:
        return prompt
    if random.random() > max(0.0, min(1.0, tuning.master_prob)):
        return prompt

    candidates: List[str] = []
    for fn in _EXTRA_POOLS.keys():
        p = float(tuning.per_file_prob.get(fn, 0.0) or 0.0)
        if p <= 0:
            continue
        if random.random() < max(0.0, min(1.0, p)):
            candidates.append(fn)

    if not candidates:
        return prompt

    k = max(1, int(tuning.max_extra_tags))
    k = min(k, len(candidates))
    chosen_files = random.sample(candidates, k=k)

    extras: List[str] = []
    for fn in chosen_files:
        items = _EXTRA_POOLS.get(fn, [])
        if items:
            extras.append(random.choice(items))

    if not extras:
        return prompt

    combined = prompt + ", " + ", ".join(extras)
    # Prefer base.clean_prompt if it exists
    if hasattr(base, "clean_prompt"):
        try:
            return base.clean_prompt(combined)
        except Exception:
            return _dedupe_csv(combined)
    return _dedupe_csv(combined)


# ---- genres ----
def list_genres():
    gw = getattr(base, "GENRE_WEIGHTS", {})
    out = []
    for name, cfg in gw.items():
        out.append({
            "name": name,
            "is_ecchi": "yes" if bool(cfg.get("is_ecchi", False)) else "no",
            "mood": str(cfg.get("mood", "")),
        })
    out.sort(key=lambda x: (0 if x["is_ecchi"] == "no" else 1, x["name"]))
    return out


# ---- generator passthrough ----
def generate_prompt(
    genre: str = "random",
    seed: Optional[int] = None,
    extra_words: str = "",
    distance_preset: str = "random",
    force_1girl: bool = False,
    quality_preset: str = "ultra",
    extra_pools_tuning: Optional[ExtraPoolsTuning] = None,
) -> str:
    if seed is not None:
        random.seed(int(seed))

    prompt = base.generate_prompt(
        genre=genre,
        seed=seed,
        extra_words=extra_words,
        distance_preset=distance_preset,
        force_1girl=force_1girl,
        quality_preset=quality_preset,
    )

    tuning = extra_pools_tuning or ExtraPoolsTuning()
    prompt = _append_extra_pools(prompt, tuning)
    return prompt


# Init
_reload_extra_pools()

if __name__ == "__main__":
    print(generate_prompt())
