"""Playability metrics: city room, wood and metal access per town site."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, build, geo, cities
from scipy import ndimage
W = int(sys.argv[1]) if len(sys.argv) > 1 else 512
H = round(W / geo.aspect() / 4) * 4
T0 = build.compute_terrain(W, H)
T = build.pad_square(T0)
g = geo.Grid(W, H)
flags = T['flags']; c58 = T['c58']; HH, WW = flags.shape
gx0 = int(g.to_xy(26.5, 40)[0])
K = lambda m: np.kron(m, np.ones((4, 4), bool))
ok = ((flags & 0x12) == 0) & ~K(T['mt']) & ~K(T['forest']) & K(c58[..., 2] == 0)
f = ndimage.minimum_filter(ok.astype(np.uint8), size=7, mode='constant', cval=0) > 0
land = ~T0['water']
print(f'map {W}x{H} -> {WW}x{HH}, {g.km_per_tile():.2f} km/tile; land tiles {int(land.sum())}')
print(f'city spots (7x7) west/east: {int(f[:, :gx0].sum())} / {int(f[:, gx0:].sum())}')
print(f'mountain cells {int(T["mt"].sum())} ({T["mt"].sum() / build.features.cell_land(T0["water"]).sum():.0%} of land cells), stamps {len(T["recs"])}, forest cells {int(T["forest"].sum())}, river tiles {int(T["river"].sum())}')
mt = T0['mt']; fo = T0['forest']
dm = ndimage.distance_transform_edt(~mt); dfo = ndimage.distance_transform_edt(~fo)
ys, xs = np.nonzero(f)
rows = []
for la, lo, gr, tr in cities.CITIES:
    x, y = g.to_xy(lo, la)
    if 0 <= x < W and 0 <= y < H and not T0['water'][int(y), int(x)]:
        sy, sx = int(y // 4), int(x // 4)
        dspot = np.sqrt((xs - x) ** 2 + (ys - (y + T['yoff'])) ** 2).min()
        rows.append((tr, dm[sy, sx], dfo[sy, sx], dspot))
print(f'town sites on land: {len(rows)}; metal within 3 cells: {np.mean([r[1] <= 3 for r in rows]):.0%}, '
      f'wood within 3 cells: {np.mean([r[2] <= 3 for r in rows]):.0%}, city spot within 6 tiles: {np.mean([r[3] <= 6 for r in rows]):.0%}')
for key in ('Atina', 'Selanik', 'Ballibadra', 'Izmir', 'Istanbul', 'Bursa', 'Ankara', 'Trabzon', 'Lefkosa', 'Kandiye'):
    r = next((r for r in rows if r[0] == key), None)
    if r: print(f'  {key:10s} metal {r[1]:.1f} cells, wood {r[2]:.1f} cells, nearest city spot {r[3]:.1f} tiles')
