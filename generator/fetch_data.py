"""Download the open geodata the generator needs into generator/data (about 30 MB)."""
import math, os, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
import geo

DATA = geo.DATA
NE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson'
NE_FILES = ['ne_10m_land', 'ne_10m_minor_islands', 'ne_10m_lakes', 'ne_10m_rivers_europe', 'ne_10m_rivers_lake_centerlines']
DEM = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
DEM_Z = 7
# NASA GIBS Blue Marble in web mercator, covering geo.IMG_* (the map extent)
BM = ('https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0'
      '&LAYERS=BlueMarble_NextGeneration&CRS=EPSG:3857&BBOX={:.1f},{:.1f},{:.1f},{:.1f}'
      '&WIDTH=3200&HEIGHT={}&FORMAT=image/jpeg&STYLES=')

def tile_xy(lon, lat, z):
    n = 2 ** z
    return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)

def merc(lon, lat):
    R = 6378137.0
    return R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

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
    x0, y0 = tile_xy(geo.LON0 - 0.5, geo.LAT1 + 0.5, DEM_Z); x1, y1 = tile_xy(geo.LON1 + 0.5, geo.LAT0 - 0.5, DEM_Z)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            get(DEM.format(z=DEM_Z, x=x, y=y), os.path.join(DATA, 'dem', f't_{DEM_Z}_{x}_{y}.png'))
    (mx0, my0), (mx1, my1) = merc(geo.IMG_LON0, geo.IMG_LAT0), merc(geo.IMG_LON1, geo.IMG_LAT1)
    url = BM.format(mx0, my0, mx1, my1, round(3200 * (my1 - my0) / (mx1 - mx0)))
    bm, tag = os.path.join(DATA, 'img', 'bm.jpg'), os.path.join(DATA, 'img', 'bm.url')
    if not os.path.exists(tag) or open(tag).read() != url:      # extent changed: fetch the image again
        if os.path.exists(bm): os.remove(bm)
        get(url, bm); open(tag, 'w').write(url)
    print('data ready in', DATA)

if __name__ == '__main__':
    sys.exit(main())
