/* Combatant figures: a small flat SVG drawn from an armour kit, a weapon and a "look".
   Same front view as the hit-location chart (the figure's right is on the viewer's left).
   Everything comes from the data:
     armour   - the kit's slots and coverage (armor.yaml); kit.look.helmet names a helmet shape
     weapon   - the weapon's `icon` (weapons.yaml)
     look     - side defaults merged with the example's own (conflicts.yaml):
                colour (coat), trousers, coat: skin (bare chest), hat (when no helmet),
                helmet (overrides the kit's shape), beard (moustache | beard | stubble)
   Partial coverage ("greaves on 50%") is drawn as that share of the body part: a visual
   shorthand for "half the hits there meet armour". */
const FIG = (() => {
  const SKIN = "#d9a77c", SKIN_DARK = "#b9855b", INK = "#2a2f35";
  // --- body geometry (viewBox 0 0 120 230) ------------------------------------------
  const SLOT_BOX = {               // [x, y, w, h]: the area each slot's coverage is measured over
    helm: [44, 10, 32, 22], visor: [48, 22, 24, 18], gorget: [52, 40, 16, 12],
    torso_upper: [38, 50, 44, 42], torso_lower: [40, 92, 40, 26], skirt: [38, 118, 44, 16],
    pauldron: [26, 48, 68, 18], arm: [20, 62, 80, 62], gauntlet: [18, 124, 84, 14],
    leg: [42, 134, 36, 48], greave: [42, 182, 36, 26], sabaton: [38, 208, 44, 10],
  };
  const PARTS = {
    torso_upper: ["M38 52 Q60 46 82 52 L80 92 L40 92 Z"],
    torso_lower: ["M40 92 L80 92 L80 118 L40 118 Z"],
    skirt: ["M40 118 L80 118 L82 134 L38 134 Z"],
    gorget: ["M52 40 L68 40 L70 52 L50 52 Z"],
    pauldron: ["M26 60 Q28 48 40 50 L40 64 Q32 66 26 60 Z", "M94 60 Q92 48 80 50 L80 64 Q88 66 94 60 Z"],
    arm: ["M26 62 L36 62 L35 94 L25 94 Z", "M84 62 L94 62 L95 94 L85 94 Z",
          "M25 94 L35 94 L33 124 L23 124 Z", "M85 94 L95 94 L97 124 L87 124 Z"],
    leg: ["M42 134 L59 134 L58 182 L44 182 Z", "M61 134 L78 134 L76 182 L62 182 Z"],
    greave: ["M44 182 L58 182 L57 208 L45 208 Z", "M62 182 L76 182 L75 208 L63 208 Z"],
  };
  const COAT = "M38 52 Q60 46 82 52 L82 134 L38 134 Z";
  const HANDS = [[28, 130], [92, 130]];
  const FEET = ["M42 208 L58 208 L60 216 L38 216 Z", "M62 208 L78 208 L82 216 L60 216 Z"];

  // --- materials ------------------------------------------------------------------------
  const MAT = {
    padded: "url(#fg-quilt)", leather: "#7d5530", buff_coat: "#c39a5e",
    mail: "url(#fg-mail)", mail_padded: "url(#fg-mail)", plates: "url(#fg-plates)",
    plate: "url(#fg-steel)", cuirass: "url(#fg-steel)", steel_vest: "url(#fg-steel)", sappenpanzer: "url(#fg-steel)",
    steel_helmet: "#5d6449", cavalry_helmet: "url(#fg-brass)",
    flak_steel: "url(#fg-flak)", nylon_flak: "url(#fg-flak)", doron: "url(#fg-flak)",
    kevlar_soft: "#6e6a4c", kevlar_helmet: "#6e6a4c", sapi: "url(#fg-carrier)", esapi: "url(#fg-carrier)",
  };
  const DEFS = `<defs>
    <pattern id="fg-mail" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#9aa3ad"/><circle cx="2" cy="2" r="1.4" fill="none" stroke="#5c646e" stroke-width=".7"/></pattern>
    <pattern id="fg-quilt" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="#d8c8a2"/><path d="M0 6 L6 0 M0 0 L6 6" stroke="#a8966d" stroke-width=".6"/></pattern>
    <pattern id="fg-plates" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#6d2c2c"/><circle cx="4" cy="4" r="1" fill="#d5bd70"/></pattern>
    <pattern id="fg-flak" width="5" height="5" patternUnits="userSpaceOnUse"><rect width="5" height="5" fill="#5f6a3c"/><path d="M0 0 V5" stroke="#4b5430" stroke-width=".8"/></pattern>
    <pattern id="fg-carrier" width="10" height="8" patternUnits="userSpaceOnUse"><rect width="10" height="8" fill="#a68d5d"/><rect x="1" y="1" width="8" height="5" rx="1" fill="#8f784c"/></pattern>
    <linearGradient id="fg-steel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e3e8ec"/><stop offset=".55" stop-color="#a9b3bc"/><stop offset="1" stop-color="#7c8792"/></linearGradient>
    <linearGradient id="fg-brass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f0d488"/><stop offset="1" stop-color="#a7822f"/></linearGradient>
  </defs>`;
  const st = `stroke="${INK}" stroke-width=".8"`;

  // --- helmets (armour): shape by kit/example look, else by the helm slot's material ----
  const HELMETS = {
    kettle: `<path d="M44 26 Q44 8 60 8 Q76 8 76 26 Z" fill="url(#fg-steel)" ${st}/><path d="M36 27 Q60 20 84 27 L84 30 Q60 24 36 30 Z" fill="url(#fg-steel)" ${st}/>`,
    bascinet: `<path d="M44 30 Q42 4 60 2 Q78 4 76 30 L72 30 Q70 16 60 16 Q50 16 48 30 Z" fill="url(#fg-steel)" ${st}/>`,
    sallet: `<path d="M40 34 Q42 6 60 4 Q78 6 80 34 L74 31 Q72 18 60 18 Q48 18 46 31 Z" fill="url(#fg-steel)" ${st}/><path d="M47 22 H73" stroke="#3a4148" stroke-width="1.4"/>`,
    closed: `<path d="M44 40 Q42 6 60 4 Q78 6 76 40 Z" fill="url(#fg-steel)" ${st}/><path d="M50 24 H70 M50 28 H70" stroke="#3a4148" stroke-width="1.6"/>`,
    pot: `<path d="M45 27 Q45 9 60 9 Q75 9 75 27 Z" fill="url(#fg-steel)" ${st}/><path d="M45 26 L42 38 L48 38 Z M75 26 L78 38 L72 38 Z" fill="url(#fg-steel)" ${st}/><rect x="58" y="24" width="4" height="14" fill="#7c8792"/>`,
    morion: `<path d="M44 26 Q46 10 60 10 Q74 10 76 26 Z" fill="url(#fg-steel)" ${st}/><path d="M60 3 Q66 8 64 12 L56 12 Q54 8 60 3 Z" fill="url(#fg-steel)" ${st}/><path d="M36 28 Q48 22 60 26 Q72 22 84 28 Q72 25 60 29 Q48 25 36 28 Z" fill="url(#fg-steel)" ${st}/>`,
    coif: `<path d="M43 30 Q42 8 60 8 Q78 8 77 30 L77 46 Q60 54 43 46 Z" fill="url(#fg-mail)" ${st}/><ellipse cx="60" cy="31" rx="10" ry="12" fill="${SKIN}"/>`,
    crested: `<path d="M45 27 Q45 9 60 9 Q75 9 75 27 Z" fill="url(#fg-brass)" stroke="#7b5f1e" stroke-width=".8"/><path d="M50 10 Q60 0 74 8 Q66 6 58 12 Z" fill="#2b2b2b"/><path d="M45 26 Q60 22 75 26" fill="none" stroke="#7b5f1e" stroke-width="1.6"/>`,
    brodie: `<path d="M46 24 Q46 11 60 11 Q74 11 74 24 Z" fill="#5d6449" ${st}/><path d="M37 25 Q60 18 83 25 L81 28 Q60 22 39 28 Z" fill="#5d6449" ${st}/>`,
    adrian: `<path d="M45 25 Q45 10 60 10 Q75 10 75 25 Z" fill="#6f7560" ${st}/><path d="M58 6 Q60 4 62 6 L62 11 L58 11 Z" fill="#6f7560" ${st}/><path d="M40 26 Q60 20 80 26 L79 28 Q60 23 41 28 Z" fill="#6f7560" ${st}/>`,
    stahlhelm: `<path d="M44 26 Q43 8 60 8 Q77 8 76 26 L78 34 L72 34 L71 27 Q60 24 49 27 L48 34 L42 34 Z" fill="#5a5f55" ${st}/>`,
    fj: `<path d="M45 29 Q44 9 60 9 Q76 9 75 29 Q60 26 45 29 Z" fill="#5a5f55" ${st}/>`,
    m1: `<path d="M44 29 Q43 9 60 9 Q77 9 76 29 Q60 25 44 29 Z" fill="#5d6449" ${st}/>`,
    japanese: `<path d="M45 27 Q45 9 60 9 Q75 9 75 27 Q60 24 45 27 Z" fill="#6b6a42" ${st}/><path d="M60 13 l1 2 2 .2 -1.6 1.3 .6 2 -2-1.2 -2 1.2 .6-2 -1.6-1.3 2-.2 Z" fill="#d6b44a"/>`,
    soviet: `<path d="M44 30 Q43 8 60 8 Q77 8 76 30 Q60 26 44 30 Z" fill="#4f5a3a" ${st}/>`,
    pasgt: `<path d="M43 33 Q42 8 60 8 Q78 8 77 33 L72 33 L72 27 Q60 24 48 27 L48 33 Z" fill="#6e6a4c" ${st}/>`,
    ach: `<path d="M44 31 Q43 8 60 8 Q77 8 76 31 L72 31 L72 26 Q60 23 48 26 L48 31 Z" fill="#7a7354" ${st}/><rect x="56" y="10" width="8" height="5" rx="1" fill="#3a3a3a"/>`,
    cap: `<path d="M46 22 Q46 11 60 11 Q74 11 74 22 Z" fill="#d8c8a2" stroke="#a8966d" stroke-width=".8"/>`,
  };
  const HELM_BY_MAT = { plate: "kettle", mail: "coif", mail_padded: "coif", padded: "cap", leather: "cap",
                        steel_helmet: "m1", kevlar_helmet: "pasgt", cavalry_helmet: "crested" };

  // --- hats (cloth headgear, drawn when the kit has no helmet); c = coat colour --------
  const HATS = {
    none: c => "",
    hood: c => `<path d="M42 32 Q40 6 60 6 Q80 6 78 32 L80 50 Q60 56 40 50 Z" fill="${shade(c, -.15)}" ${st}/><ellipse cx="60" cy="30" rx="10.5" ry="12" fill="${SKIN}"/>`,
    broad_hat: c => `<ellipse cx="60" cy="19" rx="23" ry="4.5" fill="#3a3530" ${st}/><path d="M48 18 Q48 6 60 6 Q72 6 72 18 Z" fill="#3a3530" ${st}/><path d="M70 12 Q84 2 90 12 Q80 8 72 15 Z" fill="#e8e4d8"/>`,
    tricorne: c => `<path d="M38 20 Q60 8 82 20 L76 23 Q60 15 44 23 Z" fill="#1f1f1f" ${st}/><path d="M47 18 Q49 8 60 8 Q71 8 73 18 Z" fill="#1f1f1f"/><path d="M38 20 Q60 26 82 20" fill="none" stroke="#e8e4d8" stroke-width="1"/>`,
    bicorne: c => `<path d="M36 20 Q60 2 84 20 Q60 14 36 20 Z" fill="#1f1f1f" ${st}/><circle cx="60" cy="14" r="2.4" fill="#c73a3a"/>`,
    shako: c => `<path d="M48 18 L50 0 L70 0 L72 18 Z" fill="#1f1f1f" ${st}/><path d="M46 18 Q60 22 74 18 L74 21 Q60 25 46 21 Z" fill="#1f1f1f"/><circle cx="60" cy="9" r="3" fill="#d6b44a"/><path d="M60 0 V-6" stroke="#e8e4d8" stroke-width="3"/>`,
    bearskin: c => `<path d="M46 20 Q44 -6 60 -8 Q76 -6 74 20 Z" fill="#1c1a18" ${st}/><path d="M50 18 L70 18 L70 13 L50 13 Z" fill="#d6b44a"/>`,
    mitre: c => `<path d="M47 20 L60 -6 L73 20 Z" fill="url(#fg-brass)" stroke="#7b5f1e" stroke-width=".8"/><path d="M47 20 Q60 23 73 20" fill="none" stroke="${c}" stroke-width="3"/>`,
    round_hat: c => `<ellipse cx="60" cy="19" rx="18" ry="3.6" fill="#2f2a26" ${st}/><path d="M49 18 Q49 7 60 7 Q71 7 71 18 Z" fill="#2f2a26" ${st}/>`,
    kepi: c => `<path d="M48 21 L50 7 Q60 4 71 8 L72 21 Z" fill="${c}" ${st}/><path d="M47 20 Q60 23 73 20 L73 22 Q60 25 47 22 Z" fill="#1f1f1f"/><path d="M47 22 Q40 22 44 26 Q52 24 60 23" fill="#1f1f1f"/>`,
    slouch: c => `<ellipse cx="60" cy="18" rx="22" ry="4.5" fill="${shade(c, -.25)}" ${st}/><path d="M48 18 Q47 6 60 5 Q73 6 72 18 Z" fill="${shade(c, -.25)}" ${st}/><path d="M48 16 Q60 19 72 16" fill="none" stroke="#1f1f1f" stroke-width="1.6"/>`,
    feather: c => `<path d="M46 20 Q60 16 74 20 L74 23 Q60 19 46 23 Z" fill="#a23b2a"/><path d="M68 18 Q78 0 72 -6 Q70 6 66 18 Z" fill="#f2efe6" ${st}/><path d="M72 -6 L70 2" stroke="#1f1f1f" stroke-width="2"/>`,
    headband: c => `<path d="M45 20 Q60 15 75 20 L75 24 Q60 19 45 24 Z" fill="#b8402e"/><path d="M46 20 Q47 9 60 9 Q73 9 74 20 Q60 15 46 20 Z" fill="#1f1a17"/>`,
    czapka: c => `<path d="M48 20 L50 8 L44 2 L76 2 L70 8 L72 20 Z" fill="${shade(c, -.1)}" ${st}/><path d="M47 20 Q60 23 73 20 L73 22 Q60 25 47 22 Z" fill="#1f1f1f"/>`,
    field_cap: c => `<path d="M47 21 Q47 9 60 9 Q73 9 73 21 Z" fill="${c}" ${st}/><path d="M47 21 Q60 24 73 21 L73 23 Q60 26 47 23 Z" fill="${shade(c, -.3)}"/><path d="M48 23 Q42 25 46 27 Q54 25 60 25" fill="${shade(c, -.4)}"/><circle cx="60" cy="16" r="1.8" fill="#c73a3a"/>`,
    winter_cap: c => `<path d="M45 26 Q44 8 60 8 Q76 8 75 26 Z" fill="${shade(c, -.1)}" ${st}/><path d="M45 22 L42 36 L49 36 L49 24 Z M75 22 L78 36 L71 36 L71 24 Z" fill="${shade(c, -.1)}" ${st}/><circle cx="60" cy="15" r="1.8" fill="#c73a3a"/>`,
    pith: c => `<path d="M44 24 Q44 6 60 6 Q76 6 76 24 Z" fill="#5f6b3a" ${st}/><ellipse cx="60" cy="24" rx="19" ry="3.5" fill="#5f6b3a" ${st}/><circle cx="60" cy="15" r="2" fill="#c73a3a"/>`,
    boonie: c => `<ellipse cx="60" cy="20" rx="19" ry="4" fill="${shade(c, -.1)}" ${st}/><path d="M48 20 Q48 9 60 9 Q72 9 72 20 Z" fill="${shade(c, -.1)}" ${st}/>`,
    turban: c => `<path d="M44 24 Q42 8 60 7 Q78 8 76 24 Q60 20 44 24 Z" fill="#2b2b2b" ${st}/><path d="M46 14 Q60 10 74 16 M45 19 Q60 14 75 21" fill="none" stroke="#4a4a4a" stroke-width="1.4"/>`,
    shemagh: c => `<path d="M43 34 Q41 7 60 7 Q79 7 77 34 L80 52 Q60 58 40 52 Z" fill="url(#fg-shemagh)" ${st}/><ellipse cx="60" cy="29" rx="9.5" ry="9" fill="${SKIN}"/>`,
    balaclava: c => `<path d="M45 30 Q44 13 60 13 Q76 13 75 30 Q76 44 60 45 Q44 44 45 30 Z" fill="#232323"/><rect x="51" y="24" width="18" height="8" rx="3" fill="${SKIN}"/>`,
    beret: c => `<path d="M45 19 Q44 9 60 9 Q78 9 76 16 Q66 14 60 19 Z" fill="#7b1f2a" ${st}/>`,
    police_cap: c => `<path d="M44 16 Q60 8 76 16 L73 21 L47 21 Z" fill="#1d2433" ${st}/><path d="M47 21 Q60 24 73 21 L73 23 Q60 26 47 23 Z" fill="#111"/><circle cx="60" cy="17" r="2" fill="#d6b44a"/>`,
    kabalak: c => `<path d="M45 24 Q44 8 60 8 Q76 8 75 24 Q60 21 45 24 Z" fill="#8a7a52" ${st}/><path d="M46 13 Q60 9 74 14 M45 18 Q60 13 75 19" fill="none" stroke="#6e6140" stroke-width="1.4"/>`,
  };
  const BEARDS = {
    none: "", stubble: `<path d="M50 35 Q60 44 70 35 Q60 41 50 35 Z" fill="#6a5a4a" opacity=".45"/>`,
    moustache: `<path d="M53 33 Q60 30 67 33 Q60 32 53 33 Z" fill="#4a3b2c" stroke="#4a3b2c" stroke-width="1.2" stroke-linejoin="round"/>`,
    beard: `<path d="M47 30 Q48 46 60 46 Q72 46 73 30 Q70 38 60 38 Q50 38 47 30 Z" fill="#5a4632"/><path d="M53 33 Q60 31 67 33" fill="none" stroke="#5a4632" stroke-width="1.6"/>`,
  };

  // --- weapons, by `icon` (held in the weapon hand at 28,130) ------------------------
  // Shield shapes (look.shield): a heater with painted bands, or a round shield with a boss.
  const SHIELDS = {
    heater: c => `<path d="M88 92 L112 92 L112 116 Q112 136 100 144 Q88 136 88 116 Z" fill="${shade(c, 0.15)}" stroke="${INK}" stroke-width="1.2"/><path d="M100 96 V138 M90 110 H110" stroke="${shade(c, 0.55)}" stroke-width="2"/>`,
    round: c => `<circle cx="100" cy="114" r="15" fill="${shade(c, 0.15)}" stroke="${INK}" stroke-width="1.2"/><circle cx="100" cy="114" r="10" fill="none" stroke="${shade(c, 0.5)}" stroke-width="1.2"/><circle cx="100" cy="114" r="3.2" fill="#9aa3ad" stroke="${INK}" stroke-width=".8"/>`,
  };
  const W = {
    sword: `<path d="M28 132 L18 70" stroke="#c9d1d8" stroke-width="3" stroke-linecap="round"/><path d="M22 128 L34 126" stroke="#6b5530" stroke-width="3"/>`,
    sabre: `<path d="M28 132 Q12 104 22 70" fill="none" stroke="#c9d1d8" stroke-width="3" stroke-linecap="round"/><path d="M22 128 L34 126" stroke="#a7822f" stroke-width="3"/>`,
    dagger: `<path d="M28 133 L24 112" stroke="#c9d1d8" stroke-width="3" stroke-linecap="round"/><path d="M24 130 L33 129" stroke="#6b5530" stroke-width="2.5"/>`,
    axe: `<path d="M28 140 L20 72" stroke="#6b4b28" stroke-width="3"/><path d="M21 80 Q8 76 8 90 Q14 86 22 88 Z" fill="#9aa3ad" stroke="#4a525a" stroke-width=".8"/>`,
    club: `<path d="M28 140 L20 84" stroke="#6b4b28" stroke-width="3.5"/><circle cx="19" cy="80" r="7" fill="#9aa3ad" stroke="#4a525a"/><path d="M19 70 V73 M10 80 H13 M25 80 H28 M13 74 L15 76 M23 84 L25 86" stroke="#4a525a" stroke-width="1.6"/>`,
    spear: `<path d="M28 222 L28 8" stroke="#6b4b28" stroke-width="2.6"/><path d="M28 0 L31 12 L28 16 L25 12 Z" fill="#c9d1d8" stroke="#4a525a" stroke-width=".6"/>`,
    bill: `<path d="M28 222 L28 14" stroke="#6b4b28" stroke-width="2.6"/><path d="M28 0 L31 13 L32 34 Q22 33 23 22 Q27 24 27 16 Z" fill="#c9d1d8" stroke="#4a525a" stroke-width=".7"/><path d="M31 25 L38 21" stroke="#4a525a" stroke-width="1.6" stroke-linecap="round"/>`,
    poleaxe: `<path d="M28 222 L28 10" stroke="#6b4b28" stroke-width="2.6"/><path d="M28 0 L30.5 12 L25.5 12 Z" fill="#c9d1d8" stroke="#4a525a" stroke-width=".6"/><path d="M29.5 14 Q42 12 43 30 Q36 25 29.5 27 Z" fill="#9aa3ad" stroke="#4a525a" stroke-width=".7"/><rect x="19.5" y="16" width="8" height="7" rx="1" fill="#9aa3ad" stroke="#4a525a" stroke-width=".7"/>`,
    lance: `<path d="M28 222 L28 4" stroke="#6b4b28" stroke-width="2.6"/><path d="M28 -4 L31 8 L28 12 L25 8 Z" fill="#c9d1d8" stroke="#4a525a" stroke-width=".6"/><path d="M28 14 L42 18 L28 24 Z" fill="#c73a3a"/><path d="M28 18 L42 18 L28 22 Z" fill="#f2efe6"/>`,
    bow: `<path d="M98 72 Q120 130 98 188" fill="none" stroke="#6b4b28" stroke-width="3"/><path d="M98 72 L98 188" stroke="#ddd" stroke-width=".7"/>`,
    crossbow: `<path d="M28 134 L58 104" stroke="#6b4b28" stroke-width="4"/><path d="M44 104 Q56 96 64 112" fill="none" stroke="#4a525a" stroke-width="2.4"/>`,
    sling: `<path d="M28 130 Q14 100 22 76 Q28 72 30 78" fill="none" stroke="#7d5530" stroke-width="1.4"/><circle cx="24" cy="78" r="3" fill="#8b8b8b"/>`,
    long_gun: `<path d="M24 150 L66 96" stroke="#5a3d22" stroke-width="5" stroke-linecap="round"/><path d="M52 114 L80 78" stroke="#4a4f55" stroke-width="2.6" stroke-linecap="round"/>`,
    bayonet_gun: `<path d="M24 150 L66 96" stroke="#5a3d22" stroke-width="5" stroke-linecap="round"/><path d="M52 114 L80 78" stroke="#4a4f55" stroke-width="2.6"/><path d="M80 78 L92 62" stroke="#c9d1d8" stroke-width="2" stroke-linecap="round"/>`,
    musket_butt: `<path d="M28 146 L20 70" stroke="#4a4f55" stroke-width="2.6"/><path d="M28 140 L34 112" stroke="#5a3d22" stroke-width="5" stroke-linecap="round"/>`,
    modern_rifle: `<path d="M26 140 L72 100" stroke="#2b2e31" stroke-width="5" stroke-linecap="round"/><path d="M40 128 L44 140 M54 116 L58 128" stroke="#2b2e31" stroke-width="3"/><path d="M68 104 L84 90" stroke="#2b2e31" stroke-width="2.2"/>`,
    machine_gun: `<path d="M26 140 L76 98" stroke="#2b2e31" stroke-width="6" stroke-linecap="round"/><path d="M76 98 L90 86" stroke="#2b2e31" stroke-width="2.6"/><path d="M50 122 Q52 132 46 138" fill="none" stroke="#b08d3c" stroke-width="2"/>`,
    smg: `<path d="M26 134 L56 110" stroke="#2b2e31" stroke-width="5" stroke-linecap="round"/><path d="M42 122 L40 136" stroke="#2b2e31" stroke-width="3"/><path d="M56 110 L64 104" stroke="#2b2e31" stroke-width="2"/>`,
    pistol: `<path d="M28 132 L30 118 L44 116 L44 121 L33 122 Z" fill="#2b2e31"/>`,
    launcher: `<path d="M20 144 L84 92" stroke="#57603a" stroke-width="6" stroke-linecap="round"/><path d="M84 92 L94 82" stroke="#57603a" stroke-width="10" stroke-linecap="round"/>`,
    grenade: `<ellipse cx="22" cy="122" rx="5" ry="6.5" fill="#55603a" stroke="#2f3420"/><path d="M22 115 V112 H26" stroke="#8b8b8b" stroke-width="1.6" fill="none"/>`,
    stick_grenade: `<path d="M28 136 L20 110" stroke="#7d5530" stroke-width="3"/><rect x="15" y="100" width="10" height="11" rx="2" fill="#55603a" stroke="#2f3420" transform="rotate(-18 20 105)"/>`,
    device: `<rect x="18" y="120" width="12" height="16" rx="2" fill="#3a3a3a"/><path d="M24 120 V112" stroke="#3a3a3a" stroke-width="1.4"/><circle cx="24" cy="111" r="1.6" fill="#c73a3a"/>`,
    rammer: `<path d="M28 222 L28 40" stroke="#6b4b28" stroke-width="2.6"/><rect x="24" y="32" width="8" height="10" rx="2" fill="#2f2a26"/>`,
    stake: `<path d="M28 140 L24 106" stroke="#a2905c" stroke-width="3"/><path d="M24 106 L23 100" stroke="#a2905c" stroke-width="1.6"/>`,
    spade: `<path d="M28 140 L20 92" stroke="#6b4b28" stroke-width="3"/><path d="M20 92 L14 74 L22 70 L28 88 Z" fill="#5d6449" stroke="#3d4230" stroke-width=".8"/>`,
    fist: ``,
  };
  const iconOf = w => !w ? "fist" : w.icon || (w.threat ? (w.threat === "pistol" ? "pistol" : "long_gun") : w.melee === "unarmed" ? "fist" : "sword");

  // --- composition ------------------------------------------------------------------------
  const layersOf = v => {                       // same banding as slot_layers in the engine
    if (!v) return [];
    if (typeof v === "string") return [[v, 0, 100]];
    const items = Array.isArray(v) ? v : [v]; let lo = 0;
    return items.map(it => { const n = it.cover == null ? 100 - lo : it.cover; const r = [it.material, lo, lo + n]; lo += n; return r });
  };
  function slotSvg(slot, val, uid) {
    const shapes = PARTS[slot]; if (!shapes) return "";
    const [x, y, w, h] = SLOT_BOX[slot];
    return layersOf(val).map(([mat, lo, hi], i) => {
      const fill = MAT[mat]; if (!fill) return "";
      const id = `${uid}-${slot}-${i}`;
      return `<clipPath id="${id}"><rect x="${x - 4}" y="${y + h * lo / 100}" width="${w + 8}" height="${h * (hi - lo) / 100}"/></clipPath>` +
        shapes.map(d => `<path d="${d}" fill="${fill}" stroke="#3a4148" stroke-width=".7" clip-path="url(#${id})"/>`).join("");
    }).join("");
  }
  const face = beard => beard === "mask" ? `<path d="M52 24.5 Q55 23 57.5 24.5 M62.5 24.5 Q65 23 68 24.5" fill="none" stroke="#3b2d22" stroke-width="1.1" stroke-linecap="round"/><ellipse cx="55" cy="27.5" rx="1.3" ry="1.6" fill="#1f1a17"/><ellipse cx="65" cy="27.5" rx="1.3" ry="1.6" fill="#1f1a17"/>` : `<g><path d="M52 24.5 Q55 23 57.5 24.5 M62.5 24.5 Q65 23 68 24.5" fill="none" stroke="#3b2d22" stroke-width="1.1" stroke-linecap="round"/>
    <ellipse cx="55" cy="27.5" rx="1.3" ry="1.6" fill="#1f1a17"/><ellipse cx="65" cy="27.5" rx="1.3" ry="1.6" fill="#1f1a17"/>
    <path d="M60 28 L58.6 32.5 L61 32.8" fill="none" stroke="${SKIN_DARK}" stroke-width=".9" stroke-linecap="round"/>
    <path d="M56 36 Q60 38 64 36" fill="none" stroke="#7a3f33" stroke-width="1.1" stroke-linecap="round"/>${BEARDS[beard] || ""}</g>`;
  const HAIR = `<path d="M46.5 24 Q46 13 60 13 Q74 13 73.5 24 Q70 17 60 17 Q50 17 46.5 24 Z" fill="#4a3b2c"/>`;

  // Where to mark a wound on the figure (front view; back wounds get a dashed ring).
  const WOUND_AT = {
    skull_l: [66, 19], skull_r: [54, 19], face: [60, 31], neck: [60, 46], chest_l: [70, 68], chest_r: [50, 68],
    abdomen: [60, 104], groin: [60, 126], back_upper: [60, 72], back_lower: [60, 100],
    shoulder_l: [88, 56], shoulder_r: [32, 56], upper_arm_l: [90, 78], upper_arm_r: [30, 78],
    forearm_l: [91, 110], forearm_r: [29, 110], hand_l: [92, 130], hand_r: [28, 130],
    thigh_l: [69, 156], thigh_r: [51, 156], knee_l: [69, 182], knee_r: [51, 182],
    lower_leg_l: [69, 196], lower_leg_r: [51, 196], foot_l: [71, 212], foot_r: [49, 212],
  };
  const SEV_R = { light: 3.2, serious: 4.4, critical: 5.8 };
  const woundMarks = wounds => (wounds || []).map(w => {
    const at = WOUND_AT[w.loc]; if (!at) return "";
    const back = w.loc.startsWith("back_"), r = SEV_R[w.sev] || 4;
    return `<circle cx="${at[0]}" cy="${at[1]}" r="${r}" fill="${back ? "none" : "#c4122f"}" stroke="${back ? "#c4122f" : "#fff"}" stroke-width="${back ? 2 : 1}"${back ? ' stroke-dasharray="2 1.5"' : ""}><title>${w.loc.replace("_", " ")}: ${w.sev || ""}</title></circle>`;
  }).join("");

  let seq = 0;
  function svg({ kit = null, weapon = null, look = {}, size = 96, title = "", wounds = null } = {}) {
    const uid = "fg" + (seq++).toString(36);
    const slots = (kit && kit.slots) || {};
    const colour = look.colour || "#6b7480";
    const coat = look.coat === "skin" ? SKIN : colour;
    const trousers = look.trousers || shade(colour, -0.35);
    const helmMat = slots.helm ? layersOf(slots.helm)[0][0] : null;
    const visor = slots.visor && layersOf(slots.visor)[0][2] >= 70;
    const helmShape = helmMat ? (visor ? "closed" : look.helmet || (kit.look && kit.look.helmet) || HELM_BY_MAT[helmMat]) : null;
    const hat = !helmShape ? (look.hat || "none") : null;
    const icon = iconOf(weapon);
    const shield = kit && kit.shield;
    // Headgear that frames the face (coif, hood, head cloth, balaclava) is drawn under the face.
    const faceOver = helmShape === "coif" || ["hood", "shemagh", "balaclava"].includes(hat);
    const pole = icon === "spear" || icon === "lance" || icon === "rammer";
    const shieldDef = `<pattern id="fg-shemagh" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="#ece6d6"/><path d="M0 3 H6 M3 0 V6" stroke="#b5463a" stroke-width=".9"/></pattern>`;
    return `<svg viewBox="0 -10 120 240" width="${Math.round(size * 120 / 240)}" height="${size}" role="img" aria-label="${title}">${title ? `<title>${title}</title>` : ""}${DEFS.replace("</defs>", shieldDef + "</defs>")}
      ${pole ? W[icon] : ""}
      <g stroke="${INK}" stroke-width=".8">
        ${PARTS.leg.concat(PARTS.greave).map(d => `<path d="${d}" fill="${trousers}"/>`).join("")}
        ${FEET.map(d => `<path d="${d}" fill="#2f2a26"/>`).join("")}
        <path d="${COAT}" fill="${coat}"/>
        ${PARTS.arm.map(d => `<path d="${d}" fill="${coat}"/>`).join("")}
        <path d="${PARTS.gorget[0]}" fill="${SKIN}"/>
        <circle cx="60" cy="28" r="14" fill="${SKIN}"/>
        ${HANDS.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="5.5" fill="${SKIN}"/>`).join("")}
      </g>
      ${look.coat === "skin" ? "" : `<path d="M40 118 L80 118" stroke="#2f2a26" stroke-width="3"/>`}
      ${["leg", "greave", "skirt", "torso_lower", "torso_upper", "arm", "pauldron", "gorget"].map(s => slotSvg(s, slots[s], uid)).join("")}
      ${slots.gauntlet ? HANDS.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="5.8" fill="${MAT[layersOf(slots.gauntlet)[0][0]] || SKIN}" stroke="#3a4148" stroke-width=".7"/>`).join("") : ""}
      ${slots.sabaton ? FEET.map(d => `<path d="${d}" fill="${MAT[layersOf(slots.sabaton)[0][0]] || "#2f2a26"}" stroke="#3a4148" stroke-width=".7"/>`).join("") : ""}
      ${!helmShape && !["hood", "shemagh", "balaclava"].includes(hat) ? HAIR : ""}
      ${helmShape === "closed" || faceOver ? "" : face(look.beard)}
      ${helmShape ? HELMETS[helmShape] || "" : (HATS[hat] || HATS.none)(colour)}
      ${faceOver ? face(hat === "balaclava" ? "mask" : look.beard) : ""}
      ${shield ? (SHIELDS[look.shield] || SHIELDS.heater)(colour) : ""}
      ${pole ? "" : W[icon] || ""}
      ${woundMarks(wounds)}
    </svg>`;
  }
  function shade(hex, amt) {
    const n = parseInt(hex.slice(1), 16), f = c => Math.max(0, Math.min(255, Math.round(amt < 0 ? c * (1 + amt) : c + (255 - c) * amt)));
    return "#" + [n >> 16, (n >> 8) & 255, n & 255].map(f).map(c => c.toString(16).padStart(2, "0")).join("");
  }
  // The look of an example combatant: its side's look, then the example's own.
  const lookFor = (conflict, ex) => Object.assign({}, ((conflict.sides || []).find(s => s.name === ex.side) || {}).look || {}, ex.look || {});
  // Locator map of a conflict (data/maps.json, built by tools/maps/make_maps.mjs). Colours
  // come from CSS variables --map-sea, --map-land, --map-coast, --map-hl, --map-dot.
  // A map has one or more panels, drawn side by side. Solid dots: where the records come
  // from; hollow dots: fought there, but no wound records used.
  function map(m, height = 48, title = "") {
    if (!m) return "";
    const n = m.panels.length, W = n * m.w + (n - 1) * m.gap, width = Math.round(height * W / m.h);
    const dotName = d => d.names.join(", ") + (d.context ? " (no records used)" : "");
    const names = m.panels.map(p => (p.label ? p.label + ": " : "") + p.dots.map(dotName).join("; ")).join(" | ");
    const uid = "mp" + (seq++).toString(36);
    const panel = (p, i) => `<g transform="translate(${i * (m.w + m.gap)} 0)"><title>${p.label || title}</title>
      <clipPath id="${uid}-${i}"><rect width="${m.w}" height="${m.h}" rx="7"/></clipPath><g clip-path="url(#${uid}-${i})">
      <rect width="${m.w}" height="${m.h}" fill="var(--map-sea,#d5e1e6)"/>
      <path d="${p.land}" fill="var(--map-land,#cfc6ab)" stroke="var(--map-coast,#8c8670)" stroke-width=".5" stroke-linejoin="round"/>
      ${p.lakes ? `<path d="${p.lakes}" fill="var(--map-sea,#d5e1e6)" stroke="var(--map-coast,#8c8670)" stroke-width=".35"/>` : ""}
      ${p.highlight ? `<path d="${p.highlight}" fill="var(--map-hl,#b8a77a)" stroke="var(--map-coast,#8c8670)" stroke-width=".5"/>` : ""}
      ${p.borders ? `<path d="${p.borders}" fill="none" stroke="var(--map-coast,#8c8670)" stroke-width=".45" stroke-dasharray="1.6 1.2" opacity=".8"/>` : ""}</g>
      ${p.dots.map(d => `<circle cx="${d.x}" cy="${d.y}" r="${d.names.length > 1 ? 4.2 : 3.4}" fill="${d.context ? "var(--map-sea,#d5e1e6)" : "var(--map-dot,#8e1b2c)"}" stroke="${d.context ? "var(--map-dot,#8e1b2c)" : "var(--map-sea,#d5e1e6)"}" stroke-width="${d.context ? 1.6 : 1.2}"><title>${dotName(d)}</title></circle>`).join("")}
      <rect x=".5" y=".5" width="${m.w - 1}" height="${m.h - 1}" rx="7" fill="none" stroke="var(--map-coast,#8c8670)" stroke-width="1"/></g>`;
    return `<svg viewBox="0 0 ${W} ${m.h}" width="${width}" height="${height}" role="img" aria-label="${title}: ${names}"><title>${title}: ${names}</title>${m.panels.map(panel).join("")}</svg>`;
  }
  return { svg, map, lookFor, iconOf, names: { helmet: Object.keys(HELMETS), hat: Object.keys(HATS), icon: Object.keys(W), beard: Object.keys(BEARDS), shield: Object.keys(SHIELDS) } };
})();
if (typeof module !== "undefined") module.exports = FIG;
