import json, csv, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
INP = ROOT / 'inputs'   # populated by scripts/fetch_inputs.sh (not committed)
from pyproj import Transformer
from shapely.geometry import shape, Point, box, mapping
from shapely.ops import transform
T = Transformer.from_crs(4326, 27700, always_xy=True)
def ll(lat, lon):
    x, y = T.transform(lon, lat); return x/1000, y/1000
BX = (-230, -40, 830, 1230)   # km BNG view box
def svgpath(geom, tol):
    g = geom.simplify(tol, preserve_topology=True)
    polys = [g] if g.geom_type == 'Polygon' else list(g.geoms)
    out = []
    for p in polys:
        if p.area < 4: continue
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords)
            if len(cs) < 4: continue
            out.append('M' + 'L'.join(f'{x:.1f},{BX[3]-y:.1f}' for x, y in cs) + 'Z')
    return ''.join(out)

dno = json.load(open(INP/'dno.geojson'))
NAMES = {'_A':'Eastern','_B':'East Midlands','_C':'London','_D':'Merseyside & N Wales','_E':'West Midlands',
 '_F':'North East','_G':'North West','_H':'Southern','_J':'South East','_K':'South Wales','_L':'South West',
 '_M':'Yorkshire','_N':'South Scotland','_P':'North Scotland'}
zones = {}
for f in dno['features']:
    z = f['properties']['Name']
    g = transform(lambda x, y, z=None: (x/1000, y/1000), shape(f['geometry'])).buffer(0)
    zones[z] = g
print(sorted(zones))
# country backgrounds (lon/lat) -> BNG km, clipped
eu = json.load(open(INP/'eu.geojson'))
clip = box(BX[0]-600, BX[1]-300, BX[2]+800, BX[3]+400)
land = []
for f in eu['features']:
    g = transform(lambda x, y, z=None: ll(y, x) if False else tuple(v/1000 for v in T.transform(x, y)), shape(f['geometry'])).buffer(0).intersection(clip)
    if g.is_empty: continue
    land.append({'name': f['properties']['name'], 'd': svgpath(g, 1.5)})
# plants
P = str(INP/'power-station-dictionary'/'data')+'/'
loc = {r['dictionary_id']: (float(r['latitude']), float(r['longitude'])) for r in csv.DictReader(open(P+'attribute_sources/plant-locations/plant-locations.csv'))}
pts = {}   # bmu -> (lat,lon,name)
for row in csv.DictReader(open(P+'dictionary/ids.csv')):
    if row['dictionary_id'] not in loc: continue
    for s in row['sett_bmu_id'].split(','):
        s = s.strip()
        if s and not s.startswith('I_'): pts[s] = (*loc[row['dictionary_id']], row['name'])
# correct Power Station Dictionary locations that are wrong (prefix of the BMU id without its T_/E_ etc.)
for pre, v in json.load(open(ROOT/'data'/'location_overrides.json')).items():
    for u in list(pts):
        if u[2:].startswith(pre): pts[u] = (v[0], v[1], v[2])
manual = json.load(open(ROOT/'data'/'manual_locations.json'))
bm = json.load(open(INP/'bmu.json'))
ref = {x['elexonBmUnit']: x for x in bm if x['elexonBmUnit']}
for u, x in ref.items():
    if u in pts or u.startswith('I_'): continue
    k = u[2:].split('-')[0].rstrip('0123456789')[:5]
    for pre, v in manual.items():
        if u[2:].startswith(pre):
            pts[u] = (v[0], v[1], v[2]); break
def zone_of(x, y):
    p = Point(x, y)
    for z, g in zones.items():
        if g.contains(p): return z
    return min(zones, key=lambda z: zones[z].distance(p))
