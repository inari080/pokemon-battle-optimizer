"""シングルバトルの盤面状態。"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.models import BattlePokemon, PokemonBuild, Terrain, Weather


@dataclass
class Side:
    party: list[BattlePokemon]
    active_index: int = 0

    @property
    def active(self) -> BattlePokemon:
        return self.party[self.active_index]

    def alive_indices(self) -> list[int]:
        return [i for i, p in enumerate(self.party) if not p.fainted]

    @classmethod
    def from_builds(cls, builds: list[PokemonBuild]) -> "Side":
        return cls(party=[BattlePokemon(build=b) for b in builds])

    def light_clone(self) -> "Side":
        return Side(party=[p.light_clone() for p in self.party], active_index=self.active_index)


@dataclass
class BattleState:
    side_a: Side
    side_b: Side
    weather: Weather = Weather.NONE
    weather_turns_left: int = 0
    terrain: Terrain = Terrain.NONE
    terrain_turns_left: int = 0
    turn: int = 1
    hazards_a: dict = field(default_factory=dict)  # 例: {"stealth_rock": True, "spikes": 0}
    hazards_b: dict = field(default_factory=dict)

    def is_over(self) -> bool:
        return not self.side_a.alive_indices() or not self.side_b.alive_indices()

    def winner(self) -> str | None:
        a_alive = bool(self.side_a.alive_indices())
        b_alive = bool(self.side_b.alive_indices())
        if a_alive and not b_alive:
            return "A"
        if b_alive and not a_alive:
            return "B"
        return None

    def clone(self) -> "BattleState":
        import copy
        return copy.deepcopy(self)

    def light_clone(self) -> "BattleState":
        """
        探索用の軽量クローン。種族値・技等の不変データは複製せず、
        HP・能力ランク・場の状態など可変フィールドのみを複製する。
        探索木のノード生成で copy.deepcopy の代わりに使うと大幅に高速。
        """
        return BattleState(
            side_a=self.side_a.light_clone(),
            side_b=self.side_b.light_clone(),
            weather=self.weather,
            weather_turns_left=self.weather_turns_left,
            terrain=self.terrain,
            terrain_turns_left=self.terrain_turns_left,
            turn=self.turn,
            hazards_a=dict(self.hazards_a),
            hazards_b=dict(self.hazards_b),
        )
