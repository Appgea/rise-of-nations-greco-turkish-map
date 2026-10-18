"""Map features built from real data: mountain stamps, rock outcrops, forests, rivers."""
import json, math, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import geo

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = {int(k): np.array(v) for k, v in json.load(open(os.path.join(HERE, 'mtn_templates.json'))).items()}
ROCK_TID = 15            # smallest stamp (8 cells), used for metal outcrops
BIG_FIRST = sorted([t for t in TEMPLATES if t != ROCK_TID], key=lambda t: -len(TEMPLATES[t]))
# at ~22 km per coarse cell the big stamps (47-72 cells) are wider than real ranges; use medium+small ones
STAMP_ORDER = [t for t in BIG_FIRST if len(TEMPLATES[t]) <= 30] + [ROCK_TID]

def cell_land(water):
    H, W = water.shape
    return water.reshape(H // 4, 4, W // 4, 4).sum((1, 3)) == 0

def relief(elev_v, H, W):
    """Per coarse cell: peak elevation and height above the surrounding lowland."""
    ch, cw = H // 4, W // 4
    e = np.clip(elev_v[:H, :W], 0, None).reshape(ch, 4, cw, 4)
    emax = e.max((1, 3)); emean = e.mean((1, 3))
    base = ndimage.percentile_filter(emean, 15, size=9)
    return emax, emax - base

def _fits(fp, cy, cx, ok):
    ys = fp[:, 0] + cy; xs = fp[:, 1] + cx
    if ys.min() < 0 or xs.min() < 0 or ys.max() >= ok.shape[0] or xs.max() >= ok.shape[1]:
        return None
    if not ok[ys, xs].all():
        return None
    return ys, xs

def stamp_mountains(score, allowed, thresholds, cap_cells):
    """Greedy tiling of high-relief areas with RoN's fixed mountain footprints.
    Returns (mask, records) where records are (cy*256+cx, template_id, cells)."""
    used = np.zeros_like(allowed)
    recs = []
    for tid in STAMP_ORDER:
        fp = TEMPLATES[tid]
        thr = thresholds(len(fp))
        cy_, cx_ = np.nonzero(allowed & (score > thr))
        order = np.argsort(-score[cy_, cx_])
        for k in order:
            if used.sum() >= cap_cells: return used, recs
            cy, cx = cy_[k], cx_[k]
            hit = _fits(fp, cy, cx, allowed & ~used)
            if hit is None: continue
            ys, xs = hit
            if score[ys, xs].mean() < thr: continue
            # keep a 1-cell gap between separate stamps most of the time so passes stay open
            y0, y1 = max(ys.min() - 1, 0), min(ys.max() + 2, used.shape[0])
            x0, x1 = max(xs.min() - 1, 0), min(xs.max() + 2, used.shape[1])
            win = np.zeros((y1 - y0, x1 - x0), bool); win[ys - y0, xs - x0] = True
            ring = ndimage.binary_dilation(win, np.ones((3, 3), bool)) & ~win
            if (used[y0:y1, x0:x1] & ring).sum() > 3: continue
            used[ys, xs] = True
            recs.append((int(cy) * 256 + int(cx), tid, len(fp)))
    return used, recs

def add_rocks(mountains, recs, allowed, score, max_gap=5):
    """Sprinkle small rock outcrops so every land cell has metal within max_gap cells."""
    fp = TEMPLATES[ROCK_TID]
    for _ in range(400):
        dist = ndimage.distance_transform_edt(~mountains)
        need = allowed & (dist > max_gap)
        if not need.any(): break
        # best spot = highest relief cell among the worst-served area
        far = need & (dist >= dist[need].max() - 1)
        cand = np.argwhere(ndimage.binary_dilation(far, np.ones((5, 5), bool)) & allowed & ~mountains)
        best = None
        for cy, cx in cand[np.argsort(-score[cand[:, 0], cand[:, 1]])][:60]:
            hit = _fits(fp, cy, cx, allowed & ~ndimage.binary_dilation(mountains, np.ones((3, 3), bool)))
            if hit is not None: best = (cy, cx, hit); break
        if best is None:
            allowed = allowed & ~far
            continue
        cy, cx, (ys, xs) = best
        mountains[ys, xs] = True
        recs.append((int(cy) * 256 + int(cx), ROCK_TID, len(fp)))
    return mountains, recs

def forests(forest_idx, allowed, real_frac=0.16, max_gap=5):
    """Forest cells: the most forested real areas, plus small groves so no land is far from wood."""
    vals = forest_idx[allowed]
    thr = np.quantile(vals, 1 - real_frac)
    f = allowed & (forest_idx >= thr)
    # remove speckle, keep clumps
    f = ndimage.binary_opening(f, np.ones((2, 2), bool)) | (f & ndimage.binary_erosion(f, np.ones((1, 3), bool)))
    for _ in range(600):
        dist = ndimage.distance_transform_edt(~f)
        need = allowed & (dist > max_gap)
        if not need.any(): break
        lab, n = ndimage.label(need)
        # one grove per worst region per pass
        cy, cx = np.unravel_index(np.argmax(np.where(need, dist + forest_idx * 2, -1)), f.shape)
        grove = np.zeros_like(f)
        grove[max(cy - 1, 0):cy + 2, max(cx - 1, 0):cx + 1] = True    # one 3x2 grove instead of scattered specks
        f |= grove & allowed
        if not (grove & allowed).any(): allowed = allowed.copy(); allowed[cy, cx] = False
    return f

# (source file, exact Natural Earth name) -- one source per river to avoid doubled lines
RIVERS = {
    'ne_10m_rivers_europe.geojson': {'Maritsa', 'Mesta', 'Acheloos', 'Aoos', 'Sakarya',
                                     'Yesilirmak', 'Gediz', 'Seyhan', 'Coruh'},
    'ne_10m_rivers_lake_centerlines.geojson': {'Haliacmon', 'Drin', 'Morava', 'Ceyhan', 'Euphrates', 'Firat',
                                               'Al Furat', 'Tigris', 'Dicle',
                                               'Kiz?lirmak', 'Byk Menderes', 'Strymnas'},
}

def ascii_name(s):
    import unicodedata
    s = (s or '').replace('\u0131', 'i').replace('\u0130', 'I')
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if ord(c) < 128)

