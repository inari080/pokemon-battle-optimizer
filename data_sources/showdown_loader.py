"""
data/cache/species.json, data/cache/moves.json (parse_showdown_data.py の出力)を
core.models の Species / MoveData に変換するローダー。

英語名/showdown内部ID(garchomp等)の両方から引けるようにする。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.models import BaseStats, MoveData, Species, Type

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"

_TYPE_BY_VALUE = {t.value: t for t in Type}


def _to_type(ja_name: str) -> Type:
    return _TYPE_BY_VALUE.get(ja_name, Type.NONE)


@lru_cache(maxsize=1)
def _raw_species() -> dict:
    path = CACHE_DIR / "species.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} が見つかりません。先に `python parse_showdown_data.py` を実行してください。"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _raw_moves() -> dict:
    path = CACHE_DIR / "moves.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} が見つかりません。先に `python parse_showdown_data.py` を実行してください。"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _name_index() -> dict[str, str]:
    """英語表示名(小文字化・ハイフン除去) -> showdown内部ID の索引。"""
    idx = {}
    for key, data in _raw_species().items():
        norm = data["name"].lower().replace("-", "").replace(" ", "")
        idx[norm] = key
    return idx


def _species_from_raw(key: str, data: dict) -> Species:
    bs = data["base_stats"]
    return Species(
        name=data["name"],
        types=tuple(_to_type(t) for t in data["types"]),
        base_stats=BaseStats(hp=bs["hp"], atk=bs["atk"], dfn=bs["def"], spa=bs["spa"], spd=bs["spd"], spe=bs["spe"]),
        abilities=tuple(data["abilities"]),
        mega_form_of=data.get("base_species") if data.get("is_mega") else None,
    )


def get_species(name_or_id: str) -> Species:
    """
    表示名(例: "Garchomp", "ガブリアス" は非対応、英語表記のみ) または
    showdown内部ID(例: "garchomp", "garchompmega") から Species を取得する。
    """
    raw = _raw_species()
    if name_or_id in raw:
        return _species_from_raw(name_or_id, raw[name_or_id])
    norm = name_or_id.lower().replace("-", "").replace(" ", "")
    key = _name_index().get(norm)
    if key:
        return _species_from_raw(key, raw[key])
    raise KeyError(f"種族データが見つかりません: {name_or_id}")


def _move_from_raw(data: dict) -> MoveData:
    from core.models import Category
    cat_map = {"物理": Category.PHYSICAL, "特殊": Category.SPECIAL, "変化": Category.STATUS}
    return MoveData(
        name=data["name"],
        type=_to_type(data["type"]),
        category=cat_map.get(data["category"], Category.STATUS),
        power=data["power"],
        accuracy=data["accuracy"],
        priority=data["priority"],
        pp=data["pp"],
    )


@lru_cache(maxsize=1)
def _move_name_index() -> dict[str, str]:
    idx = {}
    for key, data in _raw_moves().items():
        norm = data["name"].lower().replace("-", "").replace(" ", "")
        idx[norm] = key
    return idx


def get_move(name_or_id: str) -> MoveData:
    """表示名(英語)または showdown内部ID(例: "earthquake") から MoveData を取得する。"""
    raw = _raw_moves()
    if name_or_id in raw:
        return _move_from_raw(raw[name_or_id])
    norm = name_or_id.lower().replace("-", "").replace(" ", "")
    key = _move_name_index().get(norm)
    if key:
        return _move_from_raw(raw[key])
    raise KeyError(f"技データが見つかりません: {name_or_id}")


def list_species_names() -> list[str]:
    return [d["name"] for d in _raw_species().values()]


def list_move_names() -> list[str]:
    return [d["name"] for d in _raw_moves().values()]
