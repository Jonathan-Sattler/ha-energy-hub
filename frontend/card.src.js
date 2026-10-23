/*
 * Energy Hub house card
 * An illustrated, live view of a house with its energy flows, drawn from a scene module.
 * Served by the energy_hub integration at /energy_hub/energy-hub-house-card.js, no resource entry needed.
 *
 *   type: custom:energy-hub-house-card
 *   entity: sensor.energy_hub_flow_state      # optional, found automatically
 *   scene: /local/energy-hub/house.js         # optional, built-in demo house otherwise
 *   weather: weather.home                      # optional, first weather entity otherwise
 *   actions:                                   # optional, standard Home Assistant actions
 *     electricity: { action: navigate, navigation_path: live }
 *     heating: { action: navigate, navigation_path: heating }
 *
 * Zones: solar, solar_thermal, battery, ems, household, grid, heating, wallbox.
 * Groups: electricity (solar, battery, ems, household, grid, wallbox), heating (heating, solar_thermal).
 * A navigation_path without a leading "/" is a view of the current dashboard.
 */
const VERSION = "0.2.0";
const TEX = __TEX__;
const NS = "http://www.w3.org/2000/svg";

const ZONES = ["solar", "solar_thermal", "battery", "ems", "household", "grid", "heating", "wallbox"];
const GROUP = { solar: "electricity", battery: "electricity", ems: "electricity", household: "electricity", grid: "electricity", wallbox: "electricity", heating: "heating", solar_thermal: "heating" };
const ZONE_ENTITY = { solar: ["pv_power"], battery: ["battery_soc", "battery_power"], grid: ["grid_power", "grid_import_power"], household: ["load_power"],
  heating: ["burner_modulation", "burner_active", "dhw_storage_temp"], solar_thermal: ["solar_collector_temp", "solar_storage_temp"], ems: [], wallbox: [] };

const STR = {
  en: { household: "Household", solar: "Solar", solar_thermal: "Solar thermal", grid: "Grid", battery: "Battery", heating: "Heating", wallbox: "Wallbox", ems: "Energy manager",
    import: "import", feedin: "feed-in", idle: "idle", charging: "charging", discharging: "discharging", off: "off", tank: "tank", notInstalled: "not installed",
    pumpOn: "pump on", hotWater: "hot water", space: "heating", selfSufficient: "self-sufficient",
    m_store: ["Battery stores solar surplus.", "The energy manager charges the battery with solar power the household does not use right now."],
    m_self: ["Battery supplies the household.", "Stored energy covers the household, so less power is bought from the grid."],
    m_grid: ["Battery charges from the grid.", "Electricity is cheap in this slot, so the energy manager tops up the battery."],
    m_full: ["Battery is full.", "Solar surplus goes to the grid as feed-in."],
    m_cheap: ["Electricity is cheap right now.", "Good moment for flexible consumers like the dishwasher or the washing machine."],
    m_wait: ["Battery is not charging.", "The battery waits for a cheaper or sunnier slot to reduce costs."],
    m_none: ["No battery data.", "Map a battery in the Energy Hub options to see what the energy manager does."] },
  de: { household: "Haushalt", solar: "Solar", solar_thermal: "Solarthermie", grid: "Netz", battery: "Batterie", heating: "Heizung", wallbox: "Wallbox", ems: "Energiemanager",
    import: "Netzbezug", feedin: "Einspeisung", idle: "inaktiv", charging: "lädt", discharging: "entlädt", off: "aus", tank: "Speicher", notInstalled: "nicht installiert",
    pumpOn: "Pumpe an", hotWater: "Warmwasser", space: "Heizen", selfSufficient: "Autarkie",
    m_store: ["Batterie speichert Solarüberschuss.", "Der Energiemanager lädt die Batterie mit Solarstrom, den der Haushalt gerade nicht braucht."],
    m_self: ["Batterie versorgt den Haushalt.", "Gespeicherte Energie deckt den Verbrauch, es wird weniger Strom aus dem Netz bezogen."],
    m_grid: ["Batterie lädt aus dem Netz.", "Strom ist in diesem Zeitfenster günstig, deshalb lädt der Energiemanager nach."],
    m_full: ["Batterie ist voll.", "Der Solarüberschuss wird ins Netz eingespeist."],
    m_cheap: ["Strom ist gerade günstig.", "Ein guter Moment für flexible Verbraucher wie Spül- oder Waschmaschine."],
    m_wait: ["Batteriespeicher lädt nicht.", "Batteriespeicher lädt nicht, um die Kosten zu reduzieren."],
    m_none: ["Keine Batteriedaten.", "Ordne in den Energy-Hub-Optionen eine Batterie zu, um den Energiemanager zu sehen."] },
};

const CSS = `
  :host { display: block; --sol: #2fd3ad; --grid: #8f63f2; --elec: #2bb673; --gas: #f08a24; --heat: #e04848; --cold: #2a9fd6;
    --surface: var(--card-background-color, var(--ha-card-background, #fff)); --fg: var(--primary-text-color, #1d2430);
    --fg-2: var(--secondary-text-color, #5e6878); --line: var(--divider-color, #d8d4cb); --cable: #8e979f;
    --font: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, "Roboto", system-ui, sans-serif)); }
  ha-card { overflow: hidden; }
  svg { width: 100%; height: auto; display: block; }
  .msg { display: flex; gap: 12px; align-items: flex-start; margin: 12px; padding: 12px 14px; border-radius: 12px; border: 2px solid transparent;
    background: linear-gradient(var(--surface), var(--surface)) padding-box, linear-gradient(90deg, var(--grid), var(--sol)) border-box; }
  .msg svg { width: 24px; height: 24px; flex: none; color: var(--fg); }
  .msg .t { font-weight: 600; color: var(--fg); } .msg .d { color: var(--fg-2); font-size: 13px; }
  .cable { fill: none; stroke: var(--cable); stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; opacity: .75; }
  .cable.idle { opacity: .25; }
  .pulse { fill: none; stroke-linecap: round; pointer-events: none; }
  .lbl .v { font: 600 13px var(--font); fill: var(--fg); font-variant-numeric: tabular-nums; }
  .lbl .v tspan.dim { fill: var(--fg-2); font-weight: 400; }
  .lbl .k { font: 400 12px var(--font); fill: var(--fg-2); }
  .lbl .plate { fill: var(--surface); opacity: .88; }
  .lbl line { stroke: var(--fg-2); stroke-width: 1; opacity: .55; }
  .lbl.dim { opacity: .5; }
  .pill rect { fill: var(--surface); stroke: var(--line); }
  .pill text { font: 500 12px var(--font); fill: var(--fg); font-variant-numeric: tabular-nums; }
  .band { fill: var(--surface); }
  .ghost { opacity: .5; }
  .zone { cursor: pointer; outline: none; }
  .zone:not([data-zone="household"]):hover, .zone:not([data-zone="household"]):focus-visible { filter: drop-shadow(0 0 5px rgba(47, 211, 173, .9)); }
  .zone[data-zone="household"]:focus-visible { filter: brightness(1.05); }
  .lbl.zone:hover .k, .lbl.zone:focus-visible .k { fill: var(--fg); text-decoration: underline; }
  .drift { animation: drift 90s ease-in-out infinite alternate; } .drift.far { animation-duration: 160s; } .drift.near { animation-duration: 70s; }
  @keyframes drift { from { transform: translateX(-40px); } to { transform: translateX(40px); } }
  .rain1 { animation: rain .55s linear infinite; } .rain2 { animation: rain .75s linear infinite; } .rain3 { animation: rain .95s linear infinite; }
  @keyframes rain { from { transform: translateY(0); } to { transform: translateY(24px); } }
  @media (prefers-reduced-motion: reduce) { .pulse { display: none; } .drift, .rain1, .rain2, .rain3 { animation: none; } }
`;

