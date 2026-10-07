"""Write the 'all hits' gameplay blends for the early-modern and musket-era tables.

all hits = (1 - k) x wounded table + k x killed table, location by location, where k is
the share of hits that killed outright. Where no region counts of a war's killed survive,
the Civil War killed-in-action table (1,173 men, soft lead balls) stands in for them; where
no wounded records survive (the Thirty Years' War), the Peninsular War records stand in.
Run from the project root after changing a source table:  python tools/blend_tables.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hitloc import model  # noqa: E402

BLENDS = [
    # (output id, wounded table, killed table, killed share)
    ("revolution-1775-83-all-hits", "revolution-1775-83-pensioners", "acw-1861-killed", 0.465),
    ("peninsular-1808-14-all-hits", "peninsular-1808-14-officers", "acw-1861-killed", 0.255),
    ("thirty-years-war-all-hits", "peninsular-1808-14-officers", "lutzen-1632-mass-grave", 0.255),
]


def shares(d, tid):
    w = d.tables[tid]["weights"]
    tot = sum(w.values())
    return {l["id"]: w.get(l["id"], 0) / tot for l in d.locations}


def main():
    d = model.load("data")
    for out, base, killed, k in BLENDS:
        wnd, kill = shares(d, base), shares(d, killed)
        blend = {i: (1 - k) * wnd[i] + k * kill[i] for i in wnd}
        path = Path("data/tables") / f"{out}.yaml"
        text = path.read_text()
        head = text.split("\nweights:\n")[0]
        body = "\n".join(f"  {i}: {round(v * 100, 3)}" for i, v in blend.items())
        path.write_text(head + "\nweights:\n" + body + "\n")
        print(out, {z: round(sum(v for i, v in blend.items() if d.loc[i]["zone"] == z) * 100, 1) for z in d.zones})


if __name__ == "__main__":
    main()
