"""第9世代ベースのタイプ相性表。"""
from __future__ import annotations

from core.models import Type

# effectiveness[attack_type][defend_type] = 倍率
_RAW: dict[Type, dict[Type, float]] = {
    Type.NORMAL: {Type.ROCK: 0.5, Type.GHOST: 0.0, Type.STEEL: 0.5},
    Type.FIRE: {Type.FIRE: 0.5, Type.WATER: 0.5, Type.GRASS: 2.0, Type.ICE: 2.0,
                Type.BUG: 2.0, Type.ROCK: 0.5, Type.DRAGON: 0.5, Type.STEEL: 2.0},
    Type.WATER: {Type.FIRE: 2.0, Type.WATER: 0.5, Type.GRASS: 0.5, Type.GROUND: 2.0,
                 Type.ROCK: 2.0, Type.DRAGON: 0.5},
    Type.ELECTRIC: {Type.WATER: 2.0, Type.ELECTRIC: 0.5, Type.GRASS: 0.5, Type.GROUND: 0.0,
                    Type.FLYING: 2.0, Type.DRAGON: 0.5},
    Type.GRASS: {Type.FIRE: 0.5, Type.WATER: 2.0, Type.GRASS: 0.5, Type.POISON: 0.5,
                 Type.GROUND: 2.0, Type.FLYING: 0.5, Type.BUG: 0.5, Type.ROCK: 2.0,
                 Type.DRAGON: 0.5, Type.STEEL: 0.5},
    Type.ICE: {Type.FIRE: 0.5, Type.WATER: 0.5, Type.GRASS: 2.0, Type.ICE: 0.5,
               Type.GROUND: 2.0, Type.FLYING: 2.0, Type.DRAGON: 2.0, Type.STEEL: 0.5},
    Type.FIGHTING: {Type.NORMAL: 2.0, Type.ICE: 2.0, Type.POISON: 0.5, Type.FLYING: 0.5,
                    Type.PSYCHIC: 0.5, Type.BUG: 0.5, Type.ROCK: 2.0, Type.GHOST: 0.0,
                    Type.DARK: 2.0, Type.STEEL: 2.0, Type.FAIRY: 0.5},
    Type.POISON: {Type.GRASS: 2.0, Type.POISON: 0.5, Type.GROUND: 0.5, Type.ROCK: 0.5,
                  Type.GHOST: 0.5, Type.STEEL: 0.0, Type.FAIRY: 2.0},
    Type.GROUND: {Type.FIRE: 2.0, Type.ELECTRIC: 2.0, Type.GRASS: 0.5, Type.POISON: 2.0,
                  Type.FLYING: 0.0, Type.BUG: 0.5, Type.ROCK: 2.0, Type.STEEL: 2.0},
    Type.FLYING: {Type.ELECTRIC: 0.5, Type.GRASS: 2.0, Type.FIGHTING: 2.0, Type.BUG: 2.0,
                  Type.ROCK: 0.5, Type.STEEL: 0.5},
    Type.PSYCHIC: {Type.FIGHTING: 2.0, Type.POISON: 2.0, Type.PSYCHIC: 0.5, Type.DARK: 0.0,
                   Type.STEEL: 0.5},
    Type.BUG: {Type.FIRE: 0.5, Type.GRASS: 2.0, Type.FIGHTING: 0.5, Type.POISON: 0.5,
               Type.FLYING: 0.5, Type.PSYCHIC: 2.0, Type.GHOST: 0.5, Type.DARK: 2.0,
               Type.STEEL: 0.5, Type.FAIRY: 0.5},
    Type.ROCK: {Type.FIRE: 2.0, Type.ICE: 2.0, Type.FIGHTING: 0.5, Type.GROUND: 0.5,
                Type.FLYING: 2.0, Type.BUG: 2.0, Type.STEEL: 0.5},
    Type.GHOST: {Type.NORMAL: 0.0, Type.PSYCHIC: 2.0, Type.GHOST: 2.0, Type.DARK: 0.5},
    Type.DRAGON: {Type.DRAGON: 2.0, Type.STEEL: 0.5, Type.FAIRY: 0.0},
    Type.DARK: {Type.FIGHTING: 0.5, Type.PSYCHIC: 2.0, Type.GHOST: 2.0, Type.DARK: 0.5,
                Type.FAIRY: 0.5},
    Type.STEEL: {Type.FIRE: 0.5, Type.WATER: 0.5, Type.ELECTRIC: 0.5, Type.ICE: 2.0,
                 Type.ROCK: 2.0, Type.STEEL: 0.5, Type.FAIRY: 2.0},
    Type.FAIRY: {Type.FIRE: 0.5, Type.FIGHTING: 2.0, Type.POISON: 0.5, Type.DRAGON: 2.0,
                 Type.DARK: 2.0, Type.STEEL: 0.5},
}


def type_effectiveness(attack_type: Type, defend_types: tuple[Type, ...]) -> float:
    """攻撃タイプ対複合防御タイプの倍率(0, 0.25, 0.5, 1, 2, 4)を返す。"""
    if attack_type == Type.NONE:
        return 1.0
    mult = 1.0
    table = _RAW.get(attack_type, {})
    for d in defend_types:
        if d == Type.NONE:
            continue
        mult *= table.get(d, 1.0)
    return mult