const COL = { frame: "#2b221c", glass: "#8fb5cf", glassNight: "#ffd27a", shutter: "#e4e0d6", fascia: "#3e2e24", concrete: "#c9c5bb", concreteDark: "#a8a398",
  wood: "#4b3020", woodLight: "#6a4630", pv: "#0f1114", pvCell: "#1a1f2b", collector: "#15181c", tube: "#2a3038", ghost: "#f1f3f6",
  lawnDark: "#6f8a5c", asphalt: "#787672", paving: "#b3ada0", pavingLine: "#9d978a", unit: "#f3f4f2", unitSide: "#c9ccc9", unitTop: "#fbfbfa" };

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const hex = (c) => { if (c.length === 4) c = "#" + [...c.slice(1)].map((ch) => ch + ch).join(""); return [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)); };
const mix = (a, b, t) => { const A = hex(a), B = hex(b); return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * clamp(t, 0, 1)).toString(16).padStart(2, "0")).join(""); };

/* ------------------------------------------------------------------------------------------------
 * Engine: projection, materials, sky, scene drawing API, energy network and comet animation.
 * ---------------------------------------------------------------------------------------------- */
function createEngine(svg, sceneFn, T) {
  const el = (tag, attrs = {}, parent = svg) => { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); parent.appendChild(n); return n; };
  const txt = (x, y, s, attrs = {}, parent = svg) => { const t = el("text", { x, y, ...attrs }, parent); t.textContent = s; return t; };
  const rect = (x, y, w, h, fill, parent, extra = {}) => el("rect", { x, y, width: w, height: h, fill, ...extra }, parent);
  const poly = (points, fill, parent, extra = {}) => el("polygon", { points: points.map((p) => p.map((v) => (+v).toFixed(2)).join(",")).join(" "), fill, ...extra }, parent);

  // oblique projection of model centimetres: x east, y away from the street, z up
  const S = 0.36, KX = 0.28 * S, KZ = 0.16 * S, OX = 402, OY = 440;
  const P = (x, y, z) => [OX + S * x + KX * y, OY - S * z - KZ * y];
  const face = (parent, o, u, v, extra = {}) => {
    const [e, f] = P(...o);
    const a = S * u[0] + KX * u[1], b = -S * u[2] - KZ * u[1], c = S * v[0] + KX * v[1], d = -S * v[2] - KZ * v[1];
    return el("g", { transform: `matrix(${a.toFixed(5)} ${b.toFixed(5)} ${c.toFixed(5)} ${d.toFixed(5)} ${e.toFixed(2)} ${f.toFixed(2)})`, ...extra }, parent);
  };
  const FRONT = (parent, x0, y, zTop, extra) => face(parent, [x0, y, zTop], [1, 0, 0], [0, 0, -1], extra);
  const EAST = (parent, x, y0, zTop, extra) => face(parent, [x, y0, zTop], [0, 1, 0], [0, 0, -1], extra);
  const TOP = (parent, x0, y0, z, extra) => face(parent, [x0, y0, z], [1, 0, 0], [0, 1, 0], extra);

  const gSky = el("g"), gFar = el("g"), gGround = el("g"), gHouse = el("g"), gEq = el("g"), gLight = el("g"), gCables = el("g"), gSignals = el("g"), gChips = el("g"), gFront = el("g");
  svg.insertBefore(el("defs"), gSky);
  const defs = svg.querySelector("defs");
  const grad = (id, stops, vertical = true) => { const g = el("linearGradient", { id, x1: 0, y1: 0, x2: vertical ? 0 : 1, y2: vertical ? 1 : 0 }, defs); return stops.map(([o, c, op]) => el("stop", { offset: o, "stop-color": c, ...(op !== undefined ? { "stop-opacity": op } : {}) }, g)); };
  const skyStops = grad("sky", [[0, "#2f74c9"], [0.6, "#8ec1ea"], [1, "#dbeaf6"]]);
  grad("eaveShadow", [[0, "#000", 0.32], [1, "#000", 0]]);
  grad("slopeShade", [[0, "#fff", 0.08], [1, "#000", 0.14]]);
  grad("glassRefl", [[0, "#ffffff", 0.22], [0.5, "#ffffff", 0.04], [1, "#000000", 0.1]], false);
  grad("lawn", [[0, "#a9bf93"], [1, COL.lawnDark]]);
  const cloudStops = grad("cloud", [[0, "#ffffff"], [1, "#cfd8e2"]]);
  const radial = (id, stops) => { const g = el("radialGradient", { id }, defs); stops.forEach(([o, c, op]) => el("stop", { offset: o, "stop-color": c, "stop-opacity": op }, g)); };
  radial("sunGlow", [[0, "#fff3c4", 1], [0.25, "#ffd86a", 0.45], [1, "#ffd86a", 0]]);
  radial("moonGlow", [[0, "#dfe6f2", 0.5], [1, "#dfe6f2", 0]]);
  const imgPattern = (id, tex, w, h, extra = {}) => { const p = el("pattern", { id, width: w, height: h, patternUnits: "userSpaceOnUse", ...extra }, defs); el("image", { href: tex.uri, width: w, height: h, preserveAspectRatio: "none" }, p); };
  imgPattern("plaster", TEX.plaster, 100, 100); imgPattern("brown", TEX.brown, 100, 100); imgPattern("clinker", TEX.clinker, 100, 97.2);
  imgPattern("roof", TEX.roof, 120, 100); imgPattern("wood", TEX.wood, 100, 100); imgPattern("door", TEX.door, 100, 200); imgPattern("doorG", TEX.door, 100, 215);
  imgPattern("pavers", TEX.pavers, 100, 103.9); imgPattern("terrace", TEX.terrace, 100, 100);
  const pvp = el("pattern", { id: "pv", width: 17.97, height: 9.65, patternUnits: "userSpaceOnUse" }, defs);
  const pvCell = rect(0, 0, 17.97, 9.65, COL.pvCell, pvp); rect(0, 0, 17.97, 0.5, "#070809", pvp); rect(0, 0, 0.5, 9.65, "#070809", pvp);
  const pavp = el("pattern", { id: "paving", width: 40, height: 20, patternUnits: "userSpaceOnUse" }, defs);
  rect(0, 0, 40, 20, COL.paving, pavp); el("path", { d: "M0,10 h40 M20,0 v10 M0,10 v10 M40,10 v10", fill: "none", stroke: COL.pavingLine, "stroke-width": 1.5 }, pavp);
  const filter = (id, build, box = ["-50%", "-50%", "200%", "200%"]) => { const f = el("filter", { id, x: box[0], y: box[1], width: box[2], height: box[3] }, defs); build(f); };
  filter("soft", (f) => el("feGaussianBlur", { stdDeviation: 10 }, f), ["-20%", "-20%", "140%", "140%"]);
  filter("glowW", (f) => el("feGaussianBlur", { stdDeviation: 3 }, f));
  filter("glow", (f) => { el("feGaussianBlur", { stdDeviation: 2.5, result: "b" }, f); const m = el("feMerge", {}, f); el("feMergeNode", { in: "b" }, m); el("feMergeNode", { in: "SourceGraphic" }, m); }, ["-150%", "-150%", "400%", "400%"]);
  for (const [id, freq, oct, seed, scale, blur] of [["cloudF", "0.012 0.02", 3, 7, 36, 3], ["cloudFar", "0.02 0.03", 2, 3, 22, 6]])
    filter(id, (f) => { el("feTurbulence", { type: "fractalNoise", baseFrequency: freq, numOctaves: oct, seed, result: "noise" }, f); el("feDisplacementMap", { in: "SourceGraphic", in2: "noise", scale, xChannelSelector: "R", yChannelSelector: "G", result: "disp" }, f); el("feGaussianBlur", { in: "disp", stdDeviation: blur }, f); }, ["-20%", "-40%", "140%", "180%"]);

  // ---- scene drawing API ----
  const ref = { windows: [], pvGlow: [], collectors: [], soc: null, flame: null, tank: null, emsGlow: null };
  const zone = (name, parent) => el("g", { class: "zone", "data-zone": name, tabindex: 0, role: "button" }, parent);
  const win = (g, x, y, w, h, panes = 1, shutter = true) => {
    if (shutter) { rect(x - 6, y - 22, w + 12, 20, COL.shutter, g); rect(x - 6, y - 4, w + 12, 2, "#cbc6ba", g); }
    rect(x - 8, y - 8, w + 16, h + 14, COL.frame, g);
    const gl = rect(x, y, w, h, COL.glass, g); ref.windows.push(gl);
    rect(x, y, w, h, "url(#glassRefl)", g);
    for (let i = 1; i < panes; i++) rect(x + (w / panes) * i - 4, y, 8, h, COL.frame, g);
    rect(x - 10, y + h + 6, w + 20, 5, COL.concreteDark, g);
    return gl;
  };
  const glass = (g, x, y, w, h) => { const gl = rect(x, y, w, h, COL.glass, g); ref.windows.push(gl); rect(x, y, w, h, "url(#glassRefl)", g); return gl; };
  const shade = (g, pts, op) => poly(pts, "#000", g, { opacity: op });
  const plaster = (g, pts) => poly(pts, "url(#plaster)", g);
  const eave = (g, x, w, h = 60) => rect(x, 0, w, h, "url(#eaveShadow)", g);
  const box3 = (parent, x0, x1, y0, y1, z0, z1, r = 6) => {
    rect(0, 0, x1 - x0, y1 - y0, COL.unitTop, TOP(parent, x0, y0, z1), { rx: r });
    rect(0, 0, y1 - y0, z1 - z0, COL.unitSide, EAST(parent, x1, y0, z1));
    const g = FRONT(parent, x0, y0, z1); rect(0, 0, x1 - x0, z1 - z0, COL.unit, g, { rx: r }); return g;
  };
  const battery = (x0, y0, w = 90, d = 40, h = 112) => {
    const g = box3(zone("battery", gEq), x0, x0 + w, y0, y0 + d, 0, h);
    rect(10, 6, w - 20, 3, "#d5d8d5", g, { rx: 1.5 });
    el("path", { d: `M${w / 2 + 2},40 l-12,20 h10 l-6,20 l16,-24 h-10 l6,-16z`, fill: "var(--elec)" }, g);
    rect(w - 10, 22, 4, h - 32, "#d5d8d5", g, { rx: 2 });
    ref.soc = { el: rect(w - 10, h - 10, 4, 0, "var(--elec)", g, { rx: 2 }), bottom: h - 10, max: h - 32 };
    rect(4, h - 4, w - 8, 4, "#000", g, { opacity: 0.12 });
  };
  const ems = (x, y, z) => {
    const g = FRONT(zone("ems", gEq), x, y, z);
    ref.emsGlow = rect(-6, -6, 76, 82, "none", g, { rx: 12, stroke: "var(--sol)", "stroke-width": 9, filter: "url(#glowW)", opacity: 0 });
    rect(0, 0, 64, 70, "#f6f6f4", g, { rx: 8, stroke: "#c4c7c4", "stroke-width": 1.5 });
    el("path", { d: "M20,40 l12,-11 l12,11 v13 h-24z", fill: "none", stroke: "#7d6bb8", "stroke-width": 2.4, "stroke-linejoin": "round" }, g);
    el("path", { d: "M32,49 c-6,-4 -7,-8 -4,-10 c2,-1 4,0 4,2 c0,-2 2,-3 4,-2 c3,2 2,6 -4,10z", fill: "#7d6bb8" }, g);
  };
  const heatZone = () => (ref.heatZone ||= zone("heating", gEq));
  const boiler = (x0, y0) => {
    const g = box3(heatZone(), x0, x0 + 65, y0, y0 + 50, 0, 118);
    rect(14, 20, 37, 30, "#2a2f36", g, { rx: 4 });
    ref.flame = el("path", { d: "M32,46 q-10,-12 0,-22 q10,10 0,22z", fill: "var(--gas)", opacity: 0, filter: "url(#glow)" }, g);
    rect(20, 70, 25, 3, "#d5d8d5", g); rect(20, 78, 25, 3, "#d5d8d5", g);
  };
  const tank = (x0, y0) => {
    const g = box3(heatZone(), x0, x0 + 70, y0, y0 + 65, 0, 175, 30);
    rect(29, 30, 12, 120, "#e3e5e3", g, { rx: 6 });
    ref.tank = { el: rect(29, 150, 12, 0, "var(--heat)", g, { rx: 6, opacity: 0.8 }), bottom: 150, max: 120 };
    rect(4, 171, 62, 4, "#000", g, { opacity: 0.12 });
  };
  const wallbox = (faceGroup, x, y) => {
    const g = el("g", { class: "ghost" }, zone("wallbox", faceGroup));
    rect(x, y, 28, 36, COL.ghost, g, { rx: 3, stroke: "#5b6470", "stroke-width": 2, "stroke-dasharray": "5 3" }); rect(x + 6, y + 7, 16, 8, "#5b6470", g);
    el("circle", { cx: x + 14, cy: y + 27, r: 4, fill: "none", stroke: "#5b6470", "stroke-width": 2 }, g);
    el("path", { d: `M${x + 28},${y + 31} q14,0 14,14 q0,14 -14,14`, fill: "none", stroke: "#5b6470", "stroke-width": 2.5 }, g);
  };
  // PV array on a slope face group: modules in model cm, (x, t) = left edge and distance down the slope from the face origin
  const pvArray = (slopeG, x0, t0, cols, rows, mw = 113.4, mh = 176.2, gap = 2) => {
    const g = zone("solar", slopeG), W = cols * (mw + gap) - gap, H = rows * (mh + gap) - gap;
    rect(x0 - 4, t0 + 6, W + 8, H, "#000", g, { opacity: 0.25 });
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) { const x = x0 + c * (mw + gap), t = t0 + r * (mh + gap); rect(x, t, mw, mh, COL.pv, g); rect(x + 2.8, t + 1.2, mw - 5.6, mh - 2.4, "url(#pv)", g); }
    ref.pvGlow.push(rect(x0 - 3, t0 - 3, W + 6, H + 6, "none", g, { stroke: "var(--sol)", "stroke-width": 10, filter: "url(#glowW)", opacity: 0 }));
    ref.pvGlow.push(rect(x0 - 3, t0 - 3, W + 6, H + 6, "none", g, { stroke: "var(--sol)", "stroke-width": 3, opacity: 0, rx: 3 }));
    for (let c = 1; c < cols; c++) ref.pvGlow.push(el("line", { x1: x0 + c * (mw + gap) - 1, y1: t0, x2: x0 + c * (mw + gap) - 1, y2: t0 + H, stroke: "var(--sol)", "stroke-width": 1.6, opacity: 0 }, g));
    for (let r = 1; r < rows; r++) { const y = t0 + r * (mh + gap) - 1; ref.pvGlow.push(el("line", { x1: x0, y1: y, x2: x0 + W, y2: y, stroke: "var(--sol)", "stroke-width": 1.6, opacity: 0 }, g)); }
  };
  const collector = (slopeG, x, t, w = 206, h = 224, tubes = 20) => {
    const g = zone("solar_thermal", slopeG);
    rect(x - 3, t + 5, w + 6, h, "#000", g, { opacity: 0.25 });
    rect(x, t, w, h, COL.collector, g, { rx: 4 }); rect(x, t, w, 18, "#2a2f36", g, { rx: 4 }); rect(x, t + h - 5, w, 5, "#2a2f36", g);
    const pitch = (w - 10) / tubes;
    for (let i = 0; i < tubes; i++) rect(x + 5 + i * pitch + pitch * 0.2, t + 18, pitch * 0.6, h - 23, COL.tube, g, { rx: pitch * 0.3 });
    ref.collectors.push(rect(x - 3, t - 3, w + 6, h + 6, "none", g, { rx: 6, stroke: "#ff8a5c", "stroke-width": 6, filter: "url(#glowW)", opacity: 0 }));
    ref.collectors.push(rect(x - 3, t - 3, w + 6, h + 6, "none", g, { rx: 6, stroke: "#ffb08f", "stroke-width": 1.8, opacity: 0 }));
  };
  const api = { P, face, FRONT, EAST, TOP, el, rect, poly, txt, mix, clamp, COL, layers: { ground: gGround, house: zone("household", gHouse), eq: gEq },
    zone, win, glass, windowGlass: (node) => (ref.windows.push(node), node), shade, plaster, eave, box3, battery, ems, boiler, tank, wallbox, pvArray, collector };
  const scene = sceneFn(api) || {};
  const HORIZON = scene.horizon ?? 368, POLE = scene.pole ?? { x: 42, top: 175, base: 503 };

  // ---- sky ----
  rect(0, 0, 1200, HORIZON, "#000", el("clipPath", { id: "clipSky" }, defs));
  rect(0, 0, 1200, HORIZON + 4, "url(#sky)", gSky);
  const stars = el("g", { opacity: 0 }, gSky);
  for (let i = 0; i < 90; i++) el("circle", { cx: (i * 173 + 31) % 1200, cy: 10 + ((i * 97) % 300), r: i % 5 === 0 ? 1.3 : 0.7, fill: "#fff", opacity: 0.4 + (i % 4) * 0.15 }, stars);
  const sun = el("g", {}, gSky); el("circle", { r: 170, fill: "url(#sunGlow)" }, sun); el("circle", { r: 15, fill: "#fff6cf" }, sun);
  const moon = el("g", { opacity: 0 }, gSky); el("circle", { r: 70, fill: "url(#moonGlow)" }, moon);
  el("path", { d: "M0,-14 a14,14 0 1 0 10,24 a11,11 0 1 1 -10,-24z", fill: "#e8e9ef" }, moon);
  const wx = el("g", { "clip-path": "url(#clipSky)" }, gSky), clouds = [];
  const SHAPE = [[0, 0, 70, 26], [55, -10, 50, 30], [110, 4, 60, 22], [-60, 6, 48, 20], [30, 14, 90, 18], [160, 12, 40, 16]];
  for (const [x, y, sc, f, cls] of [[120, 100, 0.55, "cloudFar", "drift far"], [820, 70, 0.6, "cloudFar", "drift far"], [420, 110, 0.9, "cloudF", "drift"], [980, 140, 0.8, "cloudF", "drift"], [640, 36, 1.3, "cloudF", "drift near"], [160, 18, 1.2, "cloudF", "drift near"]]) {
    const outer = el("g", { transform: `translate(${x},${y}) scale(${sc})`, opacity: 0 }, wx), inner = el("g", { class: cls, filter: `url(#${f})` }, outer);
    for (const [dx, dy, rx, ry] of SHAPE) el("ellipse", { cx: dx, cy: dy, rx, ry, fill: "url(#cloud)" }, inner);
    clouds.push(outer);
  }
  const rain = el("g", { opacity: 0, "clip-path": "url(#clipSky)" }, gFront);
  for (const [cls, n, len, w, op, seed] of [["rain3", 80, 10, 0.8, 0.35, 97], ["rain2", 90, 14, 1, 0.45, 131], ["rain1", 60, 18, 1.3, 0.6, 173]]) {
    const g = el("g", { class: cls }, rain);
    for (let i = 0; i < n; i++) { const x = (i * seed) % 1200, y = ((i * 53) % 400) - 30; el("line", { x1: x, y1: y, x2: x - 2, y2: y + len, stroke: "#dbe6f0", "stroke-width": w, "stroke-linecap": "round", opacity: op }, g); }
  }
  const tree = el("g", { opacity: 0.55 }, gFar);
  for (let i = 0; i < 30; i++) { const x = 10 + i * 42 + (i % 3) * 7, h = 34 + ((i * 37) % 40); el("ellipse", { cx: x, cy: HORIZON - 4 - h / 2, rx: 26, ry: h / 2, fill: i % 2 ? "#6f8f66" : "#5f7f58" }, tree); }
  if (POLE) {
    const pz = zone("grid", gFar), X = POLE.x;
    el("rect", { x: X - 26, y: POLE.top, width: 52, height: POLE.base - POLE.top, fill: "transparent" }, pz);
    el("path", { d: `M${X - 22},${POLE.base} L${X - 6},${POLE.top} L${X + 6},${POLE.top} L${X + 22},${POLE.base}`, fill: "none", stroke: "#a9aeb3", "stroke-width": 3 }, pz);
    for (const [y, w] of [[POLE.top + 36, 34], [POLE.top + 82, 46], [POLE.top + 132, 40]]) {
      el("line", { x1: X - w, y1: y, x2: X + w, y2: y, stroke: "#a9aeb3", "stroke-width": 3 }, pz);
      for (const s of [-1, 1]) el("line", { x1: X + s * w, y1: y, x2: X + s * w, y2: y + 10, stroke: "#6d7781", "stroke-width": 2 }, pz);
      el("path", { d: `M${X - w},${y + 10} Q ${X - w - 40},${y + 30} -20,${y + 26}`, fill: "none", stroke: "#5c6670", "stroke-width": 1.2 }, gFar);
    }
    for (let y = POLE.top + 10; y < POLE.base - 20; y += 28) el("line", { x1: X - 9, y1: y, x2: X + 9, y2: y + 24, stroke: "#a9aeb3", "stroke-width": 1.2 }, pz);
  }
  const light = rect(0, 0, 1200, 600, "#0b1a3a", gLight, { opacity: 0, "pointer-events": "none" });

  // ---- energy network ----
  const pathOf = (pts) => "M " + pts.map((q) => P(...q).map((v) => v.toFixed(1)).join(",")).join(" L ");
  const edges = {};
  for (const [key, pts] of Object.entries(scene.edges || {})) {
    const d = typeof pts === "string" ? pts : pathOf(pts);
    const base = el("path", { d, class: "cable" }, gCables);
    edges[key] = { key, base, len: base.getTotalLength(),
      halo: el("path", { d, class: "pulse", "stroke-width": 7, filter: "url(#glowW)", opacity: 0 }, gSignals),
      core: el("path", { d, class: "pulse", "stroke-width": 2.6, opacity: 0 }, gSignals) };
  }

  // ---- labels: value over name with a hairline leader ----
  rect(0, 534, 1200, 66, "", gChips, { class: "band" });
  const LZONE = { load: "household", pv: "solar", coll: "solar_thermal", grid: "grid", bat: "battery", heat: "heating", ev: "wallbox" };
  const labels = {};
  for (const L of scene.labels || []) {
    const [ax, ay] = L.anchor, top = L.y < ay;
    const g = el("g", { class: "lbl zone" + (L.dim ? " dim" : ""), "data-zone": LZONE[L.key] || L.key, tabindex: 0, role: "button" }, gChips);
    const lead = el("path", { d: `M${ax.toFixed(1)},${ay.toFixed(1)} V${(L.y - 13).toFixed(1)}`, fill: "none", stroke: "var(--fg-2)", "stroke-width": 1, opacity: 0.55 }, g);
    el("circle", { cx: ax.toFixed(1), cy: ay.toFixed(1), r: 2, fill: "var(--fg-2)", opacity: 0.6 }, g);
    const left = L.side === "left", tx = left ? ax - 7 : ax + 7, anc = left ? "end" : "start";
    const plate = top ? rect(0, L.y - 17, 10, 36, "", g, { class: "plate", rx: 6 }) : rect(ax, L.y - 17, 10, 36, "transparent", g);
    const v = txt(tx, L.y - 2, "—", { class: "v", "text-anchor": anc }, g);
    const k = txt(tx, L.y + 13, L.name || T[LZONE[L.key] || L.key] || L.key, { class: "k", "text-anchor": anc }, g);
    labels[L.key] = { g, v, k, lead, plate, ax, ay, y: L.y, top, left,
      fit() { if (!top) return; const w = Math.max(v.getComputedTextLength(), k.getComputedTextLength()) + 12; plate.setAttribute("x", (left ? ax - 1 - w : ax + 1).toFixed(1)); plate.setAttribute("width", w.toFixed(1)); } };
  }
  const pill = (anchorRight) => {
    const g = el("g", { class: "pill" }, gChips), bg = rect(0, 0, 10, 30, "", g, { rx: 15 }), t = txt(14, 19.5, "", {}, g);
    return { set(s) { g.style.display = s ? "" : "none"; if (!s) return; t.textContent = s; const w = t.getComputedTextLength() + 28; bg.setAttribute("width", w.toFixed(1)); g.setAttribute("transform", `translate(${anchorRight ? (1184 - w).toFixed(1) : 16},14)`); } };
  };
  const pillL = pill(false), pillR = pill(true);

  // ---- comet engine: sources run into the hub, the hub flashes, then consumers are fed ----
  const net = { elec: [[], []], therm: [[], []], gridActive: false };
  const SPEED = 95, D = 34, GAP = 0.25, PAUSE = 0.7;
  const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
  const runners = [{ key: "elec", hub: true }, { key: "therm", hub: false }].map((r) => ({ ...r, stage: -1, t: 0, dur: 0, wait: 0.3 * Math.random(), shots: [] }));
  const show = (ed, col, rev, p) => {
    const off = rev ? -ed.len + p * (ed.len + D) : D - p * (ed.len + D), fade = p < 0.08 ? p / 0.08 : p > 0.92 ? (1 - p) / 0.08 : 1;
    for (const [pth, op] of [[ed.halo, 0.55], [ed.core, 1]]) {
      pth.setAttribute("stroke", col); pth.setAttribute("stroke-dasharray", `${D} ${(ed.len + D).toFixed(1)}`);
      pth.setAttribute("stroke-dashoffset", off.toFixed(1)); pth.setAttribute("opacity", (op * fade).toFixed(2));
    }
  };
  const hide = (ed) => { ed.halo.setAttribute("opacity", 0); ed.core.setAttribute("opacity", 0); };
  const dur = (k) => clamp(edges[k].len / SPEED, 0.9, 2.6);
  let flash = 0, flashCol = "var(--sol)";
  function step(dt) {
    for (const r of runners) {
      if (r.wait > 0) { r.wait -= dt; continue; }
      if (r.stage === -1 || r.t >= r.dur) {
        r.shots.forEach(([k]) => hide(edges[k]));
        if (r.stage === 0 && r.hub) { flash = 1; flashCol = net.gridActive ? "var(--grid)" : "var(--sol)"; }
        r.stage = r.stage === 0 ? 1 : 0;
        r.shots = (net[r.key][r.stage] || []).filter(([k]) => edges[k]);
        if (r.stage === 0 && !r.shots.length) { r.stage = 1; r.shots = (net[r.key][1] || []).filter(([k]) => edges[k]); }
        r.dur = Math.max(0.9, ...r.shots.map(([k]) => dur(k)));
        r.t = 0; r.wait = r.stage === 1 ? GAP : PAUSE;
        if (!r.shots.length) { r.stage = -1; r.wait = 1; }
        continue;
      }
      r.t += dt;
      for (const [k, col, rev] of r.shots) { const p = clamp(r.t / dur(k), 0, 1); p < 1 ? show(edges[k], col, rev, ease(p)) : hide(edges[k]); }
    }
    if (flash > 0) flash = Math.max(0, flash - dt * 1.4);
    if (ref.emsGlow) { ref.emsGlow.setAttribute("stroke", flashCol); ref.emsGlow.setAttribute("opacity", (0.15 + 0.85 * flash).toFixed(2)); }
  }

  // ---- render live values ----
  const PAL = { clearDay: ["#2b6fc4", "#8cc0ea", "#dcebf6"], clearDusk: ["#2a4a86", "#e49a6a", "#f6d3b0"], cloudy: ["#6f8094", "#a6b3bf", "#d3dae0"],
    rain: ["#3b4653", "#5f6c7a", "#8d99a5"], night: ["#050b1a", "#0d182f", "#172540"], nightCloud: ["#141a24", "#232c38", "#343f4c"] };
  const kw = (w) => (Math.abs(w) / 1000).toFixed(2) + " kW";
  function render(d, T) {
    // sky from the real sun position and weather
    const e = d.elevation, en = clamp(e / 60, 0, 1), twilight = clamp(1 - Math.abs(e) / 8, 0, 1);
    const day = clamp(e > 0 ? 0.35 + e / 30 : ((e + 8) / 8) * 0.35, 0, 1);
    const dayPal = d.sky === "clear" ? PAL.clearDay : d.sky === "cloudy" ? PAL.cloudy : PAL.rain, nightPal = d.sky === "clear" ? PAL.night : PAL.nightCloud;
    skyStops.forEach((s, i) => { let c = dayPal[i]; if (d.sky === "clear") c = mix(c, PAL.clearDusk[i], twilight * (i === 0 ? 0.4 : 0.85)); s.setAttribute("stop-color", mix(nightPal[i], c, Math.min(1, day * 1.25))); });
    stars.setAttribute("opacity", ((1 - day) * (d.sky === "clear" ? 0.9 : 0)).toFixed(2));
    tree.setAttribute("opacity", (0.15 + 0.45 * day).toFixed(2));
    const sx = clamp(1080 - ((d.azimuth - 90) / 180) * 960, 60, 1140);
    sun.setAttribute("transform", `translate(${sx.toFixed(1)},${(200 - en * 95).toFixed(1)})`);
    sun.style.opacity = e > -1 ? (d.sky === "clear" ? 1 : d.sky === "cloudy" ? 0.25 : 0) : 0;
    moon.setAttribute("transform", "translate(900,120)"); moon.setAttribute("opacity", e > 0 ? 0 : d.sky === "clear" ? 0.95 : 0.15);
    const cTop = d.sky === "rain" ? mix("#2c3540", "#9aa6b2", day) : mix(d.sky === "cloudy" ? "#3a4654" : "#4a5566", "#ffffff", day);
    const cBot = d.sky === "rain" ? mix("#1e252e", "#6e7a86", day) : mix(d.sky === "cloudy" ? "#2a333d" : "#3a4452", d.sky === "cloudy" ? "#c5cfd9" : "#d9e2ea", day);
    cloudStops[0].setAttribute("stop-color", cTop); cloudStops[1].setAttribute("stop-color", cBot);
    clouds.forEach((c, i) => c.setAttribute("opacity", d.sky === "clear" ? (i < 2 ? 0.5 : 0) : d.sky === "rain" ? 0.95 : 0.9));
    rain.setAttribute("opacity", d.sky === "rain" ? 1 : 0);
    const dull = d.sky === "cloudy" ? 0.18 : d.sky === "rain" ? 0.34 : 0;
    light.setAttribute("fill", mix("#0b1a3a", "#3f4a57", dull > 0 ? 0.6 : 0));
    light.setAttribute("opacity", clamp((1 - day) * 0.5 + dull * day, 0, 0.62).toFixed(2));
    const lit = e < -2;
    ref.windows.forEach((w) => w.setAttribute("fill", lit ? COL.glassNight : day < 0.35 ? "#2c3c55" : COL.glass));

    // equipment state
    const share = clamp(d.pv / (d.pvPeak || 10000), 0, 1);
    pvCell.setAttribute("fill", d.pv > 50 ? mix(COL.pvCell, "#24406e", share) : COL.pvCell);
    ref.pvGlow.forEach((r, i) => r.setAttribute("opacity", d.pv > 50 ? (r.tagName === "rect" ? 0.35 + 0.6 * share : 0.25 + 0.45 * share).toFixed(2) : 0));
    ref.collectors.forEach((c, i) => c.setAttribute("opacity", d.pump ? (i % 2 ? 0.9 : 0.5) : 0));
    if (ref.flame) ref.flame.setAttribute("opacity", d.burner ? 0.95 : 0);
    if (ref.soc && d.soc != null) { const h = (ref.soc.max * clamp(d.soc, 0, 100)) / 100; ref.soc.el.setAttribute("y", (ref.soc.bottom - h).toFixed(1)); ref.soc.el.setAttribute("height", h.toFixed(1)); }
    if (ref.tank && d.tankT != null) { const h = clamp((d.tankT - 35) / 25, 0, 1) * ref.tank.max; ref.tank.el.setAttribute("y", (ref.tank.bottom - h).toFixed(1)); ref.tank.el.setAttribute("height", h.toFixed(1)); }

    // network: colour follows the source, grid energy is purple
    const imp = d.grid > 40 ? d.grid : 0, exp = d.grid < -40 ? -d.grid : 0, dis = d.bat < -40 ? -d.bat : 0, chg = d.bat > 40 ? d.bat : 0;
    const SOL = "var(--sol)", GRID = "var(--grid)", local = d.pv + dis;
    net.elec = [
      [d.pv > 40 && ["pv", SOL, false], dis && ["bat", SOL, true], imp && ["grid", GRID, false]].filter(Boolean),
      [d.load > 40 && ["load", local >= imp ? SOL : GRID, false], chg && ["bat", d.pv > 40 ? SOL : GRID, false], exp && ["grid", GRID, true]].filter(Boolean),
    ];
    net.therm = [
      [d.burner && ["gas", "var(--gas)", false], d.pump && ["collHot", "var(--heat)", false]].filter(Boolean),
      [d.burner && [d.dhwMode ? "dhw" : "heat", "var(--heat)", false], d.pump && ["collCold", "var(--cold)", false]].filter(Boolean),
    ];
    net.gridActive = imp > 0 || exp > 0;
    const busy = new Set([...net.elec.flat(), ...net.therm.flat()].map((s) => s[0]));
    for (const ed of Object.values(edges)) ed.base.classList.toggle("idle", !busy.has(ed.key));

    // labels
    const V = (k, main, dim, visible = true) => {
      const L = labels[k]; if (!L) return; L.g.style.display = visible ? "" : "none"; if (!visible) return;
      L.v.textContent = main; if (dim) { const s = document.createElementNS(NS, "tspan"); s.setAttribute("class", "dim"); s.textContent = " · " + dim; L.v.appendChild(s); } L.fit();
    };
    V("load", kw(d.load));
    V("pv", kw(d.pv), null, d.has.pv);
    V("coll", d.pump ? T.pumpOn : T.idle, d.collT != null ? d.collT.toFixed(0) + " °C" : null, d.has.coll);
    V("bat", d.soc != null ? Math.round(d.soc) + " %" : "—", chg ? `${T.charging} ${kw(chg)}` : dis ? `${T.discharging} ${kw(dis)}` : "0 kW", d.has.bat);
    V("grid", net.gridActive ? kw(d.grid) : "0 kW", imp ? T.import : exp ? T.feedin : T.idle);
    V("heat", d.burner ? (d.mod != null ? Math.round(d.mod) + " % " : "") + (d.dhwMode ? T.hotWater : T.space) : T.off, d.tankT != null ? `${T.tank} ${d.tankT.toFixed(0)} °C` : null, d.has.heat);
    V("ev", T.notInstalled);
    // bottom row: keep labels apart, run the leader beside the text like the app does
    const row = Object.values(labels).filter((L) => !L.top && L.g.style.display !== "none").sort((a, b) => a.ax - b.ax);
    for (const L of row) { L.w = Math.max(L.v.getComputedTextLength(), L.k.getComputedTextLength()); L.x0 = L.left ? L.ax - 7 - L.w : L.ax + 7; }
    for (let i = 1; i < row.length; i++) row[i].x0 = Math.max(row[i].x0, row[i - 1].x0 + row[i - 1].w + 26);
    let edge = 1184;
    for (let i = row.length - 1; i >= 0; i--) { row[i].x0 = Math.min(row[i].x0, edge - row[i].w); edge = row[i].x0 - 26; }
    for (const L of row) {
      const rightOf = L.ax <= L.x0 + L.w / 2, lx = rightOf ? L.x0 - 7 : L.x0 + L.w + 7;
      for (const t of [L.v, L.k]) { t.setAttribute("x", (rightOf ? L.x0 : L.x0 + L.w).toFixed(1)); t.setAttribute("text-anchor", rightOf ? "start" : "end"); }
      L.lead.setAttribute("d", Math.abs(lx - L.ax) < 1 ? `M${L.ax.toFixed(1)},${L.ay.toFixed(1)} V${L.y + 14}` : `M${L.ax.toFixed(1)},${L.ay.toFixed(1)} V${L.y - 24} H${lx.toFixed(1)} V${L.y + 14}`);
      L.plate.setAttribute("x", (L.x0 - 10).toFixed(1)); L.plate.setAttribute("width", (L.w + 20).toFixed(1));
    }
    const autarky = Math.round(clamp(1 - imp / Math.max(d.load + chg, 1), 0, 1) * 100);
    pillL.set(`⚡ ${autarky} % ${T.selfSufficient}` + (d.outT != null ? `   |   ${d.outT.toFixed(0)} °C` : ""));
    const right = [d.price != null ? `${d.price.toFixed(3)} ${d.priceUnit || ""}${d.cheap ? " ↓" : ""}` : null, d.co2 != null ? `${Math.round(d.co2)} g CO₂/kWh` : null].filter(Boolean);
    pillR.set(right.join("   |   "));

    // status message from what the battery and the energy manager are doing
    const m = !d.has.bat ? T.m_none : chg && d.pv < chg * 0.5 ? T.m_grid : chg ? T.m_store : dis ? T.m_self : d.soc >= 97 && exp ? T.m_full : d.cheap ? T.m_cheap : T.m_wait;
    return m;
  }
  return { step, render, svg };
}

