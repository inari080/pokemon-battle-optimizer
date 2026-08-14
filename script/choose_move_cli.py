#!/usr/bin/env python3
"""
指定した2体での局面を作り、最適な行動（技 or 交代）を出力する CLI。

使い方例:
PYTHONPATH=. py scripts\choose_move_cli.py --a '{"species":"dragapult","moves":["dragondarts","shadowball"],"ability":"Clear Body","item":"Choice Band","evs":{"atk":252,"spe":252}}' --b '{"species":"corviknight","moves":["bravebird","ironhead"],"ability":"Mirror Armor","item":"Rocky Helmet","evs":{"hp":252,"dfn":252}}' --depth 2

--a / --b は JSON 文字列かファイルパスを渡せます。
JSON の例:
{
  "species": "dragapult",
  "moves": ["dragondarts","shadowball"],
  "ability": "Clear Body",
  "item": "Choice Band",
  "level": 50,
  "nature_boost": "atk",
  "nature_drop": "spa",
  "evs": {"hp":0,"atk":252,"dfn":0,"spa":0,"spd":4,"spe":252}
}
"""
import sys
from pathlib import Path
import json
import argparse

# --- どのカレントからでも動くように repo root を sys.path に追加 ---
p = Path(__file__).resolve()
repo_root = p
while repo_root != repo_root.parent:
    if (repo_root / "core").exists() and (repo_root / "engine").exists():
        break
    repo_root = repo_root.parent
sys.path.insert(0, str(repo_root))

from data_sources.showdown_loader import get_species, get_move
from core.models import PokemonBuild
from core.battle_state import Side, BattleState
from engine.move_selector import best_action_for_active_matchup, legal_actions, _resolve_turn_distribution, expectiminimax

def load_json_or_file(s: str):
    # 引数がファイルパスならファイルを読み、そうでなければ JSON としてパース
    p = Path(s)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return json.loads(s)

def build_from_spec(spec: dict) -> PokemonBuild:
    # 必須: species
    if "species" not in spec:
        raise ValueError("spec must include 'species' field (showdown id or name)")
    species = get_species(spec["species"])
    moves = tuple()
    if "moves" in spec:
        moves = tuple(get_move(m) for m in spec["moves"])
    # デフォルトパラメータ
    level = int(spec.get("level", 50))
    nature_boost = spec.get("nature_boost")  # 例: "atk"
    nature_drop = spec.get("nature_drop")    # 例: "spa"
    evs = spec.get("evs", {"hp":0,"atk":0,"dfn":0,"spa":0,"spd":0,"spe":0})
    ivs = spec.get("ivs", {"hp":31,"atk":31,"dfn":31,"spa":31,"spd":31,"spe":31})
    ability = spec.get("ability", "")
    item = spec.get("item", "")
    can_mega = spec.get("can_mega_evolve", False)
    mega_species = None
    if can_mega and "mega_species" in spec:
        mega_species = get_species(spec["mega_species"])
    return PokemonBuild(
        species=species,
        level=level,
        nature_boost=nature_boost,
        nature_drop=nature_drop,
        evs=evs,
        ivs=ivs,
        ability=ability,
        item=item,
        can_mega_evolve=can_mega,
        mega_species=mega_species,
        moves=moves,
    )

def evaluate_and_print(state: BattleState, my_side: str = "A", depth: int = 2):
    print("=== 推奨行動 ===")
    score, action = best_action_for_active_matchup(state, my_side=my_side, depth=depth)
    print(f"最良: {action.label() if action else 'なし'} (スコア={score:.2f})")
    print()
    print("=== 候補ごとの期待評価（相手最善想定） ===")
    my_actions = legal_actions(state.side_a) if my_side == "A" else legal_actions(state.side_b)
    opp_actions = legal_actions(state.side_b) if my_side == "A" else legal_actions(state.side_a)
    for act in my_actions:
        worst_for_me = None
        for opp in opp_actions:
            if my_side == "A":
                branches = _resolve_turn_distribution(state, act, opp)
            else:
                branches = _resolve_turn_distribution(state, opp, act)
            expected = 0.0
            for prob, child in branches:
                val, _ = expectiminimax(child, depth - 1, my_side)
                expected += prob * val
            if worst_for_me is None or expected < worst_for_me:
                worst_for_me = expected
        print(f"{act.label():40} 期待評価 = {worst_for_me:.2f}")

def main():
    parser = argparse.ArgumentParser(description="指定した2体での最適行動を評価する")
    parser.add_argument("--a", required=True, help="A 側のポケモン指定 (JSON 文字列またはファイルパス)")
    parser.add_argument("--b", required=True, help="B 側のポケモン指定 (JSON 文字列またはファイルパス)")
    parser.add_argument("--depth", type=int, default=2, help="探索深さ（既定 2）")
    parser.add_argument("--my-side", choices=("A","B"), default="A", help="最適化の観点（自分側）")
    args = parser.parse_args()

    spec_a = load_json_or_file(args.a)
    spec_b = load_json_or_file(args.b)
    build_a = build_from_spec(spec_a)
    build_b = build_from_spec(spec_b)
    side_a = Side.from_builds([build_a])
    side_b = Side.from_builds([build_b])
    state = BattleState(side_a=side_a, side_b=side_b)
    evaluate_and_print(state, my_side=args.my_side, depth=args.depth)

if __name__ == "__main__":
    main()