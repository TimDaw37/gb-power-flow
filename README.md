# GB Power Flow

A live, indicative map of where Great Britain's electricity is generated, where it is consumed, and how it moves between regions and across the interconnectors.

**Live page:** https://timdaw37.github.io/gb-power-flow/

The page is a single self-contained HTML file. It fetches open data directly in the browser on load and every 5 minutes after that. It has no backend and needs no API keys.

## Features

- Animated flows between the 14 DNO areas, and across each interconnector.
- Regions can be coloured by export/import balance, by the carbon intensity of their supply, or by their share of the selected region's supply.
- Zoom and pan: mouse wheel, double-click, drag, pinch on touch screens, the + / − / ⤢ buttons, or the + − 0 keys. Lines, dots and text keep their on-screen size, and stations are named once zoomed in.
- Prices: wholesale market index and imbalance (cash-out) price for the half-hour, with a 48-hour chart (click it to jump to that time).
- Price units: switch between p/kWh (as on a household bill; the default) and £/MWh (as traded) from the header. The choice is remembered in the browser.
- Tap a power station or £ mark to see its details; on a phone this no longer jumps down to the region panel.
- Balancing payments: what each unit was paid (or paid back) by the system operator to increase or reduce output, as up or down block arrows with a £ inside, sized by amount, a national summary, the largest payments and a per-region line.
- Click a region to see its traced supply by region and by fuel, with its carbon intensity.
- **Money in / out:** a fourth colouring that shows the £ for the half-hour instead of the MW: gold arrows run against the power (the importing region pays the exporting one, GB pays abroad for imports), regions are coloured by net £ received or paid, and each region's panel breaks it down into wholesale, CfD difference payments and balancing, with its share of the CfD levy and balancing costs.
- ◀ ▶ (or the arrow keys) step back through the last 48 hours, one half-hour settlement period at a time. **Live** returns to now.
- Deep links to a region, e.g. `#london` or `#north-scotland`.

## Method

| Step | Source | Treatment |
|---|---|---|
| Unit output | Elexon BMRS: Physical Notifications (PN) and bid-offer acceptances (BOALF) for the current settlement period | Each unit's level is interpolated at the current time. Where a unit has an accepted bid-offer, the latest acceptance replaces its notification. |
| Unit location | OSUKED Power Station Dictionary, plus about 90 newer plants located by hand (`data/manual_locations.json`); locations found to be wrong are corrected in `data/location_overrides.json` (checked in Nov 2026 against Wikidata and the DESNZ Renewable Energy Planning Database: about 100 sites moved, mostly by 2–90 km) | Each unit is assigned to a DNO licence area by point-in-polygon. Units at the same site are drawn as one circle. Offshore wind is drawn at its array, with a dashed line to its onshore grid connection, and is assigned to the area of that connection (`data/offshore.json`; positions approximate). |
| National totals | Elexon FUELINST (5-minute metered generation by fuel, and each interconnector) | Located unit output is scaled to the metered total. Interconnector flows come from FUELINST. |
| Embedded generation | NESO embedded wind and solar forecast (national) | Split between areas using indicative capacity shares. |
| Regional demand | Supplier BM units' PN for each GSP group | Total demand is generation plus net imports, less storage charging. It is split between areas in proportion to the suppliers' notified demand. |
| Inter-regional flow | — | DC power flow on a reduced network of 14 nodes and 23 paths. Each path is weighted by a rough transfer capability. |
| Origin of supply | — | Proportional-sharing flow tracing (Bialek). This is an accounting convention: power does not travel from a specific source to a specific consumer. |
| Carbon intensity | Approximate emission factors (after NESO's Carbon Intensity API methodology); a separate factor for each interconnector's country | Applied to the traced fuel mix. |
| Prices | Elexon market index data (APX) and system prices | National figures; no regional price exists in GB. |
| Balancing payments | Elexon indicative bid and offer cashflows per BM unit | Summed per unit; offers = paid to increase output, positive bids = paid to reduce (typically wind), negative bids = paid back (fuel not burnt). Latest published half-hour in live view. |
| Money | Market index price; LCCC current CfD strike prices and CfD→BM unit mapping (`data/cfd.json`, built by `scripts/build_cfd.py`); balancing cashflows above | Wholesale = MWh × market index for use and generation; CfD = (strike − reference price) × output per contracted unit (no payment at negative prices for AR4+), funded by all demand pro rata; balancing funded by all demand pro rata. Sums to zero with money paid abroad. About 1.3 GW of small distribution-connected CfDs are not counted. |
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
scripts/build_cfd.py       builds data/cfd.json from the LCCC data portal (re-run when contracts start, and after April indexation)
scripts/assemble.py        inlines geo.json, cfd.json and model.js into index.html
```

## Rebuilding

```
scripts/fetch_inputs.sh
python3 scripts/build_geo.py
python3 scripts/build_cfd.py
python3 scripts/assemble.py
```

Only needed when plant locations, boundaries or CfD contracts change; the page itself fetches live data on load.

## Licence

The code (everything in this repository apart from the data noted below) is released under the [MIT licence](LICENSE): free to use, copy and adapt, provided the copyright notice is kept.

## Data licences

- Elexon BMRS data: Elexon BMRS licence.
- NESO data: NESO Open Data Licence.
- Power Station Dictionary: see the OSUKED repository.
- CfD data: Low Carbon Contracts Company data portal (Open Government Licence).
- Location checks: Wikidata (CC0) and DESNZ Renewable Energy Planning Database (Open Government Licence).
- Coastlines: Natural Earth (public domain).
