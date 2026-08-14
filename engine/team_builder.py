"""
パーティ構築(選出・型)の最適化。

厳密な全探索は候補ポケモン数に対して組合せ爆発するため、
「環境の脅威リスト(使用率上位+その技構成)」に対するスコアリング関数を定義し、
貪欲法+局所探索(2体入れ替えの山登り法)で近似最適なパーティを求める。

スコア関数の要素:
  - 対応力: 候補パーティのいずれかが各脅威に対して有利なダメージ交換ができるか
  - 弱点の重複回避: パーティ全体で同じタイプに対して弱点が集中しないか
  - 打点(技範囲)の広さ: 全体で等倍以上を取れるタイプがどれだけ多いか
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from core.models import PokemonBuild, Team, Type
from core.type_chart import type_effectiveness


@dataclass
class Threat:
    """環境の脅威(使用率上位ポケモン)を表す簡易モデル。"""

    name: str
    types: tuple[Type, ...]
    move_types: tuple[Type, ...]  # 主要な打点のタイプ
    usage_weight: float = 1.0  # 使用率などに基づく重み


def _defensive_score(build: PokemonBuild, threats: list[Threat]) -> float:
    """このポケモンが受けに立てるかを脅威リストに対して評価する。"""
    score = 0.0
    for t in threats:
        worst = 1.0
        for mt in t.move_types:
            mult = type_effectiveness(mt, build.species.types)
            worst = max(worst, mult)
        # 弱点(2倍以上)ならマイナス、耐性(0.5以下)ならプラス
        if worst >= 2.0:
            score -= t.usage_weight * (worst)
        elif worst <= 0.5:
            score += t.usage_weight * 1.0
    return score


def _offensive_score(build: PokemonBuild, threats: list[Threat]) -> float:
    """このポケモンの技(タイプ)が脅威にどれだけ通るかを評価する。"""
    score = 0.0
    my_types = build.species.types
    for t in threats:
        best = 0.0
        for mt in my_types:  # 技タイプの詳細が無い場合は自タイプで近似
            mult = type_effectiveness(mt, t.types)
            best = max(best, mult)
        if best >= 2.0:
            score += t.usage_weight * 1.0
        elif best <= 0.5:
            score -= t.usage_weight * 0.5
    return score


def team_score(members: list[PokemonBuild], threats: list[Threat]) -> float:
    if not members:
        return float("-inf")
    total = 0.0
    for m in members:
        total += _defensive_score(m, threats) + _offensive_score(m, threats)

    # 弱点の重複ペナルティ: 同じタイプへの弱点(2倍以上)を持つ数が多いほど減点
    weak_counts: dict[Type, int] = {}
    for m in members:
        for atk_type in Type:
            if atk_type == Type.NONE:
                continue
            if type_effectiveness(atk_type, m.species.types) >= 2.0:
                weak_counts[atk_type] = weak_counts.get(atk_type, 0) + 1
    overlap_penalty = sum(max(0, c - 1) ** 1.5 for c in weak_counts.values())
    total -= overlap_penalty * 2.0

    return total


def build_team_greedy(
    candidates: list[PokemonBuild],
    threats: list[Threat],
    team_size: int = 6,
    random_restarts: int = 20,
    local_search_iters: int = 200,
    seed: int | None = None,
) -> Team:
    """
    貪欲法で初期パーティを組み、その後2体入れ替えの山登り法で改善する。
    random_restarts回だけ初期選出の乱数シードを変えて最良解を採用する。
    """
    rng = random.Random(seed)
    best_team: list[PokemonBuild] | None = None
    best_score = float("-inf")

    for _ in range(max(1, random_restarts)):
        pool = candidates[:]
        rng.shuffle(pool)
        chosen: list[PokemonBuild] = []
        remaining = pool[:]

        # 貪欲法: 現在の暫定パーティに追加したときのスコア増分が最大の1体を毎回選ぶ
        while len(chosen) < team_size and remaining:
            best_add = None
            best_add_score = None
            for cand in remaining:
                trial = chosen + [cand]
                s = team_score(trial, threats)
                if best_add_score is None or s > best_add_score:
                    best_add_score = s
                    best_add = cand
            chosen.append(best_add)
            remaining.remove(best_add)

        # 局所探索: パーティ内の1体を候補プールの別の1体と入れ替えて改善するか試す
        current_score = team_score(chosen, threats)
        for _ in range(local_search_iters):
            if len(chosen) < team_size or not remaining:
                break
            i = rng.randrange(len(chosen))
            j = rng.randrange(len(remaining))
            trial = chosen[:]
            trial[i] = remaining[j]
            s = team_score(trial, threats)
            if s > current_score:
                remaining[j] = chosen[i]
                chosen = trial
                current_score = s

        if current_score > best_score:
            best_score = current_score
            best_team = chosen

    return Team(name=f"最適化パーティ(score={best_score:.1f})", members=best_team or [])
