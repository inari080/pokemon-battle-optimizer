"""
ポケモンチャンピオンズの公開データ取得クライアント。

出典:
  - 上位構築データ(CSV/JSON): champs.pokedb.tokyo
      https://champs.pokedb.tokyo/opendata/s{season}_{single|double}_ranked_teams.{csv|json}
      season は1始まりの連番 (1=M-1, 2=M-2, ...)
  - 技/特性の使用率API: championsbattledata.com
      https://championsbattledata.com/api/pokemon/{showdown_id}?format=Singles

注意:
  このプロジェクトの実行環境からは上記ドメインへの外部アクセスが許可されていない場合があります。
  その場合は手元の環境(ネットワーク制限のないマシン)でこのモジュールを実行し、
  取得したJSON/CSVを data/ 以下にキャッシュしてから他モジュールで読み込んでください。

実データのスキーマ(champs.pokedb.tokyo/opendata形式):
    {
      "season": "M-4", "season_number": 4, "rule": "シングル",
      "teams": [
        {"rank": 1, "rating_value": 2567.3,
         "team": [{"id": "...", "pokemon": "フラエッテ", "form": "...",
                    "type1": "フェアリー", "type2": "", "category": "一般",
                    "terastal": "", "item": "フラエッテナイト"}, ...]},
        ...
      ],
      "updated_at": "..."
    }
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

POKEDB_BASE = "https://champs.pokedb.tokyo/opendata"
BATTLE_DATA_API = "https://championsbattledata.com/api"


def fetch_ranked_teams(season: int, battle_format: str = "single") -> dict[str, Any]:
    """
    上位構築データを取得する。battle_format は "single" or "double"。
    結果は data/cache/ranked_teams_s{season}_{format}.json にキャッシュされる。
    (このファイルが手動で data/cache/ に配置されていれば、そのままキャッシュとして使われる)
    """
    cache_path = CACHE_DIR / f"ranked_teams_s{season}_{battle_format}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    url = f"{POKEDB_BASE}/s{season}_{battle_format}_ranked_teams.json"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def fetch_pokemon_usage(showdown_id: str, battle_format: str = "Singles") -> dict[str, Any]:
    """特定ポケモンの使用率・技/特性データを取得する。"""
    cache_path = CACHE_DIR / f"usage_{showdown_id}_{battle_format}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    url = f"{BATTLE_DATA_API}/pokemon/{showdown_id}"
    resp = requests.get(url, params={"format": battle_format}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def summarize_usage(ranked_teams_data: dict[str, Any], top_n: int = 30) -> list[dict[str, Any]]:
    """
    fetch_ranked_teams() の戻り値(実データスキーマ)からポケモンごとの
    採用回数(使用率の近似)を集計し、上位N体を返す。
    各要素: {"name": ポケモン名, "form": フォルム名, "count": 採用数,
             "usage_weight": 正規化重み, "type1": ..., "type2": ...,
             "items": このポケモンで使われた持ち物の内訳(上位5件)}
    """
    teams = ranked_teams_data.get("teams", [])
    counts: Counter[tuple[str, str]] = Counter()
    types_by_mon: dict[tuple[str, str], tuple[str, str]] = {}
    items_by_mon: dict[tuple[str, str], Counter] = {}

    for team in teams:
        for mon in team.get("team", []):
            name = mon.get("pokemon")
            form = mon.get("form") or ""
            if not name:
                continue
            key = (name, form)
            counts[key] += 1
            types_by_mon[key] = (mon.get("type1", ""), mon.get("type2", ""))
            items_by_mon.setdefault(key, Counter())[mon.get("item", "")] += 1

    ranked = counts.most_common(top_n)
    total = sum(c for _, c in ranked) or 1
    result = []
    for (name, form), count in ranked:
        t1, t2 = types_by_mon[(name, form)]
        top_items = [item for item, _ in items_by_mon[(name, form)].most_common(5) if item]
        result.append({
            "name": name,
            "form": form,
            "count": count,
            "usage_weight": count / total,
            "type1": t1,
            "type2": t2,
            "items": top_items,
        })
    return result

