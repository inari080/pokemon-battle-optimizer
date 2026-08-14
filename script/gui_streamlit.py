#!/usr/bin/env python3
"""
Streamlit ベースの簡易 GUI:
- 左右のポケモンを選択 / 技・特性・持ち物・性格・努力値を入力
- 「評価」ボタンで engine.move_selector による最適行動（推奨技）と候補ごとの期待評価を表示

実行:
  # 事前に data/cache/*.json を生成しておくこと (parse_showdown_data.py)
  pip install streamlit
  PYTHONPATH=. streamlit run scripts/gui_streamlit.py

注:
  データ読み込みに時間がかかる場合があります (初回)。探索 depth=2 が既定で実行に1〜2秒ほどかかります。
"""
from pathlib import Path
import sys
import json

# --- どのカレントからでも動くように repo root を sys.path に追加 ---
p = Path(__file__).resolve()
repo_root = p
while repo_root != repo_root.parent:
    if (repo_root / "core").exists() and (repo_root / "engine").exists():
        break
    repo_root = repo_root.parent
sys.path.insert(0, str(repo_root))

import streamlit as st
from data_sources.showdown_loader import list_species_names, list_move_names, get_move, get_species
from core.models import PokemonBuild
from core.battle_state import Side, BattleState
from engine.move_selector import best_action_for_active_matchup, legal_actions, _resolve_turn_distribution, expectiminimax

# キャッシュしておく（表示リスト）
@st.cache(allow_output_mutation=True)
def _species_list():
    return sorted(list_species_names())

@st.cache(allow_output_mutation=True)
def _move_list():
    moves = list_move_names()
    moves_sorted = sorted(moves)
    return moves_sorted

SPECIES = _species_list()
MOVES = _move_list()
NATURE_STATS = ["atk", "dfn", "spa", "spd", "spe", None]

st.set_page_config(page_title="Pokemon Move Selector (GUI)", layout="wide")

st.title("Pokemon Battle Optimizer — GUI")
st.markdown("左右にポケモンを設定して「評価」ボタンを押すと、その場面での推奨行動と候補ごとの期待評価を表示します。")

col_a, col_b, col_ctrl = st.columns([1,1,0.6])

def pokemon_form(col, label_prefix="A"):
    with col:
        st.header(f"{label_prefix} 側")
        species_name = st.selectbox(f"{label_prefix}: 種族", SPECIES, key=f"species_{label_prefix}")
        # 技は最大4つ選べるようにする
        moves = st.multiselect(f"{label_prefix}: 技 (最大4つ)", MOVES, default=[], key=f"moves_{label_prefix}")
        ability = st.text_input(f"{label_prefix}: 特性 (任意テキスト)", key=f"ability_{label_prefix}")
        item = st.text_input(f"{label_prefix}: 持ち物 (任意テキスト)", key=f"item_{label_prefix}")
        level = st.number_input(f"{label_prefix}: レベル", min_value=1, max_value=100, value=50, key=f"level_{label_prefix}")
        nature_boost = st.selectbox(f"{label_prefix}: 性格(+)", options=NATURE_STATS, index=0, key=f"nb_{label_prefix}")
        nature_drop = st.selectbox(f"{label_prefix}: 性格(-)", options=NATURE_STATS, index=2, key=f"nd_{label_prefix}")
        st.markdown(f"{label_prefix}: 努力値 (各 0-252, 合計 510 目安)")
        ev_hp = st.slider(f"{label_prefix}: HP EV", 0, 252, 0, key=f"ev_hp_{label_prefix}")
        ev_atk = st.slider(f"{label_prefix}: ATK EV", 0, 252, 0, key=f"ev_atk_{label_prefix}")
        ev_def = st.slider(f"{label_prefix}: DEF EV", 0, 252, 0, key=f"ev_def_{label_prefix}")
        ev_spa = st.slider(f"{label_prefix}: SPA EV", 0, 252, 0, key=f"ev_spa_{label_prefix}")
        ev_spd = st.slider(f"{label_prefix}: SPD EV", 0, 252, 0, key=f"ev_spd_{label_prefix}")
        ev_spe = st.slider(f"{label_prefix}: SPE EV", 0, 252, 0, key=f"ev_spe_{label_prefix}")
        return {
            "species": species_name,
            "moves": moves[:4],
            "ability": ability,
            "item": item,
            "level": int(level),
            "nature_boost": nature_boost,
            "nature_drop": nature_drop,
            "evs": {"hp": ev_hp, "atk": ev_atk, "dfn": ev_def, "spa": ev_spa, "spd": ev_spd, "spe": ev_spe},
        }

