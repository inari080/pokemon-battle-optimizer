"""
実データ(Pokemon Showdown由来、data/cache/species.json・moves.json)を使った動作確認スクリプト。

事前準備:
    python parse_showdown_data.py   # data/raw/*.ts -> data/cache/*.json を生成(初回のみ)

実行方法:
    PYTHONPATH=. python3 demo.py

内容:
  1) ダメージ計算
  2) 対戦中の最適な技選択(expectiminimax)
  3) パーティ構築の最適化(貪欲法+局所探索)
"""
from __future__ import annotations

from core.battle_state import BattleState, Side
from core.damage_calc import DamageContext, damage_rolls
from core.models import BattlePokemon, PokemonBuild
from data_sources.showdown_loader import get_move, get_species
from engine.move_selector import best_action_for_active_matchup
from engine.team_builder import Threat, build_team_greedy, team_score

# --- 実データ(Pokemon Showdown由来)からポケモン・技を取得 ---
GARCHOMP = get_species("garchomp")
LANDORUS_T = get_species("landorustherian")
CORVIKNIGHT = get_species("corviknight")
DRAGAPULT = get_species("dragapult")

EARTHQUAKE = get_move("earthquake")
DRAGON_CLAW = get_move("dragonclaw")
IRON_HEAD = get_move("ironhead")
BRAVE_BIRD = get_move("bravebird")
SHADOW_BALL = get_move("shadowball")
DRAGON_DARTS = get_move("dragondarts")


def demo_damage_calc() -> None:
    print("=== 1) ダメージ計算(実データ) ===")
    garchomp = BattlePokemon(build=PokemonBuild(
        species=GARCHOMP, ability="Rough Skin", item="いのちのたま",
        moves=(EARTHQUAKE, DRAGON_CLAW),
        evs={"hp": 4, "atk": 252, "dfn": 0, "spa": 0, "spd": 0, "spe": 252},
        nature_boost="atk", nature_drop="spa",
    ))
    corviknight = BattlePokemon(build=PokemonBuild(
        species=CORVIKNIGHT, ability="Mirror Armor", item="ゴツゴツメット",
        moves=(BRAVE_BIRD, IRON_HEAD),
        evs={"hp": 252, "atk": 0, "dfn": 252, "spa": 0, "spd": 4, "spe": 0},
    ))
    rolls = damage_rolls(garchomp, corviknight, EARTHQUAKE, DamageContext())
    print(f"{GARCHOMP.name}のじしん → {CORVIKNIGHT.name}: {min(rolls)}〜{max(rolls)} (乱数16通り)")
    print(f"{CORVIKNIGHT.name}の残りHP: {corviknight.current_hp}/{corviknight.max_hp}")
    print()


def demo_move_selector() -> None:
    print("=== 2) 対戦中の最適な技選択(実データ) ===")
    dragapult = PokemonBuild(
        species=DRAGAPULT, ability="Clear Body", item="こだわりハチマキ",
        moves=(DRAGON_DARTS, SHADOW_BALL),
        evs={"hp": 0, "atk": 252, "dfn": 0, "spa": 0, "spd": 4, "spe": 252},
        nature_boost="atk", nature_drop="spa",
    )
    landorus = PokemonBuild(
        species=LANDORUS_T, ability="Intimidate", item="こだわりスカーフ",
        moves=(EARTHQUAKE,),
        evs={"hp": 4, "atk": 252, "dfn": 0, "spa": 0, "spd": 0, "spe": 252},
        nature_boost="atk", nature_drop="spa",
    )
    corviknight = PokemonBuild(
        species=CORVIKNIGHT, ability="Mirror Armor", item="ゴツゴツメット",
        moves=(BRAVE_BIRD, IRON_HEAD),
        evs={"hp": 252, "atk": 0, "dfn": 252, "spa": 0, "spd": 4, "spe": 0},
    )

    side_a = Side.from_builds([dragapult, landorus])
    side_b = Side.from_builds([corviknight])

    state = BattleState(side_a=side_a, side_b=side_b)
    score, action = best_action_for_active_matchup(state, my_side="A", depth=2)
    print(f"手持ち: A={DRAGAPULT.name}/{LANDORUS_T.name}  B={CORVIKNIGHT.name}")
    print(f"推奨行動: {action.label() if action else 'なし'} (評価値={score:.1f})")
    print()


def demo_team_builder() -> None:
    print("=== 3) パーティ構築の最適化(実データ) ===")
    candidates = [
        PokemonBuild(species=GARCHOMP, moves=(EARTHQUAKE, DRAGON_CLAW)),
        PokemonBuild(species=LANDORUS_T, moves=(EARTHQUAKE,)),
        PokemonBuild(species=CORVIKNIGHT, moves=(BRAVE_BIRD, IRON_HEAD)),
        PokemonBuild(species=DRAGAPULT, moves=(DRAGON_DARTS, SHADOW_BALL)),
    ]
    threats = [
        Threat(name=GARCHOMP.name, types=GARCHOMP.types,
               move_types=GARCHOMP.types, usage_weight=1.0),
        Threat(name=DRAGAPULT.name, types=DRAGAPULT.types,
               move_types=DRAGAPULT.types, usage_weight=0.9),
    ]
    team = build_team_greedy(candidates, threats, team_size=3, random_restarts=5, local_search_iters=30, seed=42)
    names = [m.species.name for m in team.members]
    print(f"最適化されたパーティ: {names}")
    print(f"スコア: {team_score(team.members, threats):.2f}")


if __name__ == "__main__":
    demo_damage_calc()
    demo_move_selector()
    demo_team_builder()
