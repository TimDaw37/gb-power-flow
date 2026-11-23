# GB Power Flow

A live, indicative map of where Great Britain's electricity is generated, where it is consumed, and how it moves between regions and across the interconnectors.

**Live page:** https://timdaw37.github.io/gb-power-flow/

The page is a single self-contained HTML file. It fetches open data directly in the browser on load and every 5 minutes after that. It has no backend and needs no API keys.

## Features

- Animated flows between the 14 DNO areas, and across each interconnector.
- Regions can be coloured by export/import balance, by the carbon intensity of their supply, or by their share of the selected region's supply.
- Click a region to see its traced supply by region and by fuel, with its carbon intensity.
- ◀ ▶ (or the arrow keys) step back through the last 48 hours, one half-hour settlement period at a time. **Live** returns to now.
- Deep links to a region, e.g. `#london` or `#north-scotland`.

## Method

| Step | Source | Treatment |
|---|---|---|
| Unit output | Elexon BMRS: Physical Notifications (PN) and bid-offer acceptances (BOALF) for the current settlement period | Each unit's level is interpolated at the current time. Where a unit has an accepted bid-offer, the latest acceptance replaces its notification. |
| Unit location | OSUKED Power Station Dictionary, plus about 90 newer plants located by hand (`data/manual_locations.json`) | Each unit is assigned to a DNO licence area by point-in-polygon. Offshore wind is assigned to the area where it lands. |
| National totals | Elexon FUELINST (5-minute metered generation by fuel, and each interconnector) | Located unit output is scaled to the metered total. Interconnector flows come from FUELINST. |
| Embedded generation | NESO embedded wind and solar forecast (national) | Split between areas using indicative capacity shares. |
| Regional demand | Supplier BM units' PN for each GSP group | Total demand is generation plus net imports, less storage charging. It is split between areas in proportion to the suppliers' notified demand. |
| Inter-regional flow | — | DC power flow on a reduced network of 14 nodes and 23 paths. Each path is weighted by a rough transfer capability. |
| Origin of supply | — | Proportional-sharing flow tracing (Bialek). This is an accounting convention: power does not travel from a specific source to a specific consumer. |
| Carbon intensity | Approximate emission factors (after NESO's Carbon Intensity API methodology); a separate factor for each interconnector's country | Applied to the traced fuel mix. |
| Check | NESO day-ahead constraint flows (SCOTEX / B6) | Shown beside the model's Scotland→England flow. |

### Limitations

- Flows are a zonal approximation. They are not the flows on any real circuit.
- The Western HVDC Link is a controlled link, but it is treated as an ordinary path.
- Regional shares of embedded generation are fixed, not live.
- PN is planned output. Actual metered output differs, especially for units responding to frequency.

## Layout

```
index.html                 the published page (built)
src/page.html              page template
src/model.js               zonal balance, DC power flow, flow tracing
data/geo.json              projected DNO areas, coastline, plant locations, interconnectors (built)
data/manual_locations.json hand-located BM units
scripts/fetch_inputs.sh    downloads build inputs into ./inputs (NESO DNO GeoJSON, Elexon BMU reference, Power Station Dictionary, world-atlas)
scripts/build_geo.py       builds data/geo.json from ./inputs
scripts/assemble.py        inlines geo.json and model.js into index.html
```

## Rebuilding

```
scripts/fetch_inputs.sh
python3 scripts/build_geo.py
python3 scripts/assemble.py
```

Only needed when plant locations or boundaries change; the page itself fetches live data on load.

## Data licences

- Elexon BMRS data: Elexon BMRS licence.
- NESO data: NESO Open Data Licence.
- Power Station Dictionary: see the OSUKED repository.
- Coastlines: Natural Earth (public domain).
