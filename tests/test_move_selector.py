from core.battle_state import BattleState, Side
from core.models import BaseStats, Category, MoveData, PokemonBuild, Species, Type
from engine.move_selector import (
    Action,
    _damage_distribution,
    _resolve_turn_distribution,
    best_action_for_active_matchup,
)

ATTACKER_MON = Species(
    name="テストこうげき",
    types=(Type.FIRE,),
    base_stats=BaseStats(hp=100, atk=120, dfn=80, spa=60, spd=80, spe=90),
    abilities=("がんじょう",),
)
DEFENDER_MON = Species(
    name="テストぼうぎょ",
    types=(Type.GRASS,),
    base_stats=BaseStats(hp=100, atk=60, dfn=80, spa=60, spd=80, spe=70),
    abilities=("がんじょう",),
)

FLAME_KICK = MoveData(name="ほのおのキック", type=Type.FIRE, category=Category.PHYSICAL, power=80, accuracy=100)
STATUS_MOVE = MoveData(name="なきごえ", type=Type.NORMAL, category=Category.STATUS, power=0, accuracy=None)


def _build(species, moves):
    return PokemonBuild(species=species, moves=moves)


def test_damage_distribution_probabilities_sum_to_one():
    from core.battle_state import Side as _Side
    side_a = _Side.from_builds([_build(ATTACKER_MON, (FLAME_KICK,))])
    side_b = _Side.from_builds([_build(DEFENDER_MON, (STATUS_MOVE,))])
    state = BattleState(side_a=side_a, side_b=side_b)
    dist = _damage_distribution(state, side_a.active, side_b.active, FLAME_KICK)
    total_prob = sum(p for _, p in dist)
    assert abs(total_prob - 1.0) < 1e-9
    # 超効果的技なので複数の乱数値(=分岐)が存在するはず
    assert len(dist) > 1


def test_status_move_has_single_branch():
    side_a = _mk_side(ATTACKER_MON, (STATUS_MOVE,))
    side_b = _mk_side(DEFENDER_MON, (STATUS_MOVE,))
    state = BattleState(side_a=side_a, side_b=side_b)
    dist = _damage_distribution(state, side_a.active, side_b.active, STATUS_MOVE)
    assert dist == [(0, 1.0)]


def _mk_side(species, moves):
    return Side.from_builds([_build(species, moves)])


def test_resolve_turn_distribution_probabilities_sum_to_one():
    side_a = _mk_side(ATTACKER_MON, (FLAME_KICK,))
    side_b = _mk_side(DEFENDER_MON, (STATUS_MOVE,))
    state = BattleState(side_a=side_a, side_b=side_b)
    action_a = Action(kind="move", move=FLAME_KICK)
    action_b = Action(kind="move", move=STATUS_MOVE)
    branches = _resolve_turn_distribution(state, action_a, action_b)
    total_prob = sum(p for p, _ in branches)
    assert abs(total_prob - 1.0) < 1e-9
    # 元の状態は変更されない(軽量クローンが独立していること)
    assert state.side_b.active.current_hp == state.side_b.active.max_hp


def test_best_action_picks_super_effective_move():
    dragon_pretend = MoveData(name="つの", type=Type.NORMAL, category=Category.PHYSICAL, power=40, accuracy=100)
    attacker_build = _build(ATTACKER_MON, (FLAME_KICK, dragon_pretend))
    defender_build = _build(DEFENDER_MON, (STATUS_MOVE,))
    side_a = Side.from_builds([attacker_build])
    side_b = Side.from_builds([defender_build])
    state = BattleState(side_a=side_a, side_b=side_b)
    score, action = best_action_for_active_matchup(state, my_side="A", depth=1)
    assert action is not None
    assert action.move.name == "ほのおのキック"  # くさに効果抜群な方を選ぶはず
