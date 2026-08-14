from core.damage_calc import DamageContext, damage_rolls
from core.models import BaseStats, BattlePokemon, Category, MoveData, PokemonBuild, Species, Type

FIRE_MON = Species(
    name="テストほのお",
    types=(Type.FIRE,),
    base_stats=BaseStats(hp=100, atk=100, dfn=100, spa=100, spd=100, spe=100),
    abilities=("がんじょう",),
)
GRASS_MON = Species(
    name="テストくさ",
    types=(Type.GRASS,),
    base_stats=BaseStats(hp=100, atk=100, dfn=100, spa=100, spd=100, spe=100),
    abilities=("がんじょう",),
)
STEEL_MON = Species(
    name="テストはがね",
    types=(Type.STEEL,),
    base_stats=BaseStats(hp=100, atk=100, dfn=100, spa=100, spd=100, spe=100),
    abilities=("がんじょう",),
)
WATER_MON = Species(
    name="テストみず",
    types=(Type.WATER,),
    base_stats=BaseStats(hp=100, atk=100, dfn=100, spa=100, spd=100, spe=100),
    abilities=("がんじょう",),
)

EMBER = MoveData(name="ひのこ", type=Type.FIRE, category=Category.SPECIAL, power=80, accuracy=100)


def _mon(species):
    return BattlePokemon(build=PokemonBuild(species=species, moves=(EMBER,)))


def test_super_effective_hits_harder_than_resisted():
    attacker = _mon(FIRE_MON)
    grass_def = _mon(GRASS_MON)  # くさはほのおに弱点(2倍)
    water_def = _mon(WATER_MON)  # みずはほのおに耐性(0.5倍)
    rolls_super = damage_rolls(attacker, grass_def, EMBER, DamageContext())
    rolls_resist = damage_rolls(attacker, water_def, EMBER, DamageContext())
    assert min(rolls_super) > min(rolls_resist)


def test_stab_applied():
    fire_attacker = _mon(FIRE_MON)
    grass_attacker = _mon(GRASS_MON)  # STABなし(ひのこはくさタイプではない)
    defender = _mon(STEEL_MON)
    rolls_with_stab = damage_rolls(fire_attacker, defender, EMBER, DamageContext())
    rolls_without_stab = damage_rolls(grass_attacker, defender, EMBER, DamageContext())
    assert sum(rolls_with_stab) > sum(rolls_without_stab)


def test_status_move_deals_zero():
    attacker = _mon(FIRE_MON)
    defender = _mon(GRASS_MON)
    status_move = MoveData(name="でんこうせっか", type=Type.NORMAL, category=Category.STATUS, power=0, accuracy=None)
    rolls = damage_rolls(attacker, defender, status_move, DamageContext())
    assert rolls == [0]
