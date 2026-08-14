from data_sources.champions_data import summarize_usage
from data_sources.threat_builder import build_candidates_from_champions_usage, build_threats_from_champions_usage
from core.models import Type

SAMPLE_DATA = {
    "season": "M-4", "season_number": 4, "rule": "シングル",
    "teams": [
        {"rank": 1, "rating_value": 2500.0, "team": [
            {"id": "0445-00", "pokemon": "ガブリアス", "form": "", "type1": "ドラゴン",
             "type2": "じめん", "category": "一般", "terastal": "", "item": "きあいのタスキ"},
            {"id": "0778-00", "pokemon": "ミミッキュ", "form": "ばけたすがた", "type1": "ゴースト",
             "type2": "フェアリー", "category": "一般", "terastal": "", "item": "いのちのたま"},
        ]},
        {"rank": 2, "rating_value": 2490.0, "team": [
            {"id": "0445-00", "pokemon": "ガブリアス", "form": "", "type1": "ドラゴン",
             "type2": "じめん", "category": "一般", "terastal": "", "item": "こだわりスカーフ"},
        ]},
    ],
    "updated_at": "2026-08-13 16:54:21",
}


def test_summarize_usage_counts_and_weights():
    usage = summarize_usage(SAMPLE_DATA, top_n=10)
    names = {u["name"]: u for u in usage}
    assert names["ガブリアス"]["count"] == 2
    assert names["ミミッキュ"]["count"] == 1
    total_weight = sum(u["usage_weight"] for u in usage)
    assert abs(total_weight - 1.0) < 1e-9
    # 採用数の多い順に並んでいること
    assert usage[0]["name"] == "ガブリアス"


def test_summarize_usage_preserves_form_and_types():
    usage = summarize_usage(SAMPLE_DATA, top_n=10)
    mimikyu = next(u for u in usage if u["name"] == "ミミッキュ")
    assert mimikyu["form"] == "ばけたすがた"
    assert mimikyu["type1"] == "ゴースト"
    assert mimikyu["type2"] == "フェアリー"


def test_build_threats_from_champions_usage():
    usage = summarize_usage(SAMPLE_DATA, top_n=10)
    threats = build_threats_from_champions_usage(usage)
    garchomp_threat = next(t for t in threats if t.name.startswith("ガブリアス"))
    assert Type.DRAGON in garchomp_threat.types
    assert Type.GROUND in garchomp_threat.types


def test_build_candidates_from_champions_usage_includes_form_in_name():
    usage = summarize_usage(SAMPLE_DATA, top_n=10)
    candidates = build_candidates_from_champions_usage(usage)
    names = [c.species.name for c in candidates]
    assert any("ミミッキュ" in n and "ばけたすがた" in n for n in names)
