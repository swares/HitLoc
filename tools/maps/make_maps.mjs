// Builds data/maps.json: one small locator map per conflict, from the `map:` entries in
// data/conflicts.yaml and Natural Earth 1:50m coastlines and borders (public domain, via the
// world-atlas package). Run from this folder after editing a map entry:
//   npm install && node make_maps.mjs
// The output is plain SVG path data, so the roller, start page and PDF need nothing at runtime.
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import yaml from "js-yaml";
import { feature, mesh } from "topojson-client";
import { geoMercator, geoPath } from "d3-geo";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const W = 160, H = 120, MERGE = 9;          // frame (viewBox units) and dot-merge distance
const conflicts = yaml.load(fs.readFileSync(path.join(root, "data/conflicts.yaml"), "utf8")).conflicts;
const atlas = f => JSON.parse(fs.readFileSync(path.join(here, "node_modules/world-atlas", f), "utf8"));
// 1:50m for regional maps, 1:110m for continent-wide ones (keeps their path data small).
const scale = {};
for (const res of ["50m", "110m"]) {
  const lt = atlas(`land-${res}.json`), ct = atlas(`countries-${res}.json`);
  scale[res] = { land: feature(lt, lt.objects.land), countries: feature(ct, ct.objects.countries).features,
                 borders: mesh(ct, ct.objects.countries, (a, b) => a !== b) };
}

const out = {};
for (const [battle, c] of Object.entries(conflicts)) {
  const m = c.map; if (!m) continue;
  const [w, s, e, n] = m.bbox;
  // Polygon wound clockwise in lon/lat so d3 treats it as the box, not the rest of the globe.
  const box = { type: "Feature", geometry: { type: "Polygon", coordinates: [[[w, s], [w, n], [e, n], [e, s], [w, s]]] } };
  const { land, countries, borders } = scale[e - w > 60 ? "110m" : "50m"];
  const proj = geoMercator().fitExtent([[6, 6], [W - 6, H - 6]], box).clipExtent([[0, 0], [W, H]]);
  const p = geoPath(proj).digits(1);
  const missing = (m.highlight || []).filter(name => !countries.some(f => f.properties.name === name));
  if (missing.length) throw new Error(`${battle}: unknown highlight countries ${missing}`);
  const hl = (m.highlight || []).map(name => p(countries.find(f => f.properties.name === name))).join("");
  // Sites closer than MERGE units share one dot (its tooltip lists them all).
  const dots = [];
  for (const site of m.sites || []) {
    const [x, y] = proj([site.lon, site.lat]);
    const near = dots.find(d => Math.hypot(d.x - x, d.y - y) < MERGE);
    if (near) { near.names.push(site.name); near.x = (near.x + x) / 2; near.y = (near.y + y) / 2 }
    else dots.push({ x, y, names: [site.name] });
  }
  out[battle] = {
    spec: m, w: W, h: H, land: p(land) || "", highlight: hl, borders: m.borders ? p(borders) || "" : "",
    dots: dots.map(d => ({ x: +d.x.toFixed(1), y: +d.y.toFixed(1), names: d.names })),
  };
  console.log(battle.padEnd(30), `${Math.round(JSON.stringify(out[battle]).length / 1024)} KB`, `${dots.length} dot(s)`);
}
fs.writeFileSync(path.join(root, "data/maps.json"), JSON.stringify(out, null, 1) + "\n");
console.log("wrote data/maps.json");
