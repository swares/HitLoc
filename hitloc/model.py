"""Load and validate the YAML data set."""
from __future__ import annotations

import re

from dataclasses import dataclass, field
from pathlib import Path

import yaml

MECHANISMS = ("cut", "pierce", "crush", "ballistic")
THREATS = ("fragment", "pistol", "rifle", "rifle_ap")
# Names the combatant figures can draw (templates/figure.js); build.py checks they exist there.
FIG_NAMES = {
    "helmet": ("kettle", "bascinet", "sallet", "closed", "pot", "morion", "coif", "crested", "brodie", "adrian", "stahlhelm",
               "fj", "m1", "japanese", "soviet", "pasgt", "ach", "cap"),
    "hat": ("none", "hood", "broad_hat", "tricorne", "bicorne", "shako", "bearskin", "mitre", "round_hat", "kepi",
            "slouch", "feather", "headband", "czapka", "field_cap", "winter_cap", "pith", "boonie", "turban",
            "shemagh", "balaclava", "beret", "police_cap", "kabalak"),
    "icon": ("sword", "sabre", "dagger", "axe", "club", "spear", "bill", "poleaxe", "lance", "bow", "crossbow", "sling", "long_gun",
             "bayonet_gun", "musket_butt", "modern_rifle", "machine_gun", "smg", "pistol", "launcher", "grenade",
             "stick_grenade", "device", "rammer", "stake", "spade", "fist"),
    "beard": ("none", "stubble", "moustache", "beard"),
    "shield": ("heater", "round"),
}
LOOK_KEYS = ("colour", "trousers", "coat", "hat", "helmet", "beard", "shield")


COMMONS = "https://commons.wikimedia.org/wiki/File:"
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gif", ".webp", ".svg")


def commons_url(file: str) -> str:
    """Wikimedia Commons file page for an example's image (same as commonsUrl in roller.html)."""
    from urllib.parse import quote
    return COMMONS + quote(file.replace(" ", "_"), safe="!'*-._~")


def image_errors(where: str, img) -> list[str]:
    """An example's optional image: a Commons file name and a caption."""
    if img is None:
        return []
    if not isinstance(img, dict) or set(img) - {"file", "caption"}:
        return [f"{where}: image must be {{file, caption}}"]
    f, cap = img.get("file"), img.get("caption")
    errs = []
    if not (isinstance(f, str) and f.strip() and "/" not in f and not f.lower().startswith("file:")
            and f.lower().endswith(IMAGE_EXT)):
        errs.append(f"{where}: image file must be a Wikimedia Commons file name like 'Example.jpg' "
                    f"(no 'File:' prefix, no URL), got {f!r}")
    if not (isinstance(cap, str) and cap.strip()):
        errs.append(f"{where}: image needs a caption saying what it shows")
    return errs


def look_errors(where: str, look) -> list[str]:
    """Problems with a figure `look` (side, example or kit)."""
    if look is None:
        return []
    if not isinstance(look, dict):
        return [f"{where}: look must be a mapping"]
    out = []
    for k, v in look.items():
        if k not in LOOK_KEYS:
            out.append(f"{where}: unknown look key {k} (use {', '.join(LOOK_KEYS)})")
        elif k in ("colour", "trousers") and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(v)):
            out.append(f"{where}: look {k} must be a colour like #2f3f6e")
        elif k == "coat" and v != "skin":
            out.append(f"{where}: look coat can only be skin (bare chest)")
        elif k in FIG_NAMES and v not in FIG_NAMES[k]:
            out.append(f"{where}: look {k} {v} is not one the figures can draw ({', '.join(FIG_NAMES[k])})")
    return out
SEVERITIES = ("light", "serious", "critical")


class DataError(ValueError):
    pass


