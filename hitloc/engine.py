"""Turn weights into d100 ranges, roll hits, and compose wound effects."""
from __future__ import annotations

import random

from .model import Data, MECHANISMS, resolve_table, slot_layers, available_weapons


# --------------------------------------------------------------------------
# d100 ranges
# --------------------------------------------------------------------------
def to_d100(weights: list[tuple[str, float]]) -> list[dict]:
    """Largest-remainder rounding of weights to 100 slots.

    Returns [{id, pct, lo, hi}] in input order; entries that round to 0 are
    dropped (they cannot appear on a d100 table). 100 is written as 00 in print.
    """
    total = 0.0
    for _, w in weights:          # plain left-to-right sum, as in JavaScript (Python 3.12+
        total += w                # sum() compensates rounding, which can break exact ties)
    raw = [(k, w * 100.0 / total) for k, w in weights]
    floors = {k: int(v) for k, v in raw}
    left = 100 - sum(floors.values())
    # Distribute remaining slots by largest fractional part; ties keep body order.
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i][1] - int(raw[i][1])), i))
    for i in order[:left]:
        floors[raw[i][0]] += 1
    out, lo = [], 1
    for k, _ in weights:
        n = floors[k]
        if n <= 0:
            continue
        out.append({"id": k, "pct": n, "lo": lo, "hi": lo + n - 1})
        lo += n
    assert lo == 101, "d100 ranges must cover 1-100"
    return out


def ordered_mods(d: Data, mods) -> list[str]:
    """Selected modifier ids in data-file order (so stacking is deterministic)."""
    sel = set(mods or [])
    unknown = sel - set(d.modifiers)
    if unknown:
        raise KeyError(f"unknown modifiers {sorted(unknown)}")
    out = [m for m in d.modifiers if m in sel]
    groups = {}
    for m in out:
        g = d.modifiers[m].get("group")
        if g and g in groups:
            raise ValueError(f"modifiers {groups[g]} and {m} are alternatives (group {g}); pick one")
        if g:
            groups[g] = m
    return out


def shield_mods(d: Data, table_id: str, weapon_id: str | None, shield: bool | None) -> list[str]:
    """Situations added for shields. On a table that assumes a shield, a defender known to
    have none (shield=False) gets No shield. With no defender known (shield=None), a weapon
    rolling away from its own table adds its fallback_mods instead."""
    tid = resolve_table(d, table_id, weapon_id) if weapon_id else table_id
    if d.tables[tid]["assumes_shield"] and shield is not None:
        return [] if shield else ["no_shield"]
    if weapon_id and tid != table_id and shield is None:
        return list(d.weapons[weapon_id].get("fallback_mods") or [])
    return []


def effective_weights(d: Data, table_id: str, weapon_id: str | None, mods=None,
                      shield: bool | None = None) -> list[tuple[str, float]]:
    """Table weight x the weapon's multiplier on that table x each modifier (zone, side, loc).

    A close-combat weapon on a table of another kind of fighting uses the melee
    fallback table (resolve_table). The multiplication order is fixed; the web roller
    repeats it exactly, using the same precomputed multipliers, so both produce
    identical d100 ranges.
    """
    tid = resolve_table(d, table_id, weapon_id) if weapon_id else table_id
    t = d.tables[tid]
    mult = d.wmult[tid].get(weapon_id) if weapon_id else None
    if weapon_id and mult is None:
        raise KeyError(f"weapon {weapon_id} is not available on table {table_id}")
    mods = list(mods or [])
    mods += [m for m in shield_mods(d, table_id, weapon_id, shield) if m not in mods]
    ms = [d.modifiers[m] for m in ordered_mods(d, mods)]
    out = []
    for i, loc in enumerate(d.locations):
        v = float(t["weights"].get(loc["id"], 0))
        if mult is not None:
            v *= mult[i]
        for m in ms:
            v *= (m.get("zone") or {}).get(loc["zone"], 1.0)
            v *= (m.get("side") or {}).get(loc["side"], 1.0)
            v *= (m.get("loc") or {}).get(loc["id"], 1.0)
        out.append((loc["id"], v))
    return out


def table_ranges(d: Data, table_id: str, weapon_id: str | None = None, mods=None,
                 shield: bool | None = None) -> list[dict]:
    return to_d100(effective_weights(d, table_id, weapon_id, mods, shield))


def called_odds(d: Data, ranges: list[dict], zone: str | None) -> dict:
    """Exact location chances (%) after the called-shot rule (roll twice, keep the called zone)."""
    p = {r["id"]: r["pct"] / 100.0 for r in ranges}
    if not zone:
        return {k: v * 100 for k, v in p.items()}
    pz = sum(v for k, v in p.items() if d.loc[k]["zone"] == zone)
    out = {}
    for k, v in p.items():
        if d.loc[k]["zone"] == zone:
            out[k] = v * (2 - pz) * 100          # first in zone, or first out and second in
        else:
            out[k] = v * (1 - pz) * 100          # neither in zone: keep the first
    return out


