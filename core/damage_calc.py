"""
ダメージ計算エンジン。

Pokemon Champions レギュレーションM-B(メガシンカ可、ダイマックス/テラスタル不可)を
前提に、第9世代のダメージ計算式をベースにする。
乱数(0.85〜1.00, 16通り)を全て返す `damage_rolls()` を主に使う。
"""
from __future__ import annotations

from dataclasses import dataclass

from core.models import BattlePokemon, Category, MoveData, Status, Terrain, Type, Weather
from core.type_chart import type_effectiveness

RANDOM_FACTORS = [85 + i for i in range(16)]  # 85..100 (%)


@dataclass
class DamageContext:
    weather: Weather = Weather.NONE
    terrain: Terrain = Terrain.NONE
    attacker_screens: bool = False  # リフレクター/ひかりのかべ等(簡略化して単一フラグ)
    critical: bool = False


def _stab(attacker: BattlePokemon, move: MoveData) -> float:
    types = attacker.active_species.types
    if move.type in types:
        # てきおうりょくなどの特性は未対応(将来拡張)
        return 1.5
    return 1.0


def _weather_modifier(move: MoveData, weather: Weather) -> float:
    if weather == Weather.SUN:
        if move.type == Type.FIRE:
            return 1.5
        if move.type == Type.WATER:
            return 0.5
    if weather == Weather.RAIN:
        if move.type == Type.WATER:
            return 1.5
        if move.type == Type.FIRE:
            return 0.5
    return 1.0


def damage_rolls(
    attacker: BattlePokemon,
    defender: BattlePokemon,
    move: MoveData,
    ctx: DamageContext | None = None,
) -> list[int]:
    """16通りの乱数ダメージ(整数HP)のリストを返す。変化技は[0]を返す。"""
    ctx = ctx or DamageContext()
    if move.category == Category.STATUS or move.power <= 0:
        return [0]

    level = attacker.build.level
    if move.category == Category.PHYSICAL:
        atk_stat = attacker.effective_stat("atk")
        def_stat = defender.effective_stat("dfn")
    else:
        atk_stat = attacker.effective_stat("spa")
        def_stat = defender.effective_stat("spd")

    base = (((2 * level) / 5 + 2) * move.power * atk_stat / max(1, def_stat)) / 50 + 2

    modifier = 1.0
    modifier *= _weather_modifier(move, ctx.weather)
    if ctx.critical:
        modifier *= 1.5
    modifier *= _stab(attacker, move)
    type_mult = type_effectiveness(move.type, defender.active_species.types)
    modifier *= type_mult
    if ctx.attacker_screens and move.category != Category.STATUS:
        modifier *= 0.66  # リフレクター/ひかりのかべの簡易近似
    if attacker.status == Status.BURN and move.category == Category.PHYSICAL:
        # effective_stat側で既に半減しているため二重適用しない
        pass

    rolls = []
    for r in RANDOM_FACTORS:
        dmg = int(base * modifier * (r / 100))
        rolls.append(max(1, dmg) if type_mult > 0 else 0)
    return rolls


def average_damage(attacker: BattlePokemon, defender: BattlePokemon, move: MoveData,
                    ctx: DamageContext | None = None) -> float:
    rolls = damage_rolls(attacker, defender, move, ctx)
    return sum(rolls) / len(rolls)


def is_ohko_guaranteed(attacker: BattlePokemon, defender: BattlePokemon, move: MoveData,
                        ctx: DamageContext | None = None) -> bool:
    rolls = damage_rolls(attacker, defender, move, ctx)
    return min(rolls) >= defender.current_hp
