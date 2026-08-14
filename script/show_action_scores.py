# scripts/show_action_scores.py
# 実行: PYTHONPATH=. python3 scripts/show_action_scores.py

import sys
from pathlib import Path

# このファイルから上方向に辿って core/ と engine/ が見つかる最上位を repo_root とする
p = Path(__file__).resolve()
repo_root = p
while repo_root != repo_root.parent:
    if (repo_root / "core").exists() and (repo_root / "engine").exists():
        break
    repo_root = repo_root.parent
sys.path.insert(0, str(repo_root))

from engine.move_selector import legal_actions, _resolve_turn_distribution, expectiminimax
from core.battle_state import BattleState, Side
from data_sources.showdown_loader import get_species, get_move
from core.models import PokemonBuild

# --- 簡単な盤面を demo.py と同じように作る (必要に応じて書き換えてください) ---
DRAGAPULT = get_species("dragapult")
DRAGON_DARTS = get_move("dragondarts")
SHADOW_BALL = get_move("shadowball")
LANDORUS_T = get_species("landorustherian")
EARTHQUAKE = get_move("earthquake")
CORVIKNIGHT = get_species("corviknight")
BRAVE_BIRD = get_move("bravebird")
IRON_HEAD = get_move("ironhead")

dragapult = PokemonBuild(species=DRAGAPULT, ability="Clear Body", item="こだわりハチマキ",
                         moves=(DRAGON_DARTS, SHADOW_BALL),
                         evs={"hp":0,"atk":252,"dfn":0,"spa":0,"spd":4,"spe":252},
                         nature_boost="atk", nature_drop="spa")
landorus = PokemonBuild(species=LANDORUS_T, ability="Intimidate", item="こだわりスカーフ",
                        moves=(EARTHQUAKE,), evs={"hp":4,"atk":252,"dfn":0,"spa":0,"spd":0,"spe":252},
                        nature_boost="atk", nature_drop="spa")
corviknight = PokemonBuild(species=CORVIKNIGHT, ability="Mirror Armor", item="ゴツゴツメット",
                           moves=(BRAVE_BIRD, IRON_HEAD),
                           evs={"hp":252,"atk":0,"dfn":252,"spa":0,"spd":4,"spe":0})

side_a = Side.from_builds([dragapult, landorus])
side_b = Side.from_builds([corviknight])
state = BattleState(side_a=side_a, side_b=side_b)

# depth を調整（2 が既定で実用的）
depth = 2
my_side = "A"

# 全候補アクションを列挙して、それぞれの期待評価を計算
actions = legal_actions(state.side_a)  # A側の候補
for act in actions:
    # 各相手行動に対してターン解決 → 子盤面を得て、expectiminimax で残りを評価する方法
    worst_for_me = None
    opp_actions = legal_actions(state.side_b)
    for opp in opp_actions:
        branches = _resolve_turn_distribution(state, act, opp)  # (prob, child_state) のリスト
        expected = 0.0
        for prob, child in branches:
            score, _ = expectiminimax(child, depth - 1, my_side)
            expected += prob * score
        if worst_for_me is None or expected < worst_for_me:
            worst_for_me = expected
    print(f"{act.label():40} 期待評価 = {worst_for_me:.2f}")