"""
使用率上位ポケモンのリスト(名前+重み)から、team_builder.Threat のリストを
実データ(showdown_loader経由)を使って自動生成するヘルパー。

本来はチャンピオンズの使用率データ(championsbattledata.com等、data_sources/champions_data.py)
から取得した名前+重みを渡す想定。このコンテナ環境は外部アクセスが制限されているため、
ここでは「名前と重みのリストを渡せば実データのタイプ情報を使ってThreatを組み立てられる」
という変換ロジックのみを提供する。
"""
from __future__ import annotations

from data_sources.showdown_loader import get_species
from engine.team_builder import Threat
from core.models import BaseStats, PokemonBuild, Species, Type


def build_threats_from_usage(usage: list[tuple[str, float]]) -> list[Threat]:
    """
    usage: [(showdown_id_or_name, weight), ...] のリスト。
    種族のタイプ情報を実データから引き、move_types は簡易的に自タイプで近似する
    (技構成データまで統合する場合は別途 championsbattledata.com の技データで上書きする)。
    """
    threats = []
    for name, weight in usage:
        species = get_species(name)
        threats.append(Threat(
            name=species.name,
            types=species.types,
            move_types=species.types,  # 簡易近似。技データがあれば差し替え可能
            usage_weight=weight,
        ))
    return threats


_TYPE_BY_JA = {t.value: t for t in Type}


def build_threats_from_champions_usage(usage_summary: list[dict]) -> list[Threat]:
    """
    champions_data.summarize_usage() の戻り値から直接 Threat のリストを組み立てる。
    上位構築データには type1/type2 が日本語で含まれているため、
    showdown_loader を経由した英語名マッチングは不要。
    (技構成データが無いため move_types は自タイプで近似する)
    """
    threats = []
    for u in usage_summary:
        t1 = _TYPE_BY_JA.get(u.get("type1", ""), Type.NONE)
        t2 = _TYPE_BY_JA.get(u.get("type2", ""), Type.NONE)
        types = tuple(t for t in (t1, t2) if t != Type.NONE) or (Type.NONE,)
        display_name = u["name"] + (f"({u['form']})" if u.get("form") else "")
        threats.append(Threat(
            name=display_name,
            types=types,
            move_types=types,  # 簡易近似。技構成データがあれば差し替え可能
            usage_weight=u["usage_weight"],
        ))
    return threats


def build_candidates_from_champions_usage(usage_summary: list[dict]) -> list[PokemonBuild]:
    """
    champions_data.summarize_usage() の戻り値から、パーティ構築の候補プールとして
    PokemonBuild のリストを直接組み立てる。

    team_builder.team_score() はタイプ情報(Species.types)のみでスコアを計算するため、
    種族値・技構成が無くても候補として機能する。これにより、世代の新しいポケモン
    (Showdownデータやkotofurumiya/pokemon_data(第7世代までしかカバーしない)に
    無いポケモンを含む)でも、上位構築データに含まれていれば候補にできる。

    種族値はダミー値(全て0)で埋めているため、ダメージ計算等スタッツを要する用途には
    使えない。あくまで「実際の環境で使われているポケモンの中から選出/構築を最適化する」
    という粗い候補プール生成に用いる。
    """
    placeholder_stats = BaseStats(hp=0, atk=0, dfn=0, spa=0, spd=0, spe=0)
    candidates = []
    for u in usage_summary:
        t1 = _TYPE_BY_JA.get(u.get("type1", ""), Type.NONE)
        t2 = _TYPE_BY_JA.get(u.get("type2", ""), Type.NONE)
        types = tuple(t for t in (t1, t2) if t != Type.NONE) or (Type.NONE,)
        display_name = u["name"] + (f"({u['form']})" if u.get("form") else "")
        species = Species(name=display_name, types=types, base_stats=placeholder_stats, abilities=())
        candidates.append(PokemonBuild(species=species, moves=()))
    return candidates
