"""
Pokemon Showdown (smogon/pokemon-showdown, MIT License) の
data/pokedex.ts / data/moves.ts をパースしてJSON化するスクリプト。

出典: https://github.com/smogon/pokemon-showdown
      data/pokedex.ts, data/moves.ts

TypeScriptのオブジェクトリテラルを厳密にパースするのではなく、
各エントリのブロック単位でフィールドを正規表現抽出する簡易パーサー。
関数プロパティ(basePowerCallback等)を含む複雑なエントリはスキップ、
または該当フィールドのみ欠損として扱う。

実行方法:
    python parse_showdown_data.py
出力:
    data/cache/species.json   (種族データ: 名前・タイプ・種族値・特性)
    data/cache/moves.json     (技データ: タイプ・分類・威力・命中・優先度・PP)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"
CACHE_DIR = Path(__file__).resolve().parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 日本語のタイプ名への変換(core.models.Type の値と一致させる)
TYPE_JA = {
    "Normal": "ノーマル", "Fire": "ほのお", "Water": "みず", "Electric": "でんき",
    "Grass": "くさ", "Ice": "こおり", "Fighting": "かくとう", "Poison": "どく",
    "Ground": "じめん", "Flying": "ひこう", "Psychic": "エスパー", "Bug": "むし",
    "Rock": "いわ", "Ghost": "ゴースト", "Dragon": "ドラゴン", "Dark": "あく",
    "Steel": "はがね", "Fairy": "フェアリー", "???": "なし", "Stellar": "なし",
}

CATEGORY_JA = {"Physical": "物理", "Special": "特殊", "Status": "変化"}


def _split_top_level_entries(text: str) -> list[tuple[str, str]]:
    """
    `key: {...},` 形式のトップレベルエントリを (key, body) のリストとして分割する。
    ネストした波括弧の対応を数えて正しくブロック終端を判定する。
    """
    entries = []
    i = 0
    n = len(text)
    key_pattern = re.compile(r'\n\t([A-Za-z0-9_]+):\s*\{')
    for m in key_pattern.finditer(text):
        key = m.group(1)
        start = m.end() - 1  # '{' の位置
        depth = 0
        j = start
        while j < n:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = text[start:j + 1]
        entries.append((key, body))
    return entries


def _extract_field(body: str, field: str) -> str | None:
    m = re.search(rf'\b{field}:\s*"([^"]*)"', body)
    if m:
        return m.group(1)
    m = re.search(rf'\b{field}:\s*(-?\d+)', body)
    if m:
        return m.group(1)
    return None


def parse_pokedex(limit: int | None = None) -> dict:
    text = (RAW_DIR / "pokedex.ts").read_text(encoding="utf-8")
    entries = _split_top_level_entries(text)
    result = {}
    for i, (key, body) in enumerate(entries):
        if limit and i >= limit:
            break
        name_m = re.search(r'name:\s*"([^"]*)"', body)
        types_m = re.search(r'types:\s*\[([^\]]*)\]', body)
        stats_m = re.search(
            r'baseStats:\s*\{\s*hp:\s*(\d+),\s*atk:\s*(\d+),\s*def:\s*(\d+),'
            r'\s*spa:\s*(\d+),\s*spd:\s*(\d+),\s*spe:\s*(\d+)\s*\}',
            body,
        )
        abilities_m = re.search(r'abilities:\s*\{([^}]*)\}', body)
        base_species_m = re.search(r'baseSpecies:\s*"([^"]*)"', body)
        forme_m = re.search(r'\bforme:\s*"([^"]*)"', body)
        required_item_m = re.search(r'requiredItem:\s*"([^"]*)"', body)

        if not (name_m and types_m and stats_m):
            continue

        types_raw = [t.strip().strip('"') for t in types_m.group(1).split(",") if t.strip()]
        types_ja = [TYPE_JA.get(t, t) for t in types_raw]

        abilities = []
        if abilities_m:
            for am in re.finditer(r'"([^"]*)"', abilities_m.group(1)):
                abilities.append(am.group(1))

        result[key] = {
            "name": name_m.group(1),
            "types": types_ja,
            "base_stats": {
                "hp": int(stats_m.group(1)), "atk": int(stats_m.group(2)),
                "def": int(stats_m.group(3)), "spa": int(stats_m.group(4)),
                "spd": int(stats_m.group(5)), "spe": int(stats_m.group(6)),
            },
            "abilities": abilities,
            "base_species": base_species_m.group(1) if base_species_m else None,
            "forme": forme_m.group(1) if forme_m else None,
            "is_mega": bool(forme_m and "Mega" in forme_m.group(1)),
            "required_item": required_item_m.group(1) if required_item_m else None,
        }
    return result


def parse_moves(limit: int | None = None) -> dict:
    text = (RAW_DIR / "moves.ts").read_text(encoding="utf-8")
    entries = _split_top_level_entries(text)
    result = {}
    for i, (key, body) in enumerate(entries):
        if limit and i >= limit:
            break
        name_m = re.search(r'name:\s*"([^"]*)"', body)
        type_m = re.search(r'\btype:\s*"([^"]*)"', body)
        category_m = re.search(r'category:\s*"([^"]*)"', body)
        power_m = re.search(r'basePower:\s*(-?\d+)', body)
        accuracy_m = re.search(r'accuracy:\s*(true|-?\d+)', body)
        priority_m = re.search(r'priority:\s*(-?\d+)', body)
        pp_m = re.search(r'\bpp:\s*(\d+)', body)

        if not (name_m and type_m and category_m):
            continue

        accuracy = None
        if accuracy_m and accuracy_m.group(1) != "true":
            accuracy = int(accuracy_m.group(1))

        result[key] = {
            "name": name_m.group(1),
            "type": TYPE_JA.get(type_m.group(1), type_m.group(1)),
            "category": CATEGORY_JA.get(category_m.group(1), category_m.group(1)),
            "power": int(power_m.group(1)) if power_m else 0,
            "accuracy": accuracy,
            "priority": int(priority_m.group(1)) if priority_m else 0,
            "pp": int(pp_m.group(1)) if pp_m else 0,
        }
    return result


if __name__ == "__main__":
    species = parse_pokedex()
    moves = parse_moves()
    (CACHE_DIR / "species.json").write_text(
        json.dumps(species, ensure_ascii=False, indent=1), encoding="utf-8")
    (CACHE_DIR / "moves.json").write_text(
        json.dumps(moves, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"species: {len(species)}件 -> data/cache/species.json")
    print(f"moves:   {len(moves)}件 -> data/cache/moves.json")