/* ------------------------------------------------------------------------------------------------
 * Built-in demo scene: a generic two-storey house. Copy it as a starting point for your own scene.
 * ---------------------------------------------------------------------------------------------- */
function demoScene(s) {
  const { P, face, FRONT, EAST, TOP, el, rect, poly, mix, COL, layers, win, glass, shade, plaster, eave } = s;
  const PITCH = (35 * Math.PI) / 180, CP = Math.cos(PITCH), SP = Math.sin(PITCH), T = Math.tan(PITCH);
  const X0 = 0, X1 = 1100, Y0 = 0, Y1 = 900, EAVE = 560, OV = 60, YR = (Y0 + Y1) / 2, ZR = EAVE + (YR - Y0) * T, TV = 25 / CP;
  // ground
  { const g = TOP(layers.ground, 0, 0, 0);
    poly([[-1600, -1000], [2800, -1000], [2800, 1400], [-1600, 1400]], "url(#lawn)", g);
    poly([[-1600, -2800], [2800, -2800], [2800, -1500], [-1600, -1500]], "url(#lawn)", g);
    poly([[-1600, -1500], [2800, -1500], [2800, -1000], [-1600, -1000]], COL.asphalt, g);
    rect(-1600, -1004, 4400, 8, "#cfcac0", g);
    for (let x = -1600; x < 2800; x += 160) rect(x, -1254, 70, 6, "#d9d6cc", g);
    poly([[1180, 300], [1560, 300], [1580, -1000], [1160, -1000]], COL.asphalt, g);
    poly([[420, 0], [620, 0], [640, -1000], [400, -1000]], "url(#paving)", g);
    const cs = el("g", { filter: "url(#soft)", opacity: 0.4 }, g); poly([[-30, -30], [X1 + 40, -30], [X1 + 40, Y1 + 40], [-30, Y1 + 40]], "#1b1712", cs);
  }
  const H = layers.house;
  // north slope (visible past the east gable), east wall with gable, front wall
  { const g = face(H, [-OV, YR, ZR + TV], [1, 0, 0], [0, CP, -SP]); const len = (Y1 + OV - YR) / CP; rect(0, 0, X1 + 2 * OV, len, "url(#roof)", g); rect(0, 0, X1 + 2 * OV, len, "#000", g, { opacity: 0.32 }); }
  { const g = EAST(H, X1, Y0, ZR); const pts = [[0, ZR - EAVE], [YR, 0], [Y1, ZR - EAVE], [Y1, ZR], [0, ZR]];
    plaster(g, pts); rect(0, ZR - 40, Y1, 40, "url(#brown)", g); win(g, 300, ZR - 450, 110, 120); win(g, 560, ZR - 450, 110, 120); win(g, 430, ZR - 200, 110, 120); shade(g, pts, 0.2); }
  { const g = FRONT(H, X0, Y0, EAVE); plaster(g, [[0, 0], [X1, 0], [X1, EAVE], [0, EAVE]]); rect(0, EAVE - 40, X1, 40, "url(#brown)", g);
    win(g, 110, 90, 200, 130, 2); win(g, 450, 90, 200, 130, 2); win(g, 790, 90, 200, 130, 2);
    win(g, 110, 360, 200, 130, 2); win(g, 790, 360, 200, 130, 2);
    rect(452, 315, 196, 245, COL.wood, g); rect(470, 330, 160, 230, "#4a2d20", g); glass(g, 520, 350, 60, 150); eave(g, 0, X1); }
  // roof: fascia, east verge, south slope with PV
  { const g = FRONT(H, -OV, -OV, EAVE - OV * T + TV); rect(0, 0, X1 + 2 * OV, TV, COL.fascia, g); }
  { const g = EAST(H, X1 + OV, -OV, ZR + TV); const a = ZR - (EAVE - OV * T); poly([[0, a], [YR + OV, 0], [Y1 + 2 * OV, a], [Y1 + 2 * OV, a + TV], [YR + OV, TV], [0, a + TV]], mix(COL.fascia, "#000", 0.1), g); }
  const slope = face(H, [-OV, YR, ZR + TV], [1, 0, 0], [0, -CP, -SP]), len = (YR + OV) / CP;
  poly([[0, 0], [X1 + 2 * OV, 0], [X1 + 2 * OV, len], [0, len]], "url(#roof)", slope); poly([[0, 0], [X1 + 2 * OV, 0], [X1 + 2 * OV, len], [0, len]], "url(#slopeShade)", slope);
  rect(0, -3, X1 + 2 * OV, 7, "#2d2019", slope);
  const pv = face(H, [-OV, YR - 10 * SP, ZR + TV + 10 * CP], [1, 0, 0], [0, -CP, -SP]);
  s.pvArray(pv, 180, 60, 7, 2);
  // equipment in front of the house, wallbox at the east wall
  s.battery(150, -60); s.ems(260, -2, 215); s.boiler(X1 + 40, 80); s.tank(X1 + 40, 160);
  s.wallbox(EAST(H, X1, 0, 200), 40, 60);
  const roofTop = (x, y) => [x, y, EAVE + (y - Y0) * T + TV + 10];
  return {
    edges: {
      pv: [roofTop(330, 180), [330, -OV, EAVE - OV * T + TV], [330, -2, 450], [292, -2, 450], [292, -2, 215]],
      load: [[260, -2, 180], [240, -2, 180], [240, -2, 300]],
      bat: [[292, -2, 145], [292, -2, 112], [292, -40, 112]],
      grid: [[-719, -1000, 0], [130, -1000, 0], [130, -2, 0], [130, -2, 170], [260, -2, 170]],
      ev: [[324, -2, 160], [380, -2, 160], [380, -2, 0], [380, -20, 0], [X1 + 20, -20, 0], [X1, 40, 0], [X1, 40, 140]],
      gas: [[X1 + 70, -1000, 0], [X1 + 70, 80, 0], [X1 + 70, 80, 30]],
      heat: [[X1 + 40, 105, 118], [X1, 105, 118], [X1, 105, 300]],
      dhw: [[X1 + 105, 105, 60], [X1 + 105, 160, 60]],
    },
    labels: [
      { key: "pv", anchor: P(...roofTop(560, 300)), y: 26 },
      { key: "grid", anchor: [46, 498], y: 560 },
      { key: "load", anchor: P(240, 1, 300), y: 560, side: "left" },
      { key: "bat", anchor: P(195, -60, 60), y: 560 },
      { key: "heat", anchor: P(X1 + 70, 80, 60), y: 560 },
      { key: "ev", anchor: P(X1, 50, 150), y: 560, dim: true },
    ],
  };
}