ft = {r['ngc_bmu_id']: r['fuel_type'] for r in csv.DictReader(open(P+'attribute_sources/bmu-fuel-types/fuel_types.csv', encoding='utf-8-sig'))}
def fuel_of(u, name):
    f = (ref.get(u) or {}).get('fuelType') or ft.get(u[2:]) or ''
    if f: return f
    n = (name or '').lower()
    for pat, k in [(r'bess|battery|storage', 'BATTERY'), (r'solar|pv', 'SOLAR'), (r'wind|\bwf\b|offshore', 'WIND'),
                   (r'hydro', 'NPSHYD'), (r'nuclear', 'NUCLEAR'), (r'ccgt|gas|peaker|power station', 'CCGT'), (r'bio|chp|energy from waste|efw', 'BIOMASS')]:
        if re.search(pat, n): return k
    return ''
plants = []
# offshore wind: drawn at the array, credited to the region of its onshore grid connection
OFF = {k: v for k, v in json.load(open(ROOT/'data'/'offshore.json')).items() if not k.startswith('_')}
for u, (lat, lon, name) in pts.items():
    off = next((v for k, v in sorted(OFF.items(), key=lambda kv: -len(kv[0])) if u[2:].startswith(k)), None)
    if off:
        x, y = ll(off[1], off[2]); lx, ly = ll(off[4], off[5])
        plants.append([u, round(x, 1), round(BX[3]-y, 1), zone_of(lx, ly), fuel_of(u, name) or 'WIND', off[0], round(lx, 1), round(BX[3]-ly, 1), off[3]])
        continue
    x, y = ll(lat, lon)
    plants.append([u, round(x, 1), round(BX[3]-y, 1), zone_of(x, y), fuel_of(u, name), name])
gsp = {u: x['gspGroupId'] for u, x in ref.items() if x.get('gspGroupId') and u not in pts and not u.startswith('I_')}
# zone label points
zinfo = {}
for z, g in zones.items():
    c = g.representative_point() if not g.centroid.within(g) else g.centroid
    zinfo[z] = {'name': NAMES[z], 'd': svgpath(g, 1.2), 'cx': round(c.x, 1), 'cy': round(BX[3]-c.y, 1)}
IC = [ # fuelinst key, name, country, landing lat/lon, far lat/lon
 ['INTFR','IFA','France',51.106,1.003,50.89,1.85],
 ['INTIFA2','IFA2','France',50.83,-1.27,49.17,-0.33],
 ['INTELEC','ElecLink','France',51.10,1.13,50.93,1.80],
 ['INTNED','BritNed','Netherlands',51.45,0.71,51.96,4.02],
 ['INTNEM','Nemo Link','Belgium',51.30,1.34,51.32,3.20],
 ['INTNSL','North Sea Link','Norway',55.14,-1.51,59.52,6.64],
 ['INTVKL','Viking Link','Denmark',52.93,-0.20,55.52,9.15],
 ['INTIRL','Moyle','N Ireland',55.07,-4.98,54.84,-5.77],
 ['INTEW','East–West','Ireland',53.23,-3.08,53.52,-6.10],
 ['INTGRNL','Greenlink','Ireland',51.68,-4.99,52.36,-6.98]]
ics = []
for k, n, c, a, b, d, e in IC:
    x1, y1 = ll(a, b); x2, y2 = ll(d, e)
    ics.append({'key': k, 'name': n, 'country': c, 'zone': zone_of(x1, y1),
                'x1': round(x1,1), 'y1': round(BX[3]-y1,1), 'x2': round(x2,1), 'y2': round(BX[3]-y2,1)})
out = {'view': [BX[0], 0, BX[2]-BX[0], BX[3]-BX[1]], 'ox': BX[0], 'zones': zinfo, 'land': land, 'plants': plants, 'gsp': gsp, 'ics': ics}
json.dump(out, open(ROOT/'data'/'geo.json', 'w'), separators=(',', ':'))
print(len(plants), 'plants', len(gsp), 'gsp-only', [ (i['name'], i['zone']) for i in ics])
