# pokemon_optimizer

ポケモン対戦(シングルバトル、ランクバトル想定)の最適解探索ツール。

対象範囲は3本柱:
1. **技選択** — 対戦中のその場面での最適な行動(`engine/move_selector.py`, expectiminimax探索)
2. **パーティ構築** — 選出・型の最適化(`engine/team_builder.py`, 貪欲法+局所探索)
3. **ダメージ計算** — 詰み筋探索の基盤となる乱数16通りのダメージ計算(`core/damage_calc.py`)

## セットアップ

```bash
pip install -r requirements.txt
python parse_showdown_data.py   # 実データ(種族値・技)を data/cache/*.json に生成(初回のみ)
```

## 動作確認

```bash
PYTHONPATH=. python3 demo.py
PYTHONPATH=. python3 demo_real_meta.py   # 実際のチャンピオンズ環境データを使ったパーティ最適化
PYTHONPATH=. python3 -m pytest tests/
```

## ディレクトリ構成

```
core/                データモデル・タイプ相性・ダメージ計算・盤面状態
engine/               技選択探索(expectiminimax)・パーティ構築最適化
data_sources/
  showdown_loader.py    実データ(種族値・技)のロード
  threat_builder.py      使用率リストからThreatを自動生成
  champions_data.py      ポケモンチャンピオンズ公開データ取得クライアント
data/raw/              Pokemon Showdownの生データ(.ts、取得済み)・kotofurumiya/pokemon_data(日本語種族値、第7世代まで)
data/cache/             パース済みJSON・チャンピオンズ上位構築データ(取得済み)
tests/                 ユニットテスト
parse_showdown_data.py 実データ変換スクリプト
demo.py                実データでの一連の動作確認
demo_real_meta.py      実際のチャンピオンズ環境データ(M-4シングル)を使ったパーティ最適化デモ
```

## データソース

### 種族値・技データ(実装済み・取得済み)
[Pokemon Showdown](https://github.com/smogon/pokemon-showdown)(smogon、MITライセンス)の
`data/pokedex.ts` / `data/moves.ts` を `raw.githubusercontent.com` から取得し、
`parse_showdown_data.py` でJSON化して `data_sources/showdown_loader.py` から利用する。
全1480フォルム分の種族値・タイプ・特性、953件の技データ(タイプ・分類・威力・命中・優先度・PP)を収録。

```python
from data_sources.showdown_loader import get_species, get_move
garchomp = get_species("garchomp")       # 表示名 "Garchomp" でも可
earthquake = get_move("earthquake")
```

### ポケモンチャンピオンズの使用率・上位構築データ(取得済み・パイプライン実装済み)
レギュレーションM-B(メガシンカ可、ダイマックス/テラスタル不可)の環境データ:

- 上位構築データ(CSV/JSON): `champs.pokedb.tokyo/opendata/s{season}_{single|double}_ranked_teams.{csv|json}`
- 技/特性の使用率API: `championsbattledata.com/api/pokemon/{showdown_id}?format=Singles`

シーズンM-4(シングル、221チーム、2026-08-13時点)の上位構築データを取得済みで
`data/cache/ranked_teams_s4_single.json` にキャッシュしてある。
`data_sources/champions_data.py` の `summarize_usage()` で使用率上位を集計し、
`data_sources/threat_builder.py` の `build_threats_from_champions_usage()` /
`build_candidates_from_champions_usage()` で `engine.team_builder` の
`Threat` / `PokemonBuild` に変換できる。

上位構築データには技構成が含まれず種族値も持たないが、パーティ最適化のスコアリング
(`team_builder.team_score()`)はタイプ情報のみで計算されるため、
type1/type2から直接候補・脅威を組み立てる方式にしている
(第8/9世代のポケモンも含め、上位構築データに載っていれば種族値ソースの世代カバー範囲に
左右されずそのまま使える)。実際に動かす例は `demo_real_meta.py` を参照。

新しいシーズンのデータが欲しい場合は、`fetch_ranked_teams(season, "single")` を
ネットワーク制限のないローカル環境で実行し、`data/cache/` に出力されたJSONを
このプロジェクトに配置すれば良い(ファイル名の命名規則が一致していればそのままキャッシュとして使われる)。

## 技選択エンジンの性能特性

`engine/move_selector.py` は乱数ダメージ(16通り)をユニーク値ごとに確率分岐させる
expectiminimaxで、平均値のみで進める簡易版より正確(削り合いの際どい場面を正しく評価できる)。
探索木のクローンには `deepcopy` ではなく `BattleState.light_clone()`(可変フィールドのみ複製し、
種族値・技データ等の不変オブジェクトは参照共有)を使い、素朴なdeepcopy比で約18倍高速化した。

それでも分岐数は指数的に増えるため、目安として:

| 深さ | 1vs1・技2種程度での実行時間 |
|---|---|
| 2(既定) | 1〜2秒 |
| 3 | 数分オーダー(実用外) |

深さ2(自分の1手+相手の1手の読み合い)が実用上のデフォルト。より先の手数を読ませたい場合は
乱数のバケット数を減らす(例: 上振れ/中央値/下振れの3値に丸める)などの追加最適化が必要。

## 今後の拡張候補

- ポケモンチャンピオンズの使用率データを実際に取得し、`Threat` リストを環境準拠にする
- `Threat.move_types` を実際の技構成(使用率上位の技)で上書きし、簡易近似(自タイプ)から卒業する
- 深さ3以上を実用的にするための乱数バケット圧縮・枝刈り(αβ的な手法)の導入
- 特性・持ち物の個別効果(いかく、フォーカスサッシ、命の珠の反動など)の実装
- 交代読み・むしのさざめきなど追加効果を持つ技のハンドリング