def weapon_mix_ranges(d: Data, table_id: str) -> list[dict]:
    """d100 'what hit them' table from a source's weapon mix. Each row: id (row index),
    label, weapon (id or None), lo, hi, pct."""
    mix = d.tables[table_id].get("weapon_mix") or []
    if not mix:
        return []
    rows = to_d100([(str(i), float(m["pct"])) for i, m in enumerate(mix)])
    for r in rows:
        m = mix[int(r["id"])]
        r["weapon"] = m.get("weapon")
        r["label"] = m.get("label") or d.weapons[m["weapon"]]["name"]
    return rows


def mechanism_ranges(d: Data, weapon_id: str) -> list[dict]:
    mech = d.weapons[weapon_id]["mechanisms"]
    return to_d100([(m, mech[m]) for m in MECHANISMS if mech.get(m)])


def severity_ranges(d: Data, mechanism: str | None = None, zone: str | None = None,
                    weapon_id: str | None = None) -> list[dict]:
    """Default severity table, or the mechanism's table for this body zone if one exists.
    Firearms and explosives (weapons with a threat level) always use the ballistic table,
    whatever the wound mechanism (a blast's crush wounds included)."""
    if weapon_id and (d.weapons.get(weapon_id) or {}).get("threat"):
        mechanism = "ballistic"
    tiers = d.wounds["severity"]["tiers"]
    spec = (d.wounds["severity"].get("by_mechanism") or {}).get(mechanism)
    if spec and zone:
        for tbl in spec["tables"]:
            if zone in tbl["zones"]:
                tiers = tbl["tiers"]
                break
    return [{"id": t["id"], "lo": t["d100"][0], "hi": t["d100"][1]} for t in tiers]


def lookup(ranges: list[dict], roll: int) -> str:
    for r in ranges:
        if r["lo"] <= roll <= r["hi"]:
            return r["id"]
    raise ValueError(f"roll {roll} not on table")


# --------------------------------------------------------------------------
# Wound composition
# --------------------------------------------------------------------------
def _step(order: list[str], value: str, delta: int) -> str:
    i = max(0, min(len(order) - 1, order.index(value) + delta))
    return order[i]


def _matches(when: dict, sev: str, loc: dict, cls: dict) -> bool:
    if "severity" in when and sev not in when["severity"]:
        return False
    if "zone" in when and loc["zone"] not in when["zone"]:
        return False
    if "severable" in when and bool(cls.get("severable")) != when["severable"]:
        return False
    if "bony" in when and bool(cls.get("bony")) != when["bony"]:
        return False
    return True


def compose_wound(d: Data, loc_id: str, mechanism: str, severity: str) -> dict:
    """Class profile for the severity, then mechanism rules on top."""
    W = d.wounds
    loc = d.loc[loc_id]
    cls = W["classes"][loc["class"]]
    base = cls[severity]
    lethal_order = W["vocabulary"]["lethal"]["order"]
    inf_order = W["vocabulary"]["infection"]["order"]

    e = {
        "bleed": base.get("bleed", 0),
        "pain": base.get("pain", 0),
        "lethal": base.get("lethal", "none"),
        "infection": cls.get("infection", "low"),
        "impair": list(base.get("impair", [])),
        "shock": bool(base.get("shock", False)),
        "fracture": bool(base.get("fracture", False)),
        "severed": False,
    }
    for rule in W["mechanisms"][mechanism]["rules"]:
        if not _matches(rule.get("when", {}), severity, loc, cls):
            continue
        if "bleed" in rule:
            e["bleed"] += rule["bleed"]
        if "pain" in rule:
            e["pain"] += rule["pain"]
        if "lethal" in rule:
            # Modifiers never make a wound 'instant' on their own; only a profile can.
            stepped = _step(lethal_order, e["lethal"], rule["lethal"])
            if stepped == "instant" and e["lethal"] != "instant":
                stepped = e["lethal"]
            e["lethal"] = stepped
        if "infection" in rule:
            e["infection"] = _step(inf_order, e["infection"], rule["infection"])
        if "lethal_max" in rule and lethal_order.index(e["lethal"]) > lethal_order.index(rule["lethal_max"]):
            e["lethal"] = rule["lethal_max"]
        for flag in ("shock", "fracture", "severed"):
            if rule.get(flag):
                e[flag] = True
        if "bleed_min" in rule:
            e["bleed"] = max(e["bleed"], rule["bleed_min"])
    e["bleed"] = max(0, min(3, e["bleed"]))
    e["pain"] = max(0, min(3, e["pain"]))
    if e["severed"]:
        e["impair"] = [i for i in e["impair"] if i not in ("grip", "arm")] or e["impair"]
        if loc["zone"] == "arms" and "arm_useless" not in e["impair"] and loc["class"] != "hand":
            e["impair"].append("arm_useless")
        if loc["zone"] == "arms" and loc["class"] == "hand" and "hand_useless" not in e["impair"]:
            e["impair"].append("hand_useless")
        if loc["zone"] == "legs" and "stand" not in e["impair"]:
            e["impair"].append("stand")
        if e["lethal"] in ("none", "days", "hours"):
            e["lethal"] = "minutes"
    return e