# rivers missing from Natural Earth, traced by hand (lon, lat), source -> mouth
HAND_RIVERS = {
    'Axios': [(21.10, 42.02), (21.43, 42.00), (21.62, 41.86), (21.78, 41.72), (22.00, 41.55), (22.24, 41.41),
              (22.52, 41.15), (22.55, 40.99), (22.65, 40.78), (22.75, 40.58)],
    'Pineios': [(21.30, 39.85), (21.63, 39.70), (21.77, 39.55), (22.10, 39.55), (22.42, 39.64), (22.60, 39.87),
                (22.74, 39.93)],
}

def load_rivers(grid):
    import json as _j
    lines = [(nm, [grid.to_xy(lo, la) for lo, la in pts]) for nm, pts in HAND_RIVERS.items()]
    for fn, wanted in RIVERS.items():
        fc = _j.load(open(os.path.join(geo.DATA, 'ne', fn), encoding='utf-8'))
        for f in fc['features']:
            g = f['geometry']; nm = f['properties'].get('name')
            if g is None or ascii_name(nm) not in wanted: continue
            parts = g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]
            for ln in parts:
                pts = [grid.to_xy(lo, la) for lo, la in ln]
                lines.append((nm, pts))
    return lines

def river_layers(grid, water, mountains_forbid=None, width=1, min_len_tiles=14):
    """Rasterise rivers to tiles (flag 0x02) and produce RoN control polylines in coarse units."""
    H, W = water.shape
    lines = load_rivers(grid)
    img = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(img)
    polylines = []
    for nm, pts in lines:
        # split into runs that stay on the map and on land
        run = []
        runs = []
        for x, y in pts:
            inside = 0 <= x < W and 0 <= y < H and not water[int(y), int(x)]
            if inside: run.append((x, y))
            else:
                if len(run) > 1: runs.append(run)
                run = []
        if len(run) > 1: runs.append(run)
        for r in runs:
            L = sum(math.dist(r[i], r[i + 1]) for i in range(len(r) - 1))
            if L < min_len_tiles: continue
            # resample every ~6 tiles for RoN's smooth river curve
            n = max(2, int(L / 6) + 1)
            cum = np.concatenate([[0], np.cumsum([math.dist(r[i], r[i + 1]) for i in range(len(r) - 1)])])
            xs = np.interp(np.linspace(0, L, n), cum, [p[0] for p in r])
            ys = np.interp(np.linspace(0, L, n), cum, [p[1] for p in r])
            dr.line(list(zip(xs, ys)), fill=255, width=width)
            polylines.append((nm, [(int(round(x / 4 - 0.5)), int(round(y / 4 - 0.5))) for x, y in zip(xs, ys)]))
    river = (np.asarray(img) > 0) & ~water
    # de-duplicate consecutive identical control points
    out = []
    for nm, p in polylines:
        q = [p[0]] + [b for a, b in zip(p, p[1:]) if b != a]
        if len(q) >= 2: out.append((nm, q))
    return river, out

