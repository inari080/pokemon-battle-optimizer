"""
ポケモンチャンピオンズ シーズンM-4(シングル)の実際の上位構築データを使った
パーティ最適化デモ。

データソース: champs.pokedb.tokyo の公開データ(data/cache/ranked_teams_s4_single.json)
             221チーム分の上位ランカー構築(2026-08-13時点)

実行方法:
    PYTHONPATH=. python3 demo_real_meta.py
"""
from __future__ import annotations

from data_sources.champions_data import fetch_ranked_teams, summarize_usage
from data_sources.threat_builder import build_candidates_from_champions_usage, build_threats_from_champions_usage
from engine.team_builder import build_team_greedy, team_score

SEASON = 4
BATTLE_FORMAT = "single"
TOP_N = 40  # 使用率上位何体を候補・脅威リストに含めるか


def main() -> None:
    data = fetch_ranked_teams(SEASON, BATTLE_FORMAT)
    print(f"シーズン: {data.get('season')}  ルール: {data.get('rule')}  "
          f"集計チーム数: {len(data.get('teams', []))}  更新日時: {data.get('updated_at')}")
    print()

    usage = summarize_usage(data, top_n=TOP_N)
    print(f"=== 使用率トップ{min(10, TOP_N)} ===")
    for u in usage[:10]:
        form = f"({u['form']})" if u["form"] else ""
        print(f"  {u['count']:4d}件 ({u['usage_weight']*100:5.1f}%)  {u['name']}{form}"
              f"  [{u['type1']}/{u['type2'] or '-'}]")
    print()

    threats = build_threats_from_champions_usage(usage)
    candidates = build_candidates_from_champions_usage(usage)

    team = build_team_greedy(
        candidates, threats, team_size=6,
        random_restarts=20, local_search_iters=200, seed=7,
    )
    print(f"=== 環境上位{TOP_N}体を踏まえた最適化パーティ(6体) ===")
    for m in team.members:
        t1, t2 = m.species.types[0].value, (m.species.types[1].value if len(m.species.types) > 1 else "-")
        print(f"  {m.species.name}  [{t1}/{t2}]")
    print(f"スコア: {team_score(team.members, threats):.2f}")


if __name__ == "__main__":
    main()
