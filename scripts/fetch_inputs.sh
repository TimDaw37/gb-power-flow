#!/usr/bin/env bash
# Downloads the inputs build_geo.py needs into ./inputs (not committed).
set -euo pipefail
cd "$(dirname "$0")/.."; mkdir -p inputs; cd inputs
curl -sL -o dno.geojson "https://api.neso.energy/dataset/0e377f16-95e9-4c15-a1fc-49e06a39cfa0/resource/1c6a7dc0-1b6c-443a-bc67-5f7125649434/download/gb-dno-license-areas-20240503-as-geojson.geojson"
curl -s -o bmu.json "https://data.elexon.co.uk/bmrs/api/v1/reference/bmunits/all"
[ -d power-station-dictionary ] || git clone -q --depth 1 https://github.com/OSUKED/power-station-dictionary
npm i -s --prefix . world-atlas@2 topojson-client@3 >/dev/null
node -e "
const t=require('./node_modules/topojson-client');const w=require('./node_modules/world-atlas/countries-50m.json');
const fc=t.feature(w,w.objects.countries);const keep=['Ireland','France','Belgium','Netherlands','Norway','Denmark','Germany','United Kingdom','Luxembourg','Sweden','Faeroe Is.','Switzerland','Spain','Poland'];
fc.features=fc.features.filter(f=>keep.includes(f.properties.name));require('fs').writeFileSync('eu.geojson',JSON.stringify(fc));"
echo "inputs ready; now: python3 scripts/build_geo.py && python3 scripts/assemble.py"
