"""
基本データモデル定義。

Pokemon Champions レギュレーションM-B(メガシンカ可、ダイマックス/テラスタル不可)を
前提にしたシングルバトル向けモデル。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Type(str, Enum):
    NORMAL = "ノーマル"
    FIRE = "ほのお"
    WATER = "みず"
    ELECTRIC = "でんき"
    GRASS = "くさ"
    ICE = "こおり"
    FIGHTING = "かくとう"
    POISON = "どく"
    GROUND = "じめん"
    FLYING = "ひこう"
    PSYCHIC = "エスパー"
    BUG = "むし"
    ROCK = "いわ"
    GHOST = "ゴースト"
    DRAGON = "ドラゴン"
    DARK = "あく"
    STEEL = "はがね"
    FAIRY = "フェアリー"
    NONE = "なし"


class Category(str, Enum):
    PHYSICAL = "物理"
    SPECIAL = "特殊"
    STATUS = "変化"


class Weather(str, Enum):
    NONE = "なし"
    SUN = "はれ"
    RAIN = "あめ"
    SAND = "すなあらし"
    SNOW = "ゆき"


class Terrain(str, Enum):
    NONE = "なし"
    ELECTRIC = "エレキフィールド"
    GRASSY = "グラスフィールド"
    MISTY = "ミストフィールド"
    PSYCHIC = "サイコフィールド"


class Status(str, Enum):
    NONE = "なし"
    BURN = "やけど"
    POISON = "どく"
    BADLY_POISON = "もうどく"
    PARALYSIS = "まひ"
    SLEEP = "ねむり"
    FREEZE = "こおり"


@dataclass
class BaseStats:
    hp: int
    atk: int
    dfn: int
    spa: int
    spd: int
    spe: int


@dataclass
class Species:
    """種族データ(種族値・タイプ・覚える技プールなど)。"""

    name: str
    types: tuple[Type, ...]
    base_stats: BaseStats
    abilities: tuple[str, ...]
    mega_form_of: Optional[str] = None  # このフォルムがメガシンカ後の姿である場合の元species名


@dataclass
class MoveData:
    """技データ。"""

    name: str
    type: Type
    category: Category
    power: int  # 変化技/固定ダメージ技は0扱いにし、別途特殊処理する
    accuracy: Optional[int]  # Noneは必中
    priority: int = 0
    pp: int = 10
    # 追加効果(簡略化): 自分/相手への能力変化、追加状態異常、回復割合など
    secondary_effect: Optional[str] = None
    makes_contact: bool = True


@dataclass
class StatStages:
    atk: int = 0
    dfn: int = 0
    spa: int = 0
    spd: int = 0
    spe: int = 0
    accuracy: int = 0
    evasion: int = 0

    def clamp(self) -> None:
        for f in ("atk", "dfn", "spa", "spd", "spe", "accuracy", "evasion"):
            setattr(self, f, max(-6, min(6, getattr(self, f))))


@dataclass
class PokemonBuild:
    """実際に対戦で使う「型」(努力値・性格・持ち物・技構成など)。"""

    species: Species
    level: int = 50
    nature_boost: Optional[str] = None  # 上昇するステータス名 ("atk","spa","spe","dfn","spd") or None
    nature_drop: Optional[str] = None
    evs: dict[str, int] = field(default_factory=lambda: {
        "hp": 0, "atk": 0, "dfn": 0, "spa": 0, "spd": 0, "spe": 0,
    })
    ivs: dict[str, int] = field(default_factory=lambda: {
        "hp": 31, "atk": 31, "dfn": 31, "spa": 31, "spd": 31, "spe": 31,
    })
    ability: str = ""
    item: str = ""
    tera_type: Optional[Type] = None  # レギュレーションM-Bでは未解禁だが将来のため保持
    can_mega_evolve: bool = False
    mega_species: Optional[Species] = None
    moves: tuple[MoveData, ...] = field(default_factory=tuple)

    def calc_stat(self, stat: str) -> int:
        """実数値を計算する(HPと他ステータスで計算式が異なる)。"""
        base = getattr(self.species.base_stats, "dfn" if stat == "def" else stat)
        iv = self.ivs.get(stat, 31)
        ev = self.evs.get(stat, 0)
        if stat == "hp":
            if self.species.name == "ヌケニン":
                return 1
            return ((base * 2 + iv + ev // 4) * self.level) // 100 + self.level + 10
        value = ((base * 2 + iv + ev // 4) * self.level) // 100 + 5
        if self.nature_boost == stat:
            value = int(value * 1.1)
        if self.nature_drop == stat:
            value = int(value * 0.9)
        return value


@dataclass
class BattlePokemon:
    """バトル中の1体の可変状態(現在HP・能力ランク・状態異常など)。"""

    build: PokemonBuild
    current_hp: int = field(init=False)
    max_hp: int = field(init=False)
    stages: StatStages = field(default_factory=StatStages)
    status: Status = Status.NONE
    is_mega_evolved: bool = False
    active_species: Species = field(init=False)
    fainted: bool = False

    def __post_init__(self) -> None:
        self.max_hp = self.build.calc_stat("hp")
        self.current_hp = self.max_hp
        self.active_species = self.build.species

    def effective_stat(self, stat: str) -> int:
        base = self.build.calc_stat(stat)
        stage = getattr(self.stages, stat)
        multiplier = (max(2, 2 + stage)) / (max(2, 2 - stage)) if stage >= 0 else 2 / (2 - stage)
        value = int(base * multiplier)
        if self.status == Status.PARALYSIS and stat == "spe":
            value = value // 2
        if self.status == Status.BURN and stat == "atk":
            value = value // 2
        return max(1, value)

    def hp_fraction(self) -> float:
        return self.current_hp / self.max_hp if self.max_hp else 0.0

    def apply_damage(self, dmg: int) -> None:
        self.current_hp = max(0, self.current_hp - dmg)
        if self.current_hp == 0:
            self.fainted = True

    def heal(self, amount: int) -> None:
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def light_clone(self) -> "BattlePokemon":
        """
        探索用の軽量クローン。build/active_species等の不変データは複製せず参照を共有し、
        ターン中に変化しうるフィールド(HP・能力ランク・状態異常等)だけを複製する。
        copy.deepcopyよりも大幅に高速。
        """
        clone = object.__new__(BattlePokemon)
        clone.build = self.build  # 不変なので共有
        clone.max_hp = self.max_hp
        clone.current_hp = self.current_hp
        clone.stages = StatStages(
            atk=self.stages.atk, dfn=self.stages.dfn, spa=self.stages.spa,
            spd=self.stages.spd, spe=self.stages.spe,
            accuracy=self.stages.accuracy, evasion=self.stages.evasion,
        )
        clone.status = self.status
        clone.is_mega_evolved = self.is_mega_evolved
        clone.active_species = self.active_species  # 不変なので共有
        clone.fainted = self.fainted
        return clone


@dataclass
class Team:
    name: str
    members: list[PokemonBuild] = field(default_factory=list)
