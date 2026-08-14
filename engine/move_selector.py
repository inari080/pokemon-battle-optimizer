"""
対戦中の技選択(その場面での最適な行動)を探索するエンジン。

方式: expectiminimax
  - 各ターンで自分/相手それぞれの行動(技 or 交代)を全列挙
  - 素早さ順に行動を解決し、ダメージは16通りの乱数を「確率分布」のまま扱う
    (乱数のユニーク値ごとに 出現数/16 を確率として分岐するチャンスノード)
  - 相手は「自分にとって最悪(=相手にとって最良)」を選ぶと仮定するミニマックス
  - 指定した深さまで探索し、末端は評価関数でスコア化。チャンスノードでは
    各分岐の評価値を確率で重み付けした期待値を返す

平均値のみで進める簡易版と比べ、「乱数上振れなら倒せる/下振れなら耐える」
といった際どい場面を正しく評価できる。ただし分岐数が増えるため、
既定の深さは2(自分の1手+相手の1手)に抑えている。
深さを増やすほど正確だが指数的に重くなる点に注意。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional

from core.battle_state import BattleState, Side
from core.damage_calc import DamageContext, damage_rolls
from core.models import BattlePokemon, Category, MoveData


@dataclass
class Action:
    kind: str  # "move" or "switch"
    move: Optional[MoveData] = None
    switch_index: Optional[int] = None

    def label(self) -> str:
        if self.kind == "move":
            return f"技: {self.move.name}"
        return f"交代: index={self.switch_index}"


def legal_actions(side: Side) -> list[Action]:
    actions = []
    active = side.active
    if not active.fainted:
        for mv in active.build.moves:
            actions.append(Action(kind="move", move=mv))
    for i in side.alive_indices():
        if i != side.active_index:
            actions.append(Action(kind="switch", switch_index=i))
    return actions


def _evaluate(state: BattleState, my_side: str) -> float:
    """盤面を評価するヒューリスティック(HP割合の差 + 生存数の差 + 素早さ有利)。"""
    a, b = state.side_a, state.side_b
    hp_a = sum(p.hp_fraction() for p in a.party if not p.fainted)
    hp_b = sum(p.hp_fraction() for p in b.party if not p.fainted)
    alive_a = len(a.alive_indices())
    alive_b = len(b.alive_indices())
    score = (hp_a - hp_b) * 10 + (alive_a - alive_b) * 30
    if not a.active.fainted and not b.active.fainted:
        if a.active.effective_stat("spe") > b.active.effective_stat("spe"):
            score += 3
        else:
            score -= 3
    return score if my_side == "A" else -score


def _damage_distribution(
    state: BattleState, attacker: BattlePokemon, defender: BattlePokemon, move: MoveData,
) -> list[tuple[int, float]]:
    """
    (ダメージ量, 確率) のリストを返す。16通りの乱数のうちユニークな値ごとに
    出現数/16を確率として集約するため、分岐数を実質的な種類数まで抑えられる。
    変化技や無効(タイプ相性0倍)の場合は [(0, 1.0)] を返す。
    """
    if attacker.fainted or defender.fainted or move.category == Category.STATUS:
        return [(0, 1.0)]
    rolls = damage_rolls(attacker, defender, move, DamageContext(weather=state.weather, terrain=state.terrain))
    counts = Counter(rolls)
    total = len(rolls)
    return [(dmg, cnt / total) for dmg, cnt in counts.items()]


def _resolve_turn_distribution(
    state: BattleState, action_a: Action, action_b: Action,
) -> list[tuple[float, BattleState]]:
    """
    1ターン分の行動を解決し、(確率, 結果として起こりうる盤面) のリストを返す。
    ダメージ乱数をチャンスノードとして分岐させるため、通常は複数の盤面が返る。
    """
    base = state.light_clone()
    a, b = base.side_a, base.side_b

    # 交代は技より先に、かつ確定的に処理する
    if action_a.kind == "switch":
        a.active_index = action_a.switch_index
    if action_b.kind == "switch":
        b.active_index = action_b.switch_index

    movers = []
    if action_a.kind == "move" and action_a.move is not None:
        movers.append(("A", action_a.move))
    if action_b.kind == "move" and action_b.move is not None:
        movers.append(("B", action_b.move))

    def speed_key(item):
        side_label, mv = item
        side = a if side_label == "A" else b
        priority = mv.priority
        spe = side.active.effective_stat("spe")
        return (-priority, -spe)

    movers.sort(key=speed_key)

    branches: list[tuple[float, BattleState]] = [(1.0, base)]

    for side_label, mv in movers:
        next_branches: list[tuple[float, BattleState]] = []
        for prob, br_state in branches:
            atk_side = br_state.side_a if side_label == "A" else br_state.side_b
            def_side = br_state.side_b if side_label == "A" else br_state.side_a
            attacker = atk_side.active
            defender = def_side.active
            if attacker.fainted:
                next_branches.append((prob, br_state))
                continue
            dist = _damage_distribution(br_state, attacker, defender, mv)
            if len(dist) == 1:
                dmg, _ = dist[0]
                if dmg:
                    defender.apply_damage(dmg)
                next_branches.append((prob, br_state))
            else:
                for dmg, dmg_prob in dist:
                    child = br_state.light_clone()
                    child_def_side = child.side_b if side_label == "A" else child.side_a
                    if dmg:
                        child_def_side.active.apply_damage(dmg)
                    next_branches.append((prob * dmg_prob, child))
        branches = next_branches

    for _, br_state in branches:
        br_state.turn += 1

    return branches


def expectiminimax(state: BattleState, depth: int, my_side: str) -> tuple[float, Optional[Action]]:
    """my_side ("A" or "B") にとっての最適行動と評価値を返す。"""
    if depth == 0 or state.is_over():
        return _evaluate(state, my_side), None

    a_actions = legal_actions(state.side_a) or [Action(kind="move", move=None)]
    b_actions = legal_actions(state.side_b) or [Action(kind="move", move=None)]

    best_score = None
    best_action = None

    # my_side視点で最大化、相手視点で最小化(相手も最適に動くと仮定)
    my_actions = a_actions if my_side == "A" else b_actions
    opp_actions = b_actions if my_side == "A" else a_actions

    for my_act in my_actions:
        worst_for_me = None
        for opp_act in opp_actions:
            if my_side == "A":
                branches = _resolve_turn_distribution(state, my_act, opp_act)
            else:
                branches = _resolve_turn_distribution(state, opp_act, my_act)
            # チャンスノード: 乱数分岐ごとの評価値を確率で重み付けした期待値
            expected_score = 0.0
            for prob, child in branches:
                score, _ = expectiminimax(child, depth - 1, my_side)
                expected_score += prob * score
            if worst_for_me is None or expected_score < worst_for_me:
                worst_for_me = expected_score
        if best_score is None or worst_for_me > best_score:
            best_score = worst_for_me
            best_action = my_act

    return best_score, best_action


def best_action_for_active_matchup(state: BattleState, my_side: str = "A", depth: int = 2):
    """現在の場面での最適な行動を1つ返す(表示用の簡易ラッパー)。"""
    score, action = expectiminimax(state, depth, my_side)
    return score, action
