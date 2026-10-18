"""How much buildable room does Greece have? (lon 19.5-26.5, lat 35-41.3)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, build, geo
from scipy import ndimage
def run(W):
    H = round(W / geo.aspect() / 4) * 4
    T0 = build.compute_terrain(W, H); g = T0['g']
    K = lambda m: np.kron(m, np.ones((4, 4), bool))
    flags = T0['flags']; c58 = T0['c58']
    ok = ((flags & 0x12) == 0) & ~K(T0['mt']) & ~K(T0['forest']) & K(c58[..., 2] == 0)
    city = ndimage.minimum_filter(ok.astype(np.uint8), size=7, mode='constant', cval=0) > 0
    bld = ndimage.minimum_filter(ok.astype(np.uint8), size=3, mode='constant', cval=0) > 0   # farm/house size
    x0, y1 = g.to_xy(19.5, 35.0); x1, y0 = g.to_xy(26.5, 41.3)
    sl = np.s_[int(y0):int(y1), int(x0):int(x1)]
    land = ~T0['water'][sl]
    mt = K(T0['mt'])[sl] & land; fo = K(T0['forest'])[sl] & land
    print(f'W={W}: Greece land tiles {land.sum()}, mountains {mt.sum()/land.sum():.0%}, forest {fo.sum()/land.sum():.0%}, '
          f'buildable(3x3) {bld[sl].sum()/land.sum():.0%}, city spots {city[sl].sum()}  | whole map: {T0["mt"].sum()} mtn cells')
for W in map(int, sys.argv[1:]): run(W)
