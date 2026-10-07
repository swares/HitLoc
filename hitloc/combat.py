"""Fighting while wounded: penalties from a fighter's wounds, the optional attack roll,
and severity from the margin of success. Mirrored exactly by the web roller."""
from __future__ import annotations

import math

from .model import Data


def penalties(d: Data, wounds: list[dict], blood_frac: float = 1.0, hand: str = "R") -> dict:
    """wounds: [{loc, fx}] where fx is a composed wound (pain, impair). hand: 'R' or 'L'."""
    C = d.wounds["combat"]
    T = d.wounds["tracking"]
    attack = defence = 0
    notes, flags = [], set()

    pain = min(sum(w["fx"]["pain"] for w in wounds), T["pain_cap"])
    if pain:
        attack += pain * C["pain_step"]
        defence += pain * C["pain_step"]
        notes.append(f"pain -{pain * C['pain_step']}%")

    for th in sorted(T["thresholds"], key=lambda t: t["at"]):
        if blood_frac <= th["at"]:
            if th.get("incapacitated"):
                flags.add("incapacitated")
            p = th.get("penalty", 0)
            attack += p
            defence += p
            if th.get("down"):
                flags.add("down")
            if p:
                notes.append(f"blood loss -{p}%")
            break

    seen = set()
    for w in wounds:
        loc = d.loc[w["loc"]]
        for imp in w["fx"].get("impair", []):
            rule = C["impair"].get(imp, {})
            if "weapon_arm" in rule or "shield_arm" in rule:
                arm = "shield_arm" if loc["zone"] == "arms" and loc["side"] in ("L", "R") and loc["side"] != hand else "weapon_arm"
                key, eff = (imp, arm), rule.get(arm, {})
            else:
                key, eff = (imp, None), rule
            if key in seen:
                continue
            seen.add(key)
            a, df = eff.get("attack", 0), eff.get("defence", 0)
            attack += a
            defence += df
            for f in ("down", "off_hand", "no_shield", "incapacitated"):
                if eff.get(f):
                    flags.add(f)
            if a or df:
                where = f" ({key[1].replace('_', ' ')})" if key[1] else ""
                notes.append(f"{imp.replace('_', ' ')}{where}" + (f" atk -{a}%" if a else "") + (f" def -{df}%" if df else ""))
    if "off_hand" in flags and any(k == ("grip", "shield_arm") or k == ("hand_useless", "shield_arm") or k == ("arm_useless", "shield_arm") for k in seen):
        flags.add("cannot_wield")
    return {"attack": min(attack, C["cap"]), "defence": min(defence, C["cap"]),
            "flags": sorted(flags), "notes": notes}


def auto_situations(d: Data, att: dict | None, dfn: dict | None) -> list[str]:
    A = d.wounds["combat"]["auto_situations"]
    out = []
    if dfn and "down" in dfn["flags"]:
        out.append(A["defender_down"])
    if dfn and "no_shield" in dfn["flags"]:
        out.append(A["defender_no_shield"])
    if att and "down" in att["flags"]:
        out.append(A["attacker_down"])
    return out


def margin_severity(d: Data, margin: int, critical: bool, weapon_id: str, zone: str) -> str:
    if critical:
        return "critical"
    bands = d.wounds["combat"]["margin_bands"]
    b = bands["default"]
    if (d.weapons.get(weapon_id) or {}).get("threat") and "ballistic" in bands:
        b = next(x for x in bands["ballistic"] if zone in x["zones"])
    if margin >= b["critical"]:
        return "critical"
    if margin >= b["serious"]:
        return "serious"
    return "light"


def attack_roll(d: Data, attack: int, roll: int, penalty: int = 0) -> dict:
    eff = max(0, attack - penalty)
    crit_at = math.floor(eff * d.wounds["combat"]["critical_fraction"])
    hit = roll <= eff
    return {"effective": eff, "roll": roll, "hit": hit, "critical": hit and roll <= crit_at,
            "margin": eff - roll if hit else None}


def defence_roll(defence: int, roll: int, penalty: int = 0) -> dict:
    eff = max(0, defence - penalty)
    return {"effective": eff, "roll": roll, "defended": roll <= eff}