def describe(d: Data, e: dict) -> list[str]:
    V = d.wounds["vocabulary"]
    lines = [f"Bleed {e['bleed']}: {V['bleed'][e['bleed']]}",
             f"Pain {e['pain']}: {V['pain'][e['pain']]}"]
    for i in e["impair"]:
        lines.append(f"{i}: {V['impair'][i]}")
    for flag in ("shock", "fracture", "severed"):
        if e[flag]:
            lines.append(f"{flag}: {V['flags'][flag]}")
    lines.append(f"Untreated: {V['lethal'][e['lethal']]}")
    lines.append(f"Infection risk: {e['infection']}")
    return lines


# --------------------------------------------------------------------------
# Armour
# --------------------------------------------------------------------------
SEV_LADDER = ["stopped", "light", "serious", "critical"]


def armor_at(d: Data, kit_id: str | None, loc_id: str) -> list[tuple[str, int, int]]:
    """d100 bands [(material, lo, hi)] protecting this location; rolls above the last band are gaps."""
    if not kit_id:
        return []
    kit = d.armor["kits"][kit_id]
    return slot_layers((kit.get("slots") or {}).get(d.loc[loc_id]["armor"]))


def armor_steps(d: Data, material: str, mechanism: str, weapon_id: str | None) -> int:
    mat = d.armor["materials"][material]
    w = d.weapons.get(weapon_id) or {}
    if mechanism == "ballistic" and w.get("threat") and w["threat"] in (mat.get("threats") or {}):
        steps = mat["threats"][w["threat"]]
    else:
        steps = mat[mechanism]
    defeat = (w.get("armor_defeat") or {}).get(mechanism, 0)
    return max(0, steps - defeat)


def reduce_severity(severity: str, steps: int) -> str:
    return SEV_LADDER[max(0, SEV_LADDER.index(severity) - steps)]


# --------------------------------------------------------------------------
# Roll
# --------------------------------------------------------------------------
def roll_hit(d: Data, table_id: str, weapon_id: str, severity: str | None = None,
             rng: random.Random | None = None, mods=None, called: str | None = None,
             kit: str | None = None, margin: int | None = None, critical: bool = False,
             shield: bool | None = None) -> dict:
    """Roll location, mechanism and severity for a hit. If `margin` is given (from an attack
    roll made with hitloc.combat), severity comes from the margin of success instead."""
    rng = rng or random.Random()
    if kit and kit not in d.armor["kits"]:
        raise KeyError(f"unknown armour kit {kit}")
    if called and called not in d.zones:
        raise KeyError(f"unknown zone {called}")
    if weapon_id not in available_weapons(d, table_id):
        raise KeyError(f"weapon {weapon_id} is not offered on table {table_id}")
    ranges = table_ranges(d, table_id, weapon_id, mods, shield)
    r_loc = rng.randint(1, 100)
    loc_id = lookup(ranges, r_loc)
    r_loc2 = None
    if called:
        r_loc2 = rng.randint(1, 100)
        second = lookup(ranges, r_loc2)
        if d.loc[loc_id]["zone"] != called and d.loc[second]["zone"] == called:
            loc_id = second
    r_mech = rng.randint(1, 100)
    mech = lookup(mechanism_ranges(d, weapon_id), r_mech)
    r_sev = None
    if margin is not None:
        from .combat import margin_severity
        severity = margin_severity(d, margin, critical, weapon_id, d.loc[loc_id]["zone"])
    elif severity is None:
        r_sev = rng.randint(1, 100)
        severity = lookup(severity_ranges(d, mech, d.loc[loc_id]["zone"], weapon_id), r_sev)

    armour = None
    final = severity
    layers = armor_at(d, kit, loc_id)
    if layers:
        whole = len(layers) == 1 and layers[0][1] == 1 and layers[0][2] == 100
        r_cov = None if whole else rng.randint(1, 100)
        hit = layers[0] if whole else next((ly for ly in layers if ly[1] <= r_cov <= ly[2]), None)
        material = hit[0] if hit else None
        steps = armor_steps(d, material, mech, weapon_id) if hit else 0
        final = reduce_severity(severity, steps)
        armour = {"material": material, "layers": layers, "cover_roll": r_cov,
                  "covered": hit is not None, "steps": steps, "from": severity, "to": final}

    return {
        "table": resolve_table(d, table_id, weapon_id),
        "rolls": {"location": r_loc, "location2": r_loc2, "mechanism": r_mech, "severity": r_sev},
        "location": loc_id, "location_name": d.loc[loc_id]["name"],
        "mechanism": mech, "severity": final, "armor": armour,
        "effects": None if final == "stopped" else compose_wound(d, loc_id, mech, final),
    }
