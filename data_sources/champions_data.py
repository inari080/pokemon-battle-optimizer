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
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

POKEDB_BASE = "https://champs.pokedb.tokyo/opendata"
BATTLE_DATA_API = "https://championsbattledata.com/api"


def fetch_ranked_teams(season: int, battle_format: str = "single") -> list[dict[str, Any]]:
    """
    上位構築データを取得する。battle_format は "single" or "double"。
    結果は data/cache/ranked_teams_s{season}_{format}.json にキャッシュされる。
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


def build_threat_list_from_ranked_teams(
    teams: list[dict[str, Any]],
    top_n: int = 15,
) -> list[dict[str, Any]]:
    """
    上位構築データからポケモンごとの採用回数を集計し、使用率上位N体を
    team_builder.Threat 生成用の簡易辞書リストとして返す。
    (テラスタイプ・持ち物までは集計するが、技構成は含まないため
     Threat.move_types は呼び出し側で別途 pchamdb 等から補完すること)
    """
    counts: dict[str, int] = {}
    for team in teams:
        for mon in team.get("pokemon", []):
            name = mon.get("name") or mon.get("species")
            if not name:
                continue
            counts[name] = counts.get(name, 0) + 1

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    total = sum(c for _, c in ranked) or 1
    return [{"name": name, "usage_weight": count / total} for name, count in ranked]