/* ------------------------------------------------------------------------------------------------
 * The card element
 * ---------------------------------------------------------------------------------------------- */
const ICON = '<svg viewBox="0 0 26 26" aria-hidden="true"><rect x="6" y="3" width="14" height="20" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M14 8 l-4 6 h4 l-2 5" fill="none" stroke="#8f63f2" stroke-width="1.8" stroke-linejoin="round"/></svg>';
const SKY = { "clear-night": "clear", sunny: "clear", windy: "clear", partlycloudy: "cloudy", cloudy: "cloudy", fog: "cloudy", "windy-variant": "cloudy", exceptional: "cloudy",
  rainy: "rain", pouring: "rain", lightning: "rain", "lightning-rainy": "rain", hail: "rain", snowy: "rain", "snowy-rainy": "rain" };

class EnergyHubHouseCard extends HTMLElement {
  setConfig(config) {
    if (config.actions && typeof config.actions !== "object") throw new Error("actions must be a mapping of zone or group to an action");
    const rebuild = this._config && (this._config.scene !== config.scene);
    this._config = { show_status: true, ...config };
    if (rebuild) { this._engine = null; this._building = null; }
    if (this._hass) this._update();
  }
  set hass(hass) { this._hass = hass; this._update(); }
  getCardSize() { return 9; }
  getGridOptions() { return { columns: "full", min_columns: 6, rows: "auto" }; }
  static getStubConfig(hass) { return { entity: findFlowEntity(hass) || "sensor.energy_hub_flow_state" }; }

