"""Write the 'all hits' gameplay blends for the musket-era tables.

all hits = (1 - k) x wounded table + k x killed table, location by location, where k is
the share of hits that killed outright. No region counts of the killed survive for these
wars, so the Civil War killed-in-action table (1,173 men, soft lead balls) stands in.
Run from the project root after changing a source table:  python tools/blend_tables.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hitloc import model  # noqa: E402

BLENDS = [
    # (output id, wounded table, killed share, header lines)
    ("revolution-1775-83-all-hits", "revolution-1775-83-pensioners", 0.465),
    ("peninsular-1808-14-all-hits", "peninsular-1808-14-officers", 0.255),
]
KILLED = "acw-1861-killed"


def shares(d, tid):
    w = d.tables[tid]["weights"]
    tot = sum(w.values())
    return {l["id"]: w.get(l["id"], 0) / tot for l in d.locations}


def main():
    d = model.load("data")
    kill = shares(d, KILLED)
    for out, base, k in BLENDS:
        wnd = shares(d, base)
        blend = {i: (1 - k) * wnd[i] + k * kill[i] for i in wnd}
        path = Path("data/tables") / f"{out}.yaml"
        text = path.read_text()
        head = text.split("\nweights:\n")[0]
        body = "\n".join(f"  {i}: {round(v * 100, 3)}" for i, v in blend.items())
        path.write_text(head + "\nweights:\n" + body + "\n")
        print(out, {z: round(sum(v for i, v in blend.items() if d.loc[i]["zone"] == z) * 100, 1) for z in d.zones})


if __name__ == "__main__":
    main()
