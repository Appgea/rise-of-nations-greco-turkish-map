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
# the big stamps (47-72 cells) are wider than real ranges; use medium+small ones
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

def blob(cy, cx, n, ok, rng):
    """Organic patch of about n cells grown from (cy, cx) inside ok. Growth favours cells that touch the
    patch on several sides, with randomness, so patches are roundish and ragged, never boxes."""
    H, W = ok.shape
    if not (0 <= cy < H and 0 <= cx < W) or not ok[cy, cx]:
        return None
    cells = {(int(cy), int(cx))}
    while len(cells) < n:
        cand = {}
        for y, x in cells:
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (y + dy, x + dx)
                if q not in cells and 0 <= q[0] < H and 0 <= q[1] < W and ok[q]:
                    cand[q] = cand.get(q, 0) + 1
        if not cand:
            break
        ks = sorted(cand); w = np.array([cand[k] for k in ks], float) ** 2
        cells.add(ks[int(rng.choice(len(ks), p=w / w.sum()))])
    m = np.zeros_like(ok)
    for y, x in cells: m[y, x] = True
    return m

def forests(forest_idx, allowed, real_frac=0.16, max_gap=5, seed=7):
    """Forest cells: the most forested real areas, plus small groves so no land is far from wood.
    Single cells and pairs render as square tree blocks, so patches are at least 4 cells and ragged."""
    rng = np.random.default_rng(seed)
    noise = ndimage.gaussian_filter(rng.standard_normal(forest_idx.shape), 1.0)
    fi = ndimage.gaussian_filter(forest_idx, 0.7) + 0.6 * noise / noise.std() * forest_idx[allowed].std()
    thr = np.quantile(fi[allowed], 1 - real_frac)
    f = allowed & (fi >= thr)
    lab, n = ndimage.label(f)
    f &= np.bincount(lab.ravel())[lab] >= 4
    allowed = allowed.copy()
    for _ in range(800):
        dist = ndimage.distance_transform_edt(~f)
        need = allowed & (dist > max_gap)
        if not need.any(): break
        cy, cx = np.unravel_index(np.argmax(np.where(need, dist + forest_idx * 2, -1)), f.shape)
        g = blob(cy, cx, int(rng.integers(5, 8)), allowed & ~f, rng)
        if g is None or g.sum() < 4:
            allowed[cy, cx] = False; continue
        f |= g
    return f

def mask_from_recs(shape, recs):
    m = np.zeros(shape, bool)
    for pos, tid, _ in recs:
        cy, cx = divmod(pos, 256); fp = TEMPLATES[tid]
        ys, xs = fp[:, 0] + cy, fp[:, 1] + cx
        k = (ys >= 0) & (xs >= 0) & (ys < shape[0]) & (xs < shape[1])
        m[ys[k], xs[k]] = True
    return m

