"""Download the open geodata the generator needs into generator/data (about 30 MB)."""
import os, sys, urllib.request

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
NE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson'
NE_FILES = ['ne_10m_land', 'ne_10m_minor_islands', 'ne_10m_lakes', 'ne_10m_rivers_europe', 'ne_10m_rivers_lake_centerlines']
DEM = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
DEM_Z, DEM_X, DEM_Y = 7, range(70, 81), range(46, 52)
# NASA GIBS Blue Marble, web mercator, 19-45E x 34.3-43.7N (matches geo.IMG_* bbox)
BM = ('https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0'
      '&LAYERS=BlueMarble_NextGeneration&CRS=EPSG:3857&BBOX=2115070.3248,4069156.1822,5009377.085,5419133.2586'
      '&WIDTH=3200&HEIGHT=1492&FORMAT=image/jpeg&STYLES=')

def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'GrecoTurkish-map-generator'})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    open(path + '.part', 'wb').write(data)
    os.replace(path + '.part', path)
    print('got', os.path.relpath(path, DATA), len(data) // 1024, 'KB')

def main():
    for f in NE_FILES:
        get(NE.format(f), os.path.join(DATA, 'ne', f + '.geojson'))
    for x in DEM_X:
        for y in DEM_Y:
            get(DEM.format(z=DEM_Z, x=x, y=y), os.path.join(DATA, 'dem', f't_{DEM_Z}_{x}_{y}.png'))
    get(BM, os.path.join(DATA, 'img', 'bm.jpg'))
    print('data ready in', DATA)

if __name__ == '__main__':
    sys.exit(main())
