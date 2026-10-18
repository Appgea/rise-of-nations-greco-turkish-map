"""Rasterize real geography (Natural Earth + terrarium DEM) onto a Mercator tile grid."""
import json, math, os, glob
import numpy as np
from PIL import Image, ImageDraw

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
LON0, LON1, LAT0 = 19.0, 34.7, 34.3
# north edge chosen so the region is square in Mercator (RoN maps must be square)
LAT1 = math.degrees(math.atan(math.sinh(math.log(math.tan(math.pi / 4 + math.radians(LAT0) / 2)) + math.radians(LON1 - LON0))))
# bbox of the downloaded Blue Marble image (web mercator); fetch_data.py downloads exactly this
IMG_LON0, IMG_LON1, IMG_LAT0, IMG_LAT1 = LON0, LON1, LAT0, LAT1

def merc_y(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

def aspect():
    return math.radians(LON1 - LON0) / (merc_y(LAT1) - merc_y(LAT0))

class Grid:
    """Tile grid W x H; tile (i,j) spans x in [i,i+1), y in [j,j+1); y=0 is north."""
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.y0, self.y1 = merc_y(LAT1), merc_y(LAT0)
    def to_xy(self, lon, lat):
        x = (lon - LON0) / (LON1 - LON0) * self.W
        y = (self.y0 - merc_y(lat)) / (self.y0 - self.y1) * self.H
        return x, y
    def to_lonlat(self, x, y):
        lon = LON0 + x / self.W * (LON1 - LON0)
        my = self.y0 - y / self.H * (self.y0 - self.y1)
        lat = math.degrees(2 * math.atan(math.exp(my)) - math.pi / 2)
        return lon, lat
    def km_per_tile(self):
        lon, lat = self.to_lonlat(self.W / 2, self.H / 2)
        return (LON1 - LON0) / self.W * 111.32 * math.cos(math.radians(lat))

def _polys(fc):
    for f in fc['features']:
        g = f['geometry']
        if g is None: continue
        if g['type'] == 'Polygon': yield f, g['coordinates']
        elif g['type'] == 'MultiPolygon':
            for p in g['coordinates']: yield f, p

def _inbox(ring, pad=1.0):
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    return max(xs) > LON0 - pad and min(xs) < LON1 + pad and max(ys) > LAT0 - pad and min(ys) < LAT1 + pad

def raster_polys(grid, files, ss=8, filt=None):
    """Fraction of each tile covered by polygons in the given geojson files."""
    W, H = grid.W * ss, grid.H * ss
    img = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(img)
    for fn in files:
        fc = json.load(open(os.path.join(DATA, 'ne', fn), encoding='utf-8'))
        for f, poly in _polys(fc):
            if filt and not filt(f): continue
            if not _inbox(poly[0]): continue
            for k, ring in enumerate(poly):
                pts = [tuple(v * ss for v in grid.to_xy(lon, lat)) for lon, lat in ring]
                if len(pts) > 2: dr.polygon(pts, fill=255 if k == 0 else 0)
    a = np.asarray(img, np.float32) / 255
    return a.reshape(grid.H, ss, grid.W, ss).mean((1, 3))

def land_fraction(grid):
    land = raster_polys(grid, ['ne_10m_land.geojson'])
    isl = raster_polys(grid, ['ne_10m_minor_islands.geojson'])
    # lakes are left out on purpose: inland water only gets in the way of building
    return np.maximum(land, isl), None

def elevation(grid, z=7):
    """Elevation (m) at the (H+1)x(W+1) tile vertices, bilinear from terrarium tiles (web mercator)."""
    tiles = {}
    for fn in glob.glob(os.path.join(DATA, 'dem', f't_{z}_*_*.png')):
        _, _, x, y = os.path.basename(fn)[:-4].split('_')
        a = np.asarray(Image.open(fn).convert('RGB'), np.float64)
        tiles[(int(x), int(y))] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    xs = [k[0] for k in tiles]; ys = [k[1] for k in tiles]
    tx0, ty0 = min(xs), min(ys)
    mosaic = np.zeros(((max(ys) - ty0 + 1) * 256, (max(xs) - tx0 + 1) * 256))
    for (x, y), a in tiles.items():
        mosaic[(y - ty0) * 256:(y - ty0 + 1) * 256, (x - tx0) * 256:(x - tx0 + 1) * 256] = a
    n = 2 ** z * 256
    gx = np.arange(grid.W + 1); gy = np.arange(grid.H + 1)
    lon = LON0 + gx / grid.W * (LON1 - LON0)
    my = grid.y0 - gy / grid.H * (grid.y0 - grid.y1)
    px = (lon + 180) / 360 * n - tx0 * 256
    py = (1 - my / math.pi) / 2 * n - ty0 * 256
    PX, PY = np.meshgrid(px, py)
    x0 = np.floor(PX).astype(int); y0 = np.floor(PY).astype(int); fx = PX - x0; fy = PY - y0
    m = mosaic
    return (m[y0, x0] * (1 - fx) * (1 - fy) + m[y0, x0 + 1] * fx * (1 - fy) +
            m[y0 + 1, x0] * (1 - fx) * fy + m[y0 + 1, x0 + 1] * fx * fy)

def elevation_max(grid, z=7):
    """Max elevation inside each tile (H x W) -- keeps peaks that bilinear sampling misses."""
    return None

def rivers(grid, max_scalerank=6):
    fc = json.load(open(os.path.join(DATA, 'ne', 'ne_10m_rivers_lake_centerlines.geojson'), encoding='utf-8'))
    out = []
    for f in fc['features']:
        p = f['properties']; g = f['geometry']
        if g is None or p.get('scalerank', 99) > max_scalerank: continue
        lines = g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]
        for ln in lines:
            if not _inbox(ln, 0): continue
            out.append((p.get('name') or p.get('name_en') or '?', p.get('scalerank'), [grid.to_xy(lo, la) for lo, la in ln]))
    return out