  connectedCallback() {
    this._running = true; let last = performance.now();
    const loop = (now) => { if (!this._running) return; const dt = Math.min(0.05, (now - last) / 1000); last = now; if (this._engine && !this._reduced) this._engine.step(dt); this._raf = requestAnimationFrame(loop); };
    this._reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this._raf = requestAnimationFrame(loop);
  }
  disconnectedCallback() { this._running = false; cancelAnimationFrame(this._raf); }

  get _T() { const l = (this._hass?.locale?.language || this._hass?.language || "en").slice(0, 2); return STR[l] || STR.en; }

  async _build() {
    const root = this.shadowRoot || this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${CSS}</style><ha-card><svg viewBox="0 0 1200 600" role="img"></svg>${this._config.show_status ? `<div class="msg">${ICON}<div><div class="t"></div><div class="d"></div></div></div>` : ""}</ha-card>`;
    let sceneFn = demoScene;
    if (this._config.scene && this._config.scene !== "demo") {
      try { sceneFn = (await import(this._config.scene)).default; }
      catch (err) { console.error("energy-hub-house-card: cannot load scene", this._config.scene, err); }
    }
    const svg = root.querySelector("svg");
    svg.setAttribute("aria-label", this._T.ems);
    this._engine = createEngine(svg, sceneFn, this._T);
    svg.addEventListener("click", (ev) => this._tap(ev));
    svg.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); this._tap(ev); } });
    for (const z of svg.querySelectorAll("[data-zone]")) z.setAttribute("aria-label", this._T[z.dataset.zone] || z.dataset.zone);
    this._sig = null;
  }

  _update() {
    if (!this._hass || !this._config) return;
    if (!this._engine) { if (!this._building) this._building = this._build().then(() => this._update()); return; }
    const d = this._data();
    const sig = JSON.stringify(d);
    if (sig === this._sig) return;
    this._sig = sig;
    const [t, desc] = this._engine.render(d, this._T);
    const msg = this.shadowRoot.querySelector(".msg");
    if (msg) {
      const now = new Date(), m0 = now.getHours() * 60 + now.getMinutes() - (now.getMinutes() % 15), hh = (m) => String(Math.floor(m / 60) % 24).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
      msg.querySelector(".t").textContent = `${hh(m0)} – ${hh(m0 + 15)} · ${t}`; msg.querySelector(".d").textContent = desc;
    }
  }

  get _entity() { return this._config.entity || (this._autoEntity ||= findFlowEntity(this._hass)); }

  _data() {
    const h = this._hass, st = h.states[this._entity], a = st?.attributes || {}, src = a.sources || {};
    const num = (id) => { const s = id && h.states[id]; const v = s ? parseFloat(s.state) : NaN; return Number.isFinite(v) ? v : null; };
    const on = (id) => { const s = id && h.states[id]; if (!s) return null; const v = String(s.state).toLowerCase(); return v === "on" || v === "true" || parseFloat(v) > 0; };
    const n = (v) => (typeof v === "number" ? v : v == null ? null : Number.isFinite(parseFloat(v)) ? parseFloat(v) : null);
    const sunSt = h.states["sun.sun"], weatherId = this._config.weather || Object.keys(h.states).find((id) => id.startsWith("weather."));
    const w = weatherId && h.states[weatherId];
    const mod = num(src.burner_modulation), burner = mod != null ? mod > 0 : !!on(src.burner_active);
    const collT = num(src.solar_collector_temp), tankT = num(src.dhw_storage_temp) ?? num(src.solar_storage_temp), storT = num(src.solar_storage_temp) ?? tankT;
    const pumpOn = on(src.solar_pump), pump = pumpOn != null ? pumpOn : collT != null && storT != null && collT > storT + 6;
    const outT = num(src.outside_temp) ?? n(w?.attributes?.temperature);
    const soc = n(a.battery_soc) ?? num(src.battery_soc);
    return {
      pv: n(a.pv_power) ?? num(src.pv_power) ?? 0, load: n(a.load_power) ?? 0,
      bat: (n(a.battery_charge_power) ?? 0) - (n(a.battery_discharge_power) ?? 0), soc,
      grid: (n(a.grid_import_power) ?? 0) - (n(a.grid_export_power) ?? 0), cheap: !!a.cheap_now,
      pvPeak: this._config.pv_peak_power ?? 10000,
      mod, burner, dhwMode: outT == null || outT >= 16, collT, tankT, pump, outT,
      price: num(src.import_price), priceUnit: src.import_price ? h.states[src.import_price]?.attributes?.unit_of_measurement : null, co2: num(src.grid_co2_intensity),
      elevation: n(sunSt?.attributes?.elevation) ?? 30, azimuth: n(sunSt?.attributes?.azimuth) ?? 180, sky: SKY[w?.state] || "clear",
      has: { pv: !!(src.pv_power || a.pv_power), coll: !!src.solar_collector_temp, bat: !!(src.battery_power || src.battery_soc), heat: !!(src.burner_modulation || src.burner_active || src.dhw_storage_temp || src.gas_heating_volume) },
    };
  }

  _tap(ev) {
    const z = ev.target.closest?.("[data-zone]"); if (!z) return;
    const name = z.dataset.zone, acts = this._config.actions || {};
    let action = acts[name] || acts[GROUP[name]] || { action: "more-info" };
    if (action.action === "none") return;
    const src = this._hass.states[this._entity]?.attributes?.sources || {};
    const entity = action.entity || (ZONE_ENTITY[name] || []).map((k) => src[k]).find(Boolean) || this._entity;
    if (action.action === "navigate" && action.navigation_path && !action.navigation_path.startsWith("/")) {
      const base = location.pathname.split("/").filter(Boolean)[0] || "lovelace";
      action = { ...action, navigation_path: `/${base}/${action.navigation_path}` };
    }
    this.dispatchEvent(new CustomEvent("hass-action", { bubbles: true, composed: true, detail: { config: { entity, tap_action: action }, action: "tap" } }));
  }
}

function findFlowEntity(hass) {
  if (!hass) return null;
  const reg = hass.entities || {};
  return Object.keys(reg).find((id) => reg[id].platform === "energy_hub" && id.endsWith("_flow_state"))
    || Object.keys(hass.states).find((id) => id.startsWith("sensor.") && id.endsWith("_flow_state") && hass.states[id].attributes?.sources);
}

if (!customElements.get("energy-hub-house-card")) customElements.define("energy-hub-house-card", EnergyHubHouseCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "energy-hub-house-card"))
  window.customCards.push({ type: "energy-hub-house-card", name: "Energy Hub house", description: "Illustrated house with live energy flows, from the Energy Hub integration.", preview: false });
console.info(`%c ENERGY-HUB-HOUSE-CARD %c ${VERSION} `, "background:#2fd3ad;color:#0d1b16;font-weight:600", "background:#1d2430;color:#fff");