spec_a = pokemon_form(col_a, "A")
spec_b = pokemon_form(col_b, "B")

with col_ctrl:
    st.header("実行設定")
    depth = st.number_input("探索深さ (depth)", min_value=1, max_value=3, value=2, step=1)
    my_side = st.selectbox("評価の観点 (自分側)", ("A","B"), index=0)
    run_button = st.button("評価する")
    st.markdown("注意: depth=2 で数秒、depth=3 は非常に重い可能性があります。")

# 保存/読み込み
st.markdown("### 保存 / 読み込み")
save_col, load_col = st.columns(2)
with save_col:
    save_name = st.text_input("保存ファイル名 (例: a_vs_b.json)", value="a_vs_b.json")
    if st.button("現在設定を保存"):
        obj = {"a": spec_a, "b": spec_b}
        Path(save_name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        st.success(f"保存しました: {save_name}")
with load_col:
    load_path = st.text_input("読み込みファイルパス (例: a_vs_b.json)")
    if st.button("読み込み"):
        try:
            data = json.loads(Path(load_path).read_text(encoding="utf-8"))
            # crude: directly set session_state values based on loaded data
            # For simplicity, just notify and recommend refresh
            st.info("読み込みしました。ページをリロードしてフォーム値を手動で合わせてください。")
            st.json(data)
        except Exception as e:
            st.error(f"読み込み失敗: {e}")

def build_from_spec(spec):
    # 名前->Species/MoveData に変換 (get_move/get_species は内部でキャッシュあり)
    species = get_species(spec["species"])
    moves = tuple(get_move(m) for m in spec.get("moves", []))
    build = PokemonBuild(
        species=species,
        level=spec.get("level", 50),
        nature_boost=spec.get("nature_boost"),
        nature_drop=spec.get("nature_drop"),
        evs=spec.get("evs", {"hp":0,"atk":0,"dfn":0,"spa":0,"spd":0,"spe":0}),
        ivs=spec.get("ivs", {"hp":31,"atk":31,"dfn":31,"spa":31,"spd":31,"spe":31}),
        ability=spec.get("ability",""),
        item=spec.get("item",""),
        moves=moves,
    )
    return build

def evaluate(state, my_side="A", depth=2):
    # 実行: 推奨技 + 候補ごとの期待評価を計算して返す辞書
    score, action = best_action_for_active_matchup(state, my_side=my_side, depth=depth)
    results = {"best_score": score, "best_action": action.label() if action else None, "candidates": []}
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
        results["candidates"].append({"label": act.label(), "expected": worst_for_me})
    results["candidates"].sort(key=lambda x: x["expected"], reverse=True)
    return results

if run_button:
    # 実行
    with st.spinner("評価中...待ってください"):
        try:
            build_a = build_from_spec(spec_a)
            build_b = build_from_spec(spec_b)
            side_a = Side.from_builds([build_a])
            side_b = Side.from_builds([build_b])
            state = BattleState(side_a=side_a, side_b=side_b)
            res = evaluate(state, my_side=my_side, depth=int(depth))
            st.subheader("推奨結果")
            st.write(f"最良: {res['best_action']}  (スコア={res['best_score']:.2f})")
            st.subheader("候補一覧 (期待評価, 高い順)")
            for c in res["candidates"]:
                st.write(f"{c['label']}: {c['expected']:.2f}")
        except Exception as e:
            st.error(f"評価中にエラーが発生しました: {e}")