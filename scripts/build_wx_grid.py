import json
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from pyproj import Transformer
T=Transformer.from_crs(4326,27700,always_xy=True)
dno=json.load(open('/home/claude/build/dno.geojson'))
Z={f['properties']['Name']:shape(f['geometry']).buffer(0) for f in dno['features']}
U=unary_union(list(Z.values())).simplify(500)
pts=[]
lat=49.9
while lat<=60.9:
    lon=-7.6
    while lon<=2.4:
        x,y=T.transform(lon,lat); p=Point(x,y)
        d=U.distance(p)
        if d<30000:
            z=next((k for k,g in Z.items() if g.contains(p)),None)
            pts.append([round(lat,2),round(lon,2),round(x/1000,1),round(1230-y/1000,1),z])
        lon+=1.0
    lat+=0.6
print(len(pts), sum(1 for p in pts if p[4]))
json.dump(pts,open('/home/claude/build/wx.json','w'),separators=(',',':'))
zi={}
for k,g in Z.items():
    gb=g.buffer(25000)
    zi[k]=[i for i,p in enumerate(pts) if gb.contains(Point(*T.transform(p[1],p[0])))]
print({k:len(v) for k,v in zi.items()})
json.dump({'pts':[p[:4] for p in pts],'zone':zi},open('/home/claude/build/wx.json','w'),separators=(',',':'))
