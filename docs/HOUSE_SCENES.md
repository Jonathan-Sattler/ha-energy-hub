# House scenes

The house card draws a *scene*: a small JavaScript module that describes one
house. The card ships a generic demo house; your own house lives in a file you
keep in Home Assistant, for example `/config/www/energy-hub/house.js`, used
with `scene: /local/energy-hub/house.js`.

## Coordinates

Everything is in centimetres of the real building. `x` runs east along the
street-facing wall, `y` runs away from the street, `z` is up. The origin is the
south-west corner of the main block at ground level. The card projects this
obliquely, so the south wall faces the viewer and the east side and the south
roof slope are visible. One centimetre is 0.36 SVG pixels; the image is
1200 × 600.

## The module

```js
export default function scene(s) {
  const { P, FRONT, EAST, TOP, face, rect, poly, COL, layers, win, plaster, shade } = s;
  const H = layers.house;
  // walls: FRONT(parent, x0, y, zTop) gives a group in local cm, u to the right, v down from zTop
  const front = FRONT(H, 0, 0, 560);
  plaster(front, [[0, 0], [1100, 0], [1100, 560], [0, 560]]);
  win(front, 110, 90, 200, 130, 2);
  // ... roof slopes with face(parent, origin, u, v), PV with s.pvArray(slopeGroup, x, t, cols, rows)
  s.battery(150, -60); s.ems(260, -2, 215); s.boiler(1140, 80); s.tank(1140, 160);
  return {
    edges: { pv: [[x, y, z], ...], load: [...], bat: [...], grid: [...], gas: [...], heat: [...], dhw: [...], collHot: [...], collCold: [...], ev: [...] },
    labels: [{ key: "pv", anchor: P(x, y, z), y: 26 }, { key: "bat", anchor: P(x, y, z), y: 560 }],
  };
}
```

- `FRONT`, `EAST`, `TOP` and `face` return SVG groups mapped onto a model
  plane, so material patterns (`url(#plaster)`, `#brown`, `#clinker`, `#roof`,
  `#wood`, `#door`, `#paving`) keep their real size.
- `s.battery`, `s.ems`, `s.boiler`, `s.tank`, `s.wallbox`, `s.pvArray` and
  `s.collector` draw the equipment the card animates and make it clickable.
- `edges` are cable runs as model points (or an SVG path string). The card
  animates the keys it knows: `pv`, `bat`, `grid` and `ev` run into or out of
  the energy manager, `load` runs to the household, `gas`, `heat`, `dhw`,
  `collHot` and `collCold` form the heating loop. Missing keys are skipped.
- `labels` place the value labels: `y: 26` for the top row, `y: 560` for the
  bottom row, `side: "left"` to put the text left of the leader.
- Optional: `horizon` (default 368) and `pole: { x, top, base }` for the grid
  pole, or `pole: null` to hide it.

The demo scene at the bottom of `frontend/card.src.js` is a complete example.