def start_kit(mt, recs, forest, land_ok, score, site, rng, clear_r=1.8, wood_r=(2.2, 3.0), metal_r=(2.2, 3.4)):
    """A playable start around coarse cell `site`: a clear disk (city plus farms), an organic forest
    about 8-12 tiles out and a mineable rock on another side. Returns the kit centre cell."""
    ch, cw = mt.shape
    yy, xx = np.mgrid[0:ch, 0:cw]
    # centre: the nearest cell to the site that has solid land around it
    inland = ndimage.distance_transform_edt(land_ok)
    sy, sx = site
    dsite = np.hypot(yy - sy, xx - sx)
    cand = (dsite <= 2.5) & (inland >= 2.5)
    if not cand.any(): cand = (dsite <= 2.5) & (inland >= inland[dsite <= 2.5].max())
    cy, cx = np.unravel_index(np.argmin(np.where(cand, dsite, 99)), mt.shape)
    d = np.hypot(yy - cy, xx - cx); ang = np.arctan2(yy - cy, xx - cx)
    clear = d <= clear_r
    # the scenario script spawns the starting citizens south-east of the city (+x, +y): keep that side open
    clear |= (yy > cy) & (xx > cx) & (d <= clear_r + 1.2)
    removed = [r for r in recs if (mask_from_recs(mt.shape, [r]) & clear).any()]
    recs[:] = [r for r in recs if r not in removed]
    mt[:] = mask_from_recs(mt.shape, recs)
    forest &= ~clear
    free = land_ok & ~mt & ~ndimage.binary_dilation(clear)
    # wood: unless a real forest is already close, grow one where the ring has the most open land
    wood_ang = None
    near_f = forest & (d <= wood_r[1])
    if near_f.sum() >= 5:
        wood_ang = float(np.arctan2((yy[near_f] - cy).mean(), (xx[near_f] - cx).mean()))
    else:
        ring = free & (d >= wood_r[0]) & (d <= wood_r[1]) & ~forest
        room = ndimage.uniform_filter(free.astype(float), 3)
        if ring.any():
            wy, wx = np.unravel_index(np.argmax(np.where(ring, room + rng.uniform(0, 0.05, ring.shape), -1)), ring.shape)
            g = blob(wy, wx, 7, free & ~forest & (d >= clear_r + 0.8), rng)
            if g is not None:
                forest |= g; wood_ang = float(np.arctan2(wy - cy, wx - cx))
    # metal: a rock outcrop on a side away from the wood, unless a mountain is already in reach
    if not (mt & (d <= metal_r[1])).any():
        okm = land_ok & ~mt & ~clear & ~forest
        best = None
        for tid, r1 in ((ROCK_TID, metal_r[1]), (ROCK_TID, metal_r[1] + 1.5)):
            fp = TEMPLATES[tid]
            for py, px in np.argwhere((d >= metal_r[0]) & (d <= r1)):
                hit = _fits(fp, py, px, okm)
                if hit is None: continue
                a = float(np.arctan2(py - cy, px - cx))
                away = 1.0 if wood_ang is None else abs(math.remainder(a - wood_ang, 2 * math.pi)) / math.pi
                sc = away + 0.3 * score[hit].mean() - 0.3 * d[py, px] + rng.uniform(0, 0.05)
                if best is None or sc > best[0]: best = (sc, tid, py, px, hit)
            if best: break
        if best:
            _, tid, py, px, (ys, xs) = best
            _place(mt, recs, tid, py, px, ys, xs)
        else:
            # no room for a new rock (narrow islands like Crete): keep the real mountains instead
            keep = [r for r in removed if not mask_from_recs(mt.shape, [r])[cy, cx]]
            recs.extend(keep); mt[:] = mask_from_recs(mt.shape, recs)
    return int(cy), int(cx)

def wood_near_sites(forest, allowed, sites, rng, rmax=3.2, n=5):
    """Every big town gets at least a small wood within ~13 tiles."""
    ch, cw = forest.shape
    yy, xx = np.mgrid[0:ch, 0:cw]
    for sy, sx in sites:
        d = np.hypot(yy - sy, xx - sx)
        if (forest & (d <= rmax)).sum() >= 4: continue
        ring = allowed & ~forest & (d >= 2.0) & (d <= rmax)
        if not ring.any(): continue
        wy, wx = np.argwhere(ring)[int(rng.integers(ring.sum()))]
        g = blob(wy, wx, n, allowed & ~forest & (d >= 1.6), rng)
        if g is not None: forest |= g
    return forest

# (source file, exact Natural Earth name) -- one source per river to avoid doubled lines
RIVERS = {
    'ne_10m_rivers_europe.geojson': {'Maritsa', 'Sakarya', 'Gediz'},
    'ne_10m_rivers_lake_centerlines.geojson': {'Haliacmon', 'Kiz?lirmak', 'Byk Menderes', 'Strymnas', 'Danube'},
}

def ascii_name(s):
    import unicodedata
    s = (s or '').replace('\u0131', 'i').replace('\u0130', 'I')
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if ord(c) < 128)

# rivers missing from Natural Earth, traced by hand (lon, lat), source -> mouth
HAND_RIVERS = {
    'Axios': [(21.10, 42.02), (21.43, 42.00), (21.62, 41.86), (21.78, 41.72), (22.00, 41.55), (22.24, 41.41),
              (22.52, 41.15), (22.55, 40.99), (22.65, 40.78), (22.75, 40.58)],
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
