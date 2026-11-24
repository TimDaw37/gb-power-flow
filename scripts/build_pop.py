"""Build data/pop.json: GB towns and cities as [x, y, population] in the map's BNG-km coordinates.

Used by the Landscape view to spread each region's demand towards where people live.
Source: GeoNames 'cities1000' (places of 1,000+ people), as packaged in the npm module all-the-cities (MIT):
    npm pack all-the-cities && tar xzf all-the-cities-*.tgz   ->  package/cities.pbf
    python3 scripts/build_pop.py package/cities.pbf
GeoNames data is CC BY 4.0 (geonames.org). Northern Ireland is excluded (not on the GB grid).
"""
import sys, json
from pathlib import Path
from pyproj import Transformer

buf = open(sys.argv[1], 'rb').read()
def varint(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7f) << s; s += 7
        if x < 0x80: return r, i
sv = lambda n: (n >> 1) ^ -(n & 1)
T = Transformer.from_crs(4326, 27700, always_xy=True)
i = lon = lat = 0; out = []
while i < len(buf):
    ln, i = varint(buf, i); end = i + ln; c = {'pop': 0}
    while i < end:
        key, i = varint(buf, i); tag, wt = key >> 3, key & 7
        if wt == 2:
            l, i = varint(buf, i); v = buf[i:i+l].decode('utf-8', 'replace'); i += l
            if tag == 3: c['country'] = v
            elif tag == 8: c['admin'] = v
        else:
            v, i = varint(buf, i)
            if tag == 9: c['pop'] = v
            elif tag == 10: lon += sv(v)
            elif tag == 11: lat += sv(v)
            if tag in (10, 11): c['ll'] = (lat / 1e5, lon / 1e5)
    if c.get('country') == 'GB' and c.get('admin') != 'NIR' and c['pop'] > 0:
        x, y = T.transform(c['ll'][1], c['ll'][0])
        out.append([round(x / 1000, 1), round(1230 - y / 1000, 1), c['pop']])
Path(__file__).resolve().parent.parent.joinpath('data', 'pop.json').write_text(json.dumps(out, separators=(',', ':')))
print(len(out), 'places, population %.1f M' % (sum(p[2] for p in out) / 1e6))