def _place(used, recs, tid, cy, cx, ys, xs):
    used[ys, xs] = True
    recs.append((int(cy) * 256 + int(cx), tid, len(TEMPLATES[tid])))

def _ring_hits(used, ys, xs):
    y0, y1 = max(ys.min() - 1, 0), min(ys.max() + 2, used.shape[0])
    x0, x1 = max(xs.min() - 1, 0), min(xs.max() + 2, used.shape[1])
    win = np.zeros((y1 - y0, x1 - x0), bool); win[ys - y0, xs - x0] = True
    ring = ndimage.binary_dilation(win, np.ones((3, 3), bool)) & ~win
    return int((used[y0:y1, x0:x1] & ring).sum())

def stamp_ranges(score, allowed, cap_cells, massif_thr=2.4, ridge_thr=1.85, ridge_mean=1.5, max_touch=4):
    """Massifs first (medium stamps on the highest ground), then chains of small stamps along ridges."""
    used = np.zeros_like(allowed); recs = []
    medium = [t for t in STAMP_ORDER if t != ROCK_TID]
    for tid in medium:
        fp = TEMPLATES[tid]
        cy_, cx_ = np.nonzero(allowed & (score > massif_thr))
        for k in np.argsort(-score[cy_, cx_]):
            cy, cx = cy_[k], cx_[k]
            hit = _fits(fp, cy, cx, allowed & ~used)
            if hit is None: continue
            ys, xs = hit
            if score[ys, xs].mean() < massif_thr or _ring_hits(used, ys, xs) > 0: continue
            _place(used, recs, tid, cy, cx, ys, xs)
    small = [ROCK_TID, 14, 12, 10]
    cy_, cx_ = np.nonzero(allowed & (score > ridge_thr))
    for k in np.argsort(-score[cy_, cx_]):
        if used.sum() >= cap_cells: break
        cy, cx = cy_[k], cx_[k]
        if used[cy, cx]: continue
        for tid in small:
            hit = _fits(TEMPLATES[tid], cy, cx, allowed & ~used)
            if hit is None: continue
            ys, xs = hit
            if score[ys, xs].mean() < ridge_mean or _ring_hits(used, ys, xs) > max_touch: continue
            _place(used, recs, tid, cy, cx, ys, xs)
            break
    return used, recs

def rocks_near_sites(mountains, recs, allowed, score, sites, rmin=2, rmax=3):
    """Make sure every town site (coarse cell) has a mineable mountain/rock rmin..rmax cells away,
    so a city founded there can put a mine just outside its centre."""
    fp = TEMPLATES[ROCK_TID]
    ch, cw = mountains.shape
    added = 0
    for sy, sx in sites:
        y0, y1 = max(sy - rmax - 1, 0), min(sy + rmax + 2, ch); x0, x1 = max(sx - rmax - 1, 0), min(sx + rmax + 2, cw)
        if mountains[y0:y1, x0:x1].any():
            continue
        keep_off = np.zeros_like(mountains)
        keep_off[max(sy - rmin + 1, 0):sy + rmin, max(sx - rmin + 1, 0):sx + rmin] = True   # don't sit on the town
        ok = allowed & ~keep_off & ~mountains
        best = None
        for cy in range(y0, y1):
            for cx in range(x0, x1):
                hit = _fits(fp, cy, cx, ok)
                if hit is None: continue
                ys, xs = hit
                d = max(abs(ys - sy).min(), abs(xs - sx).min())
                if not (rmin <= max(abs(cy - sy), abs(cx - sx)) <= rmax + 1): continue
                if keep_off[ys, xs].any(): continue
                sc = score[ys, xs].mean()
                if best is None or sc > best[0]: best = (sc, cy, cx, hit)
        if best:
            _, cy, cx, (ys, xs) = best
            _place(mountains, recs, ROCK_TID, cy, cx, ys, xs); added += 1
    return mountains, recs, added
