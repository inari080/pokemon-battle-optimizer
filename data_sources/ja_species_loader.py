"""
日本語名でのポケモン種族データを core.models.Species に変換するローダー。

出典: kotofurumiya/pokemon_data (GitHub, データ元は個人によるポケモン徹底攻略/PokeAPI等からの
      手動入力とされる。誤りが含まれる可能性がある点に留意)
      https://github.com/kotofurumiya/pokemon_data
      https://raw.githubusercontent.com/kotofurumiya/pokemon_data/master/data/pokemon_data.json

ポケモンチャンピオンズの上位構築データ(champions_data.py)は日本語名なので、
showdown_loader(英語名ベース)を経由せずこちらで直接名前引きできる。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.models import BaseStats, Species, Type

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "pokemon_data_ja.json"

_TYPE_BY_JA = {t.value: t for t in Type}


@lru_cache(maxsize=1)
def _raw() -> list[dict]:
    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"{RAW_PATH} が見つかりません。"
            "raw.githubusercontent.com/kotofurumiya/pokemon_data/master/data/pokemon_data.json "
            "を取得して data/raw/pokemon_data_ja.json に保存してください。"
        )
    return json.loads(RAW_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _index() -> dict[tuple[str, str], dict]:
    """(名前, フォルム) -> 生データ の索引。フォルム省略時は "" とマッチする。"""
    idx = {}
    for entry in _raw():
        idx[(entry["name"], entry.get("form", ""))] = entry
    return idx


def _to_species(entry: dict) -> Species:
    types = tuple(_TYPE_BY_JA.get(t, Type.NONE) for t in entry["types"])
    s = entry["stats"]
    return Species(
        name=entry["name"] + (f"({entry['form']})" if entry.get("form") else ""),
        types=types,
        base_stats=BaseStats(
            hp=s["hp"], atk=s["attack"], dfn=s["defence"],
            spa=s["spAttack"], spd=s["spDefence"], spe=s["speed"],
        ),
        abilities=tuple(entry.get("abilities", [])) + tuple(entry.get("hiddenAbilities", [])),
        mega_form_of=None,
    )


def get_species_ja(name: str, form: str = "") -> Species:
    """
    日本語名(例: "ガブリアス")とフォルム名(例: "ヒスイのすがた"、省略可)から Species を取得する。
    フォルム指定が無くデータ側にフォルム違いしか無い場合は、フォルム無しの標準形を優先する。
    """
    idx = _index()
    key = (name, form)
    if key in idx:
        return _to_species(idx[key])
    # フォルム指定が無い場合のフォールバック: 同名の最初のエントリ(通常は無印フォルム)
    if form == "":
        for (n, _f), entry in idx.items():
            if n == name:
                return _to_species(entry)
    raise KeyError(f"種族データが見つかりません: {name}({form})")


def try_get_species_ja(name: str, form: str = "") -> Species | None:
    try:
        return get_species_ja(name, form)
    except KeyError:
        return None
