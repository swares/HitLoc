"""Command line: python -m hitloc roll|list|check"""
from __future__ import annotations

import argparse
import random
import sys

from . import load, DataError
from .engine import roll_hit, describe, table_ranges


def fmt(n: int) -> str:
    return "00" if n == 100 else f"{n:02d}"


def main(argv=None) -> int:
    try:
        return _main(argv)
    except (KeyError, ValueError) as e:
        print("error:", str(e).strip("'\""), file=sys.stderr)
        return 2


def _main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hitloc", description="Historical hit-location roller")
    p.add_argument("--data", default="data", help="data folder (default: data)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("roll", help="roll a hit")
    r.add_argument("--table", required=True)
    r.add_argument("--weapon", required=True)
    r.add_argument("--severity", choices=["light", "serious", "critical"],
                   help="use your system's severity instead of rolling")
    r.add_argument("--seed", type=int)
    r.add_argument("-n", type=int, default=1, help="number of hits")
    r.add_argument("--mod", action="append", default=[], help="situation modifier id (repeatable; they stack)")
    r.add_argument("--called", choices=["head", "torso", "arms", "legs"], help="called shot zone")
    r.add_argument("--armor", help="target armour kit id")
    r.add_argument("--shield", choices=["kit", "yes", "no"],
                   help="does the target carry a shield? 'kit' takes it from --armor; matters on tables that assume one (Visby)")
    r.add_argument("--attack", type=int, help="attack chance %%: roll the attack here; margin of success sets severity")
    r.add_argument("--defence", type=int, help="defender's parry/dodge chance %% (needs --attack)")
    r.add_argument("--att-penalty", type=int, default=0, help="attacker's wound penalty %%")
    r.add_argument("--def-penalty", type=int, default=0, help="defender's wound penalty %%")

    s = sub.add_parser("show", help="print a d100 table")
    s.add_argument("--table", required=True)
    s.add_argument("--weapon")
    s.add_argument("--mod", action="append", default=[], help="situation modifier id (repeatable)")

    sub.add_parser("list", help="list tables and weapons")
    sub.add_parser("check", help="validate the data set")

    a = p.parse_args(argv)
    try:
        d = load(a.data)
    except DataError as e:
        print("Data errors:\n" + str(e), file=sys.stderr)
        return 1

    if a.cmd == "check":
        for w in d.warnings:
            print("warning:", w)
        print(f"OK: {len(d.locations)} locations, {len(d.weapons)} weapons, {len(d.tables)} tables")
    elif a.cmd == "list":
        print("Tables:")
        for t in d.tables.values():
            print(f"  {t['id']:<24} {t['name']}  [{t['confidence']}]")
        print("Weapons:")
        for w in d.weapons.values():
            tag = f"  [threat: {w['threat']}]" if w.get("threat") else (f"  [melee: {w['melee']}]" if w.get("melee") else "")
            print(f"  {w['id']:<24} {w['name']}{tag}")
        print("Modifiers (--mod, stack; one per group):")
        for m in d.modifiers.values():
            g = f"  [group: {m['group']}]" if m.get("group") else ""
            print(f"  {m['id']:<24} {m['name']}{g}")
        print("Armour kits (--armor):")
        for k in d.armor["kits"].values():
            print(f"  {k['id']:<24} {k['name']}")
    elif a.cmd == "show":
        for row in table_ranges(d, a.table, a.weapon, a.mod):
            print(f"  {fmt(row['lo'])}-{fmt(row['hi'])}  {d.loc[row['id']]['name']}")
    elif a.cmd == "roll":
        from .model import resolve_table
        if a.armor and d.tables[resolve_table(d, a.table, a.weapon)]["armor"] == "baked_in":
            print("warning: this table already reflects the armour its source population wore; "
                  "use an all-hits, baseline, knife or unarmed table with --armor", file=sys.stderr)
        rng = random.Random(a.seed)
        from .combat import attack_roll, defence_roll
        for _ in range(a.n):
            margin = crit = None
            if a.attack is not None:
                ar_ = attack_roll(d, a.attack, rng.randint(1, 100), a.att_penalty)
                tag = " CRITICAL" if ar_["critical"] else ""
                print(f"Attack: d100 {fmt(ar_['roll'])} vs {ar_['effective']}% - "
                      + (f"hit, margin {ar_['margin']}{tag}" if ar_["hit"] else "miss"))
                if not ar_["hit"]:
                    continue
                if a.defence is not None and not ar_["critical"]:
                    dr = defence_roll(a.defence, rng.randint(1, 100), a.def_penalty)
                    print(f"Defence: d100 {fmt(dr['roll'])} vs {dr['effective']}% - " + ("defended" if dr["defended"] else "failed"))
                    if dr["defended"]:
                        continue
                margin, crit = ar_["margin"], ar_["critical"]
            shield = None
            if a.shield == "yes":
                shield = True
            elif a.shield == "no":
                shield = False
            elif a.shield == "kit":
                shield = bool((d.armor["kits"].get(a.armor or "none") or {}).get("shield", False))
            h = roll_hit(d, a.table, a.weapon, a.severity, rng, a.mod, a.called, a.armor, margin, bool(crit), shield)
            rl = h["rolls"]
            loc_roll = fmt(rl["location"]) + (f"/{fmt(rl['location2'])}" if rl["location2"] else "")
            sev_roll = f" (d100 {fmt(rl['severity'])})" if rl["severity"] else ""
            ar = h["armor"]
            sev_txt = ar["from"] if ar else h["severity"]
            print(f"{h['location_name']} (d100 {loc_roll}) - "
                  f"{h['mechanism']} (d100 {fmt(rl['mechanism'])}) - {sev_txt}{sev_roll}")
            if h["table"] != a.table:
                print(f"    (close combat: location rolled on {d.tables[h['table']]['name']})")
            if ar:
                cov = f", cover d100 {fmt(ar['cover_roll'])}" if ar["cover_roll"] else ""
                if not ar["covered"]:
                    print(f"    Armour: gap, not covered{cov}")
                else:
                    mat = d.armor["materials"][ar["material"]]["name"]
                    print(f"    Armour: {mat}{cov} - {ar['steps']} step(s): {ar['from']} -> {ar['to']}")
            if h["effects"] is None:
                print("    Stopped by armour: bruise, no wound")
                continue
            for line in describe(d, h["effects"]):
                print("   ", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
