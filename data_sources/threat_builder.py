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