@dataclass
class Data:
    root: Path
    zones: list
    locations: list            # ordered list of dicts
    loc: dict                  # id -> location
    weapons: dict              # id -> weapon (ordered)
    tables: dict               # id -> table (ordered by file name)
    wounds: dict
    modifiers: dict = field(default_factory=dict)   # id -> modifier (ordered)
    called_shot: dict = field(default_factory=dict)
    armor: dict = field(default_factory=dict)       # materials, slots, kits (id -> kit)
    melee_everywhere: list = field(default_factory=list)
    melee_fallback: dict = field(default_factory=dict)
    conflicts: dict = field(default_factory=dict)   # battle group -> history, sides, examples
    wmult: dict = field(default_factory=dict)       # table id -> weapon id -> [multiplier per location]
    warnings: list = field(default_factory=list)


def _read(path: Path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load(root: str | Path = "data") -> Data:
    root = Path(root)
    body = _read(root / "body.yaml")
    wfile = _read(root / "weapons.yaml")
    weapons = wfile["weapons"]
    wounds = _read(root / "wounds.yaml")
    tables = [_read(p) for p in sorted((root / "tables").glob("*.yaml"))]
    tables.sort(key=lambda t: t.get("order", 999))   # stable: file name breaks ties
    mods = _read(root / "modifiers.yaml") if (root / "modifiers.yaml").exists() else {"modifiers": []}
    armor = _read(root / "armor.yaml") if (root / "armor.yaml").exists() else {"materials": {}, "slots": {}, "kits": []}
    conflicts = (_read(root / "conflicts.yaml") or {}).get("conflicts", {}) if (root / "conflicts.yaml").exists() else {}

    data = Data(
        root=root,
        zones=body["zones"],
        locations=body["locations"],
        loc={l["id"]: l for l in body["locations"]},
        weapons={w["id"]: w for w in weapons},
        tables={t["id"]: t for t in tables},
        wounds=wounds,
        modifiers={m["id"]: m for m in mods.get("modifiers", [])},
        called_shot=mods.get("called_shot", {}),
        armor={**armor, "kits": {k["id"]: k for k in armor.get("kits", [])}},
        melee_everywhere=wfile.get("melee_everywhere", []),
        melee_fallback=wfile.get("melee_fallback", {}),
        conflicts=conflicts,
    )
    for t in data.tables.values():
        if "regions" in t and "weights" not in t:
            t["weights"] = expand_regions(data, t)
        t.setdefault("native", "gunfire")
        t.setdefault("weapon_bias", "raw")
        t.setdefault("armor", "allowed" if t.get("variant") == "adjusted" else "baked_in")
        t.setdefault("assumes_shield", False)
    validate(data)
    compute_multipliers(data)
    return data


# --------------------------------------------------------------------------
# Weapon availability and location multipliers
# --------------------------------------------------------------------------
def available_weapons(d: Data, tid: str) -> list[str]:
    """The table's own weapons, then the close-combat weapons offered everywhere."""
    own = list(d.tables[tid]["weapons"])
    return own + [w for w in d.melee_everywhere if w not in own]


def resolve_table(d: Data, tid: str, wid: str) -> str:
    """Table whose location data a weapon uses: a close-combat weapon on a table of another
    kind of fighting rolls on the era's melee table (melee_fallback)."""
    w, t = d.weapons[wid], d.tables[tid]
    kind = w.get("melee")
    if not kind:
        return tid
    if wid in t["weapons"] and kind in natives(t):
        return tid                                    # the table records this kind of fighting
    if w.get("melee_table"):
        return w["melee_table"]                       # e.g. sword, bayonet -> Visby table
    return tid if kind == t["native"] else d.melee_fallback[kind]


def natives(t: dict) -> set[str]:
    """Kinds of fighting a table's own data records: `native` plus any `also_native`
    (e.g. a Napoleonic table recording musket, sabre and bayonet wounds)."""
    return {t["native"], *(t.get("also_native") or [])}


def sourced(d: Data, t: dict, weapons: list[str]) -> dict:
    """Per-weapon location data from the source (`weapon_regions`): each listed weapon's
    multipliers turn the table's pooled weights into that weapon's own distribution.
    Weapons without their own data use the pooled odds."""
    base = [float(t["weights"].get(l["id"], 0)) for l in d.locations]
    tb = sum(base)
    out = {}
    for w in weapons:
        regs = (t.get("weapon_regions") or {}).get(w)
        if not regs:
            out[w] = [1.0] * len(base)
            continue
        ww = expand_regions(d, {"id": f"{t['id']}:{w}", "regions": regs})
        wv = [float(ww[l["id"]]) for l in d.locations]
        tw = sum(wv)
        out[w] = [(x / tw) / (b / tb) if b > 0 else 0.0 for x, b in zip(wv, base)]
    return out


def raw_bias(d: Data, wid: str) -> list[float]:
    w = d.weapons[wid]
    zb, lb = w.get("zone_bias") or {}, w.get("loc_bias") or {}
    return [float(zb.get(l["zone"], 1.0)) * float(lb.get(l["id"], 1.0)) for l in d.locations]


def recentre(d: Data, t: dict, weapons: list[str]) -> dict:
    """Find per-location corrections c so that the mix-weighted average of every
    weapon's distribution (base x bias x c) equals the source's base distribution."""
    base = [float(t["weights"].get(l["id"], 0)) for l in d.locations]
    tb = sum(base)
    base = [b / tb for b in base]
    mix = [(m["weapon"], float(m["pct"])) for m in t.get("weapon_mix") or [] if m.get("weapon")]
    tm = sum(p for _, p in mix)
    mix = [(w, p / tm) for w, p in mix]
    bias = {w: raw_bias(d, w) for w in set(weapons) | {w for w, _ in mix}}
    c = [1.0] * len(base)
    for _ in range(500):
        avg = [0.0] * len(base)
        for w, p in mix:
            v = [b * x * k for b, x, k in zip(base, bias[w], c)]
            z = sum(v)
            for i, x in enumerate(v):
                avg[i] += p * x / z
        err = max((abs(a - b) for a, b in zip(avg, base) if b > 0), default=0)
        c = [k * (b / a) if a > 0 and b > 0 else k for k, a, b in zip(c, avg, base)]
        if err < 1e-12:
            break
    else:
        d.warnings.append(f"tables/{t['id']}: weapon re-centring did not fully converge (max error {err:.2e})")
    return {w: [x * k for x, k in zip(bias[w], c)] for w in weapons}


def compute_multipliers(d: Data) -> None:
    need = {tid: set() for tid in d.tables}
    for tid in d.tables:
        for wid in available_weapons(d, tid):
            need[resolve_table(d, tid, wid)].add(wid)
    for tid, t in d.tables.items():
        ws = sorted(need[tid])
        mode = t["weapon_bias"]
        if mode == "pooled":
            d.wmult[tid] = {w: [1.0] * len(d.locations) for w in ws}
        elif mode == "recentred":
            d.wmult[tid] = recentre(d, t, ws)
        elif mode == "sourced":
            d.wmult[tid] = sourced(d, t, ws)
        else:
            d.wmult[tid] = {w: raw_bias(d, w) for w in ws}


def slot_layers(v) -> list[tuple[str, int, int]]:
    """Normalise a kit slot to [(material, lo, hi)] d100 bands; anything above the last hi is a gap."""
    if v is None:
        return []
    if isinstance(v, str):
        return [(v, 1, 100)]
    items = v if isinstance(v, list) else [v]
    out, lo = [], 1
    for i, it in enumerate(items):
        cover = int(it.get("cover", 101 - lo))
        if cover < 1:
            raise ValueError("cover must be at least 1")
        out.append((it["material"], lo, lo + cover - 1))
        lo += cover
    return out


def region_value(r: dict) -> float:
    return float(r["pct"] if "pct" in r else r["count"])


def expand_regions(d: Data, t: dict) -> dict:
    """Turn a source's coarse region totals into location weights.

    Each region: {pct or count, zone: <zone> | locs: [ids], split: {id: share} (optional)}.
    Counts (raw case numbers from a source) are normalised; percentages should sum to ~100.
    Without a split, the region's pct is shared by the locations' body.yaml exposure.
    """
    w = {l["id"]: 0.0 for l in d.locations}
    for r in t["regions"]:
        if "zone" in r:
            ids = [l["id"] for l in d.locations if l["zone"] == r["zone"]]
        else:
            ids = list(r["locs"])
        unknown = [i for i in ids if i not in d.loc] + [i for i in (r.get("split") or {}) if i not in ids]
        if unknown:
            raise DataError(f"tables/{t['id']}: region {r.get('label', r)} has unknown or out-of-region locations {unknown}")
        share = r.get("split") or {i: d.loc[i].get("exposure", 1.0) for i in ids}
        tot = sum(share.values())
        for i in ids:
            w[i] += region_value(r) * share.get(i, 0) / tot
    total = sum(region_value(x) for x in t["regions"]) + float(t.get("excluded_pct", 0))
    uses_pct = any("pct" in x for x in t["regions"])
    if uses_pct and any("count" in x for x in t["regions"]):
        raise DataError(f"tables/{t['id']}: regions mix pct and count")
    if uses_pct and abs(total - 100) > 2.0:   # sources often round to whole percents
        d.warnings.append(f"tables/{t['id']}: region totals sum to {total:g}%, normalised to 100")
    return w


def validate(d: Data) -> None:
    errors, warn = [], d.warnings
    classes = d.wounds["classes"]

    # body map
    ids = [l["id"] for l in d.locations]
    if len(ids) != len(set(ids)):
        errors.append("body.yaml: duplicate location ids")
    for l in d.locations:
        if l["zone"] not in d.zones:
            errors.append(f"body.yaml: {l['id']} has unknown zone {l['zone']}")
        if l["class"] not in classes:
            errors.append(f"body.yaml: {l['id']} has class {l['class']} missing from wounds.yaml")

    # wound classes
    for cid, c in classes.items():
        for sev in SEVERITIES:
            if sev not in c:
                errors.append(f"wounds.yaml: class {cid} missing severity {sev}")

    # weapons
    for wid, w in d.weapons.items():
        mech = w.get("mechanisms", {})
        bad = set(mech) - set(MECHANISMS)
        if bad:
            errors.append(f"weapons.yaml: {wid} unknown mechanisms {sorted(bad)}")
        if sum(mech.values()) != 100:
            errors.append(f"weapons.yaml: {wid} mechanisms sum to {sum(mech.values())}, not 100")
        for z in w.get("zone_bias", {}):
            if z not in d.zones:
                errors.append(f"weapons.yaml: {wid} zone_bias has unknown zone {z}")
        for lid in w.get("loc_bias", {}) or {}:
            if lid not in d.loc:
                errors.append(f"weapons.yaml: {wid} loc_bias has unknown location {lid}")

    # tables
    for tid, t in d.tables.items():
        w = t.get("weights", {})
        unknown = set(w) - set(d.loc)
        if unknown:
            errors.append(f"tables/{tid}: unknown locations {sorted(unknown)}")
        missing = set(d.loc) - set(w)
        if missing:
            warn.append(f"tables/{tid}: no weight for {sorted(missing)} (treated as 0)")
        if any(v < 0 for v in w.values()):
            errors.append(f"tables/{tid}: negative weight")
        if sum(w.values()) <= 0:
            errors.append(f"tables/{tid}: weights sum to zero")
        for wid in t.get("weapons", []):
            if wid not in d.weapons:
                errors.append(f"tables/{tid}: unknown weapon {wid}")

    # modifiers
    sides = {"L", "R", "C"}
    for mid, m in d.modifiers.items():
        for z in m.get("zone", {}) or {}:
            if z not in d.zones:
                errors.append(f"modifiers.yaml: {mid} unknown zone {z}")
        for sd in m.get("side", {}) or {}:
            if sd not in sides:
                errors.append(f"modifiers.yaml: {mid} unknown side {sd}")
        for lid in m.get("loc", {}) or {}:
            if lid not in d.loc:
                errors.append(f"modifiers.yaml: {mid} unknown location {lid}")
        for part in ("zone", "side", "loc"):
            if any(v < 0 for v in (m.get(part) or {}).values()):
                errors.append(f"modifiers.yaml: {mid} negative multiplier")

    # armour
    mats, slots = d.armor.get("materials", {}), d.armor.get("slots", {})
    for mid, mat in mats.items():
        for mech in MECHANISMS:
            if not isinstance(mat.get(mech), int) or not 0 <= mat[mech] <= 3:
                errors.append(f"armor.yaml: material {mid} needs {mech} steps 0-3")
    body_slots = {l["armor"] for l in d.locations}
    for s_ in body_slots - set(slots):
        warn.append(f"armor.yaml: body slot {s_} not listed under slots")
    for mid, mat in mats.items():
        for th, v in (mat.get("threats") or {}).items():
            if th not in THREATS or not isinstance(v, int) or not 0 <= v <= 3:
                errors.append(f"armor.yaml: material {mid} threat {th} must be one of {THREATS} with steps 0-3")
    for kid, kit in d.armor.get("kits", {}).items():
        for slot, v in (kit.get("slots") or {}).items():
            if slot not in body_slots:
                errors.append(f"armor.yaml: kit {kid} unknown slot {slot}")
            try:
                layers = slot_layers(v)
            except (TypeError, KeyError, ValueError) as e:
                errors.append(f"armor.yaml: kit {kid} slot {slot}: {e}")
                continue
            for mat, lo, hi in layers:
                if mat not in mats:
                    errors.append(f"armor.yaml: kit {kid} unknown material {mat}")
            if layers and layers[-1][2] > 100:
                errors.append(f"armor.yaml: kit {kid} slot {slot} layers exceed 100%")
    for wid, w in d.weapons.items():
        if w.get("threat") and w["threat"] not in THREATS:
            errors.append(f"weapons.yaml: {wid} threat must be one of {THREATS}")
        if w.get("mechanisms", {}).get("ballistic") and not w.get("threat"):
            errors.append(f"weapons.yaml: {wid} has a ballistic mechanism but no threat level")
    for wid, w in d.weapons.items():
        for mech in (w.get("armor_defeat") or {}):
            if mech not in MECHANISMS:
                errors.append(f"weapons.yaml: {wid} armor_defeat unknown mechanism {mech}")

    for kind, tid in d.melee_fallback.items():
        if tid not in d.tables:
            errors.append(f"weapons.yaml: melee_fallback {kind} -> unknown table {tid}")
        elif d.tables[tid]["native"] != kind:
            errors.append(f"weapons.yaml: melee_fallback {kind} -> {tid}, whose native fighting is {d.tables[tid]['native']}")
    for wid in d.melee_everywhere:
        if wid not in d.weapons or not d.weapons[wid].get("melee"):
            errors.append(f"weapons.yaml: melee_everywhere {wid} must be a weapon with a melee kind")
    for wid, w in d.weapons.items():
        mt = w.get("melee_table")
        if mt and (mt not in d.tables or w.get("melee") not in natives(d.tables[mt])):
            errors.append(f"weapons.yaml: {wid} melee_table {mt} must be a table whose native fighting is {w.get('melee')}")
        for m in w.get("fallback_mods") or []:
            if m not in d.modifiers:
                errors.append(f"weapons.yaml: {wid} fallback_mods names unknown situation {m}")
            elif mt and m not in (d.tables[mt].get("modifiers") or []):
                errors.append(f"weapons.yaml: {wid} fallback_mods {m} is not offered on {mt}")
        if w.get("melee") and w["melee"] not in ("armed", "unarmed"):
            errors.append(f"weapons.yaml: {wid} melee must be armed or unarmed")
    for wid, w in d.weapons.items():
        if w.get("icon") and w["icon"] not in FIG_NAMES["icon"]:
            errors.append(f"weapons.yaml: {wid} icon {w['icon']} is not one the figures can draw")
    for kid, kit in d.armor.get("kits", {}).items():
        errors += look_errors(f"armor.yaml: kit {kid}", kit.get("look"))
    for kid, kit in d.armor.get("kits", {}).items():
        if "shield" in kit and not isinstance(kit["shield"], bool):
            errors.append(f"armor.yaml: kit {kid} shield must be true or false")
    for tid, t in d.tables.items():
        if t["assumes_shield"] and "no_shield" not in (t.get("modifiers") or []):
            errors.append(f"tables/{tid}: assumes_shield needs the no_shield situation in its modifiers")
    # conflict histories
    battles = {t.get("battle") for t in d.tables.values()}
    for b in sorted(battles - set(d.conflicts)):
        warn.append(f"conflicts.yaml: no history for table group '{b}'")
    for b, c in d.conflicts.items():
        if b not in battles:
            errors.append(f"conflicts.yaml: '{b}' matches no table's battle group")
        offered = set(d.melee_everywhere)
        for t in d.tables.values():
            if t.get("battle") == b:
                offered |= set(t["weapons"])
        sides = {sd["name"] for sd in c.get("sides") or []}
        for mp in (c.get("map") if isinstance(c.get("map"), list) else [c.get("map")]):
            if mp is None:
                continue
            bb = mp.get("bbox") if isinstance(mp, dict) else None
            if not (isinstance(bb, list) and len(bb) == 4 and bb[0] < bb[2] and bb[1] < bb[3]
                    and -180 <= bb[0] and bb[2] <= 180 and -90 <= bb[1] and bb[3] <= 90):
                errors.append(f"conflicts.yaml: {b} map bbox must be [west, south, east, north] in degrees")
            for site in (mp.get("sites") or []) if isinstance(mp, dict) else []:
                if not (isinstance(site, dict) and site.get("name") and -90 <= float(site.get("lat", 999)) <= 90
                        and -180 <= float(site.get("lon", 999)) <= 180):
                    errors.append(f"conflicts.yaml: {b} map site {site} needs name, lat and lon")
        for sd in c.get("sides") or []:
            errors += look_errors(f"conflicts.yaml: {b} side {sd['name']}", sd.get("look"))
        for ex in c.get("examples") or []:
            errors += look_errors(f"conflicts.yaml: {b} example {ex['name']}", ex.get("look"))
            errors += image_errors(f"conflicts.yaml: {b} example {ex['name']}", ex.get("image"))
            if ex["kit"] not in d.armor["kits"]:
                errors.append(f"conflicts.yaml: {b} example '{ex['name']}' has unknown kit {ex['kit']}")
            if ex["weapon"] not in d.weapons:
                errors.append(f"conflicts.yaml: {b} example '{ex['name']}' has unknown weapon {ex['weapon']}")
            elif ex.get("elsewhere"):
                if not any(ex["weapon"] in t["weapons"] for t in d.tables.values()):
                    errors.append(f"conflicts.yaml: {b} example '{ex['name']}' is marked elsewhere but no table offers {ex['weapon']}")
            elif ex["weapon"] not in offered:
                warn.append(f"conflicts.yaml: {b} example '{ex['name']}' carries {ex['weapon']}, which no table in the group offers")
            if sides and ex.get("side") not in sides:
                errors.append(f"conflicts.yaml: {b} example '{ex['name']}' names unknown side {ex.get('side')}")
        covered = {ex.get("side") for ex in c.get("examples") or []}
        for sd in sorted(sides - covered):
            errors.append(f"conflicts.yaml: {b} side '{sd}' has no example combatant")
    seen = {}
    for tid, t in d.tables.items():
        if t["native"] not in ("armed", "unarmed", "gunfire"):
            errors.append(f"tables/{tid}: native must be armed, unarmed or gunfire")
        if t["weapon_bias"] not in ("raw", "recentred", "pooled", "sourced"):
            errors.append(f"tables/{tid}: weapon_bias must be raw, recentred, pooled or sourced")
        for k in t.get("also_native") or []:
            if k not in ("armed", "unarmed", "gunfire") or k == t["native"]:
                errors.append(f"tables/{tid}: also_native {k} must be another of armed, unarmed, gunfire")
        for wid, regs in (t.get("weapon_regions") or {}).items():
            if wid not in t["weapons"]:
                errors.append(f"tables/{tid}: weapon_regions for {wid}, which the table does not list")
                continue
            try:
                ww = expand_regions(d, {"id": f"{tid}:{wid}", "regions": regs})
            except DataError as e:
                errors.append(str(e)); continue
            gaps = [l for l, v in ww.items() if v > 0 and not t["weights"].get(l)]
            if gaps:
                errors.append(f"tables/{tid}: {wid} has hits at {gaps}, where the pooled table has none")
        if t.get("weapon_regions") and t["weapon_bias"] != "sourced":
            errors.append(f"tables/{tid}: weapon_regions needs weapon_bias: sourced")
        if t["armor"] not in ("allowed", "baked_in"):
            errors.append(f"tables/{tid}: armor must be allowed or baked_in")
        if t["weapon_bias"] == "recentred" and not any(m.get("weapon") for m in t.get("weapon_mix") or []):
            errors.append(f"tables/{tid}: recentred needs a weapon_mix that names weapons")
        for m in t.get("weapon_mix") or []:
            if m.get("weapon") and m["weapon"] not in d.weapons:
                errors.append(f"tables/{tid}: weapon_mix names unknown weapon {m['weapon']}")
            if not m.get("weapon") and not m.get("label"):
                errors.append(f"tables/{tid}: weapon_mix entries need a weapon or a label")
        key = (t.get("battle"), t.get("label", t["name"]))
        if key in seen:
            errors.append(f"tables/{tid}: label '{key[1]}' duplicates {seen[key]} in group '{key[0]}'")
        seen[key] = tid
    for tid, t in d.tables.items():
        mix = t.get("weapon_mix") or []
        if mix and abs(sum(m["pct"] for m in mix) - 100) > 1:
            errors.append(f"tables/{tid}: weapon_mix must sum to 100")
        for mid in t.get("modifiers") or []:
            if mid not in d.modifiers:
                errors.append(f"tables/{tid}: unknown modifier {mid}")
    for mech, spec in (d.wounds["severity"].get("by_mechanism") or {}).items():
        if mech not in MECHANISMS:
            errors.append(f"wounds.yaml: severity table for unknown mechanism {mech}")
        covered = [z for tbl in spec["tables"] for z in tbl["zones"]]
        if sorted(covered) != sorted(d.zones):
            errors.append(f"wounds.yaml: {mech} severity tables must cover each zone once")
        for tbl in spec["tables"]:
            nums = sorted(n for t in tbl["tiers"] for n in range(t["d100"][0], t["d100"][1] + 1))
            if nums != list(range(1, 101)):
                errors.append(f"wounds.yaml: {mech} severity table {tbl['zones']} must cover 1-100 exactly once")
    for m in MECHANISMS:
        if m not in d.wounds["mechanisms"]:
            errors.append(f"wounds.yaml: no rules for mechanism {m}")

    if errors:
        raise DataError("\n".join(errors))
