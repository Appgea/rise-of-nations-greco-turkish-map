"""Turn real geography into RoN map layers (tile flags, vertex heights, coarse cells)."""
import os
import numpy as np
from PIL import Image
from scipy import ndimage
import geo

WATER, COAST, RIVER = 0x10, 0x20, 0x02

# narrow straits that the 0.5 land threshold closes; forced open as water (lon, lat polylines)
STRAITS = {
    'Bosphorus': [(29.12, 41.23), (29.07, 41.15), (29.05, 41.10), (29.01, 41.03), (28.99, 40.99)],
    'Dardanelles': [(26.18, 40.05), (26.36, 40.13), (26.40, 40.20), (26.47, 40.25), (26.68, 40.40), (26.75, 40.47)],
    'Rio': [(21.66, 38.29), (21.79, 38.32), (21.92, 38.35)],      # mouth of the Gulf of Corinth
}

# Greece is narrow and rugged; its land grows outward so there is room to build (lon/lat box, tiles)
GROW_BOX = (19.0, 28.4, 34.3, 41.9)
GROW_TILES = 2

def grow_greece(grid, water, tiles=GROW_TILES, box=GROW_BOX):
    """Widen Greek and Balkan coasts and islands by up to `tiles` and fill narrow inlets, without
    merging separate landmasses (a gap of 2+ tiles always stays) and without touching Anatolia,
    lakes or open-sea channels to Asia."""
    H, W = water.shape
    lon0, lon1, lat0, lat1 = box
    x0, _ = grid.to_xy(lon0, lat0); x1, _ = grid.to_xy(lon1, lat0)
    _, y1 = grid.to_xy(lon0, lat0); _, y0 = grid.to_xy(lon0, lat1)
    inbox = np.zeros_like(water); inbox[max(int(y0), 0):int(y1) + 1, max(int(x0), 0):int(x1) + 1] = True
    lab, n = ndimage.label(~water, np.ones((3, 3), bool))
    ax, ay = grid.to_xy(32.86, 39.93)
    asia = lab == lab[int(ay), int(ax)]
    wl, _ = ndimage.label(water)
    sea = wl == np.bincount(wl.ravel())[1:].argmax() + 1          # the open sea, not lakes
    near_asia = ndimage.distance_transform_edt(~asia) <= tiles + 3
    big = n + 1
    for _ in range(tiles):
        grow = np.where(asia, 0, lab)
        hi = ndimage.maximum_filter(grow, size=5)
        lo = ndimage.minimum_filter(np.where(grow > 0, grow, big), size=5)
        touch = ndimage.maximum_filter(grow, size=3) > 0
        add = water & sea & inbox & touch & (hi > 0) & (hi == lo) & ~near_asia
        lab = np.where(add, hi, lab); water = water & ~add
    return water

def fill_bays(grid, water, size=4, greek_size=5, box=GROW_BOX, keep=60):
    """Less water: fill narrow inlets and lagoons, and turn small water bodies cut off from the sea into
    land (no lakes). A fill that would cut a gulf of `keep`+ tiles off the sea is undone, so Corinth,
    Izmir, Izmit, Volos... stay. Separate landmasses never merge."""
    lon0, lon1, lat0, lat1 = box
    x1, _ = grid.to_xy(lon1, lat0); _, y0 = grid.to_xy(lon0, lat1); _, y1 = grid.to_xy(lon0, lat0)
    inbox = np.zeros_like(water); inbox[max(int(y0), 0):int(y1) + 1, :int(x1) + 1] = True
    land = ~water
    lab, n = ndimage.label(land); big = n + 1        # 4-connected: a diagonal touch across a strait is no bridge
    hi = ndimage.maximum_filter(lab, size=5)
    lo = ndimage.minimum_filter(np.where(lab > 0, lab, big), size=5)
    closed = ndimage.binary_closing(land, np.ones((size, size), bool)) |         (ndimage.binary_closing(land, np.ones((greek_size, greek_size), bool)) & inbox)
    cand = closed & water & (hi > 0) & (hi == lo)
    regions, _ = ndimage.label(cand, np.ones((3, 3), bool))
    def seas(w):
        wl, _ = ndimage.label(w); sz = np.bincount(wl.ravel()); sz[0] = 0
        return wl, sz
    wl0, sz0 = seas(water)
    for _ in range(12):
        wl, sz = seas(water & ~cand)
        sea_ids = np.nonzero(sz >= 3000)[0]
        cut = np.isin(wl, np.nonzero((sz >= keep) & (sz < 3000))[0])
        # a cut-off gulf that was part of the open sea before: reopen the fills that border it
        was_sea = np.isin(wl0, np.nonzero(sz0 >= 3000)[0])
        cut &= was_sea
        if not cut.any(): break
        undo = np.unique(regions[ndimage.binary_dilation(cut, np.ones((3, 3), bool)) & cand])
        undo = undo[undo > 0]
        if not len(undo): break
        cand &= ~np.isin(regions, undo)
    water = water & ~cand
    wl, sz = seas(water)
    # keep the seas and the gulfs hanging off them; every small or landlocked body becomes land
    return np.isin(wl, np.nonzero(sz >= keep)[0]) & np.isin(wl, np.unique(wl[np.isin(wl0, np.nonzero(sz0 >= 3000)[0])]))

def chebyshev_dist(mask, maxd):
    """Chebyshev distance (in tiles) from each cell to the nearest True cell, capped at maxd+1."""
    dist = np.where(mask, 0, maxd + 1)
    cur = mask.copy()
    for d in range(1, maxd + 1):
        cur = ndimage.binary_dilation(cur, np.ones((3, 3), bool))
        dist[cur & (dist > maxd)] = d
    return dist

def carve(grid, water, lines, width=1):
    from PIL import ImageDraw
    img = Image.new('L', (grid.W, grid.H), 0); dr = ImageDraw.Draw(img)
    for pts in lines:
        dr.line([grid.to_xy(lo, la) for lo, la in pts], fill=255, width=width)
    return water | (np.asarray(img) > 0)

def fatten_islands(water, big=900, steps=((900, 1),), min_size=12):
    """Grow small islands by 1-2 tiles so they are playable, without merging them with other land."""
    land = ~water
    lab, n = ndimage.label(land, np.ones((3, 3), bool))
    sizes = np.bincount(lab.ravel())
    grown = land.copy()
    for limit, k in steps:
        small = np.isin(lab, np.nonzero((sizes < limit) & (sizes >= min_size) & (np.arange(len(sizes)) > 0))[0])
        if not small.any(): continue
        # tiles reachable from a small island within k steps, but at least 3 tiles away from any other land
        other = land & ~small
        far_from_other = ndimage.distance_transform_cdt(~other, metric='chessboard') > k + 3
        add = ndimage.binary_dilation(small, np.ones((3, 3), bool), iterations=k) & far_from_other
        grown |= add
    return ~grown

def tile_layers(grid, land_frac, land_thr=0.5):
    # land_thr < 0.5 widens thin peninsulas/islands slightly (more room to build on the Greek coast)
    water = land_frac < land_thr
    water = grow_greece(grid, water)
    water = carve(grid, water, STRAITS.values(), width=2)
    water = fill_bays(grid, water)
    water = fatten_islands(water)
    water = carve(grid, water, STRAITS.values(), width=2)
    wl, _ = ndimage.label(water); sz = np.bincount(wl.ravel()); sz[0] = 0
    water = np.isin(wl, np.nonzero(sz >= 100)[0])                # no ponds left behind by the carving
    # drop 1-tile specks of land/water that RoN renders badly
    lab, n = ndimage.label(~water)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    for i, s in enumerate(sizes, 1):
        if s < 2: water[lab == i] = True
    lab, n = ndimage.label(water)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    for i, s in enumerate(sizes, 1):
        if s < 3: water[lab == i] = False
    flags = np.zeros(water.shape, np.uint16)
    flags[water] |= WATER
    dland = chebyshev_dist(~water, 3)
    flags[water & (dland >= 1) & (dland <= 3)] |= COAST
    return water, flags

def vertex_heights(water, elev_v, river=None, mountains=None, smooth=4.0, scale=450, ramp=25):
    """Heights at (H+1)x(W+1) vertices in RoN units. Real relief is smoothed and compressed so slopes match
    the stock maps (cities and buildings need gentle ground); impassable mountain cells get a raised bump."""
    H, W = water.shape
    wv = np.zeros((H + 1, W + 1)); cnt = np.zeros((H + 1, W + 1))
    for dy in (0, 1):
        for dx in (0, 1):
            wv[dy:dy + H, dx:dx + W] += water; cnt[dy:dy + H, dx:dx + W] += 1
    wfrac = wv / cnt
    e = elev_v
    es = ndimage.gaussian_filter(np.clip(e, 0, None), smooth)
    land_h = 10 + scale * (es / 3000) ** 0.75
    if mountains is not None:
        mt_v = np.zeros((H + 1, W + 1)); mt_v[:H, :W] = np.kron(mountains, np.ones((4, 4)))
        land_h += 380 * ndimage.gaussian_filter(mt_v, 1.5)
    # land comes down to and just under the waterline over ~3 tiles, like the stock maps: the engine
    # draws a smooth sand beach there instead of a cliff with a cell-shaped edge
    dist_w = ndimage.distance_transform_edt(wfrac < 0.5)
    beach = np.where(dist_w <= 4, -45 + 15 * dist_w, 15 + 8 * (dist_w - 4))
    land_h = np.minimum(land_h, beach)
    water_h = np.clip(-45 + np.clip(e, None, 0) * 0.2, -273, -30)
    # lakes: real surface is high, so give them a shallow bowl instead
    lake_like = (e > 0) & (wfrac >= 0.5)
    water_h = np.where(lake_like, -40 - 25 * np.clip(ndimage.distance_transform_edt(wfrac >= 0.5) - 1, 0, 6), water_h)
    h = np.where(wfrac >= 0.5, water_h, land_h)
    h = np.where((wfrac > 0) & (wfrac < 0.5), np.minimum(h, -25), h)
    if river is not None:
        # carve river beds below the waterline like the stock maps (bed ~ -15, banks ramp up)
        rv = np.zeros((H + 1, W + 1))
        for dy in (0, 1):
            for dx in (0, 1):
                rv[dy:dy + H, dx:dx + W] += river
        rv /= cnt
        bank = ndimage.distance_transform_edt(rv == 0)
        h = np.where(wfrac < 0.5, np.minimum(h, 4 + ramp * (bank - 1).clip(0)), h)
        h = np.where((rv >= 0.75) & (wfrac < 0.5), -40, np.where((rv > 0) & (wfrac < 0.5), np.minimum(h, -14), h))
    return h.astype(np.float32)

def mountain_cells(elev_v, water, frac_cap=0.10):
    """Coarse (4x4 tile) cells that become impassable RoN mountains, picked from real relief."""
    H, W = water.shape; ch, cw = H // 4, W // 4
    e = elev_v[:H, :W].reshape(ch, 4, cw, 4)
    emax = e.max((1, 3)); emean = e.mean((1, 3))
    bg = ndimage.gaussian_filter(emean, 3)
    prom = emax - bg
    cwater = water.reshape(ch, 4, cw, 4).mean((1, 3))
    ok = cwater == 0
    # keep 1 cell away from shores so coasts stay usable
    ok &= ~ndimage.binary_dilation(cwater > 0, np.ones((3, 3), bool))
    score = prom + 0.25 * emax
    cand = ok & (((emax > 1300) & (prom > 420)) | (emax > 2900))
    # cap total coverage to keep the map playable
    land_cells = (cwater < 1).sum()
    if cand.sum() > frac_cap * land_cells:
        thr = np.sort(score[cand])[::-1][int(frac_cap * land_cells)]
        cand &= score > thr
    # remove single isolated cells (look like noise), keep clumps
    lab, n = ndimage.label(cand)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    for i, s in enumerate(sizes, 1):
        if s < 2: cand[lab == i] = False
    return cand, emax

def vegetation(grid, path=None):
    """Per-tile greenness and darkness from NASA Blue Marble (web mercator, same bbox as the grid)."""
    path = path or os.path.join(geo.DATA, 'img', 'bm.jpg')
    im = Image.open(path).convert('RGB')
    iw, ih = im.size
    fx0 = (geo.LON0 - geo.IMG_LON0) / (geo.IMG_LON1 - geo.IMG_LON0)
    fx1 = (geo.LON1 - geo.IMG_LON0) / (geo.IMG_LON1 - geo.IMG_LON0)
    my0, my1 = geo.merc_y(geo.IMG_LAT1), geo.merc_y(geo.IMG_LAT0)
    fy0 = (my0 - geo.merc_y(geo.LAT1)) / (my0 - my1); fy1 = (my0 - geo.merc_y(geo.LAT0)) / (my0 - my1)
    im = im.crop((int(fx0 * iw), int(fy0 * ih), int(round(fx1 * iw)), int(round(fy1 * ih))))
    im = im.resize((grid.W * 4, grid.H * 4), Image.BILINEAR)
    a = np.asarray(im, np.float32).reshape(grid.H, 4, grid.W, 4, 3).mean((1, 3))
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    bright = (r + g + b) / 3
    green = (g - r) / (g + r + 1)          # >0 vegetated, <0 dry/brown
    return green, bright

def textures(green, water):
    """RoN base textures per coarse cell: 0 grass, 1 grass_dirt, 2 dirt_grass, 3 dirt."""
    H, W = water.shape; ch, cw = H // 4, W // 4
    gc = green.reshape(ch, 4, cw, 4).mean((1, 3))
    gc = ndimage.gaussian_filter(gc, 0.8)
    t = np.full((ch, cw), 3, np.uint8)
    t[gc > -0.14] = 2
    t[gc > -0.08] = 1
    t[gc > -0.03] = 0
    return t

def coarse_layers(flags, mountains, tex):
    """Coarse cell layers: 0x58 (4 bytes/cell) and 0x63 (u16/cell), from learned stock-map rules."""
    H, W = flags.shape; ch, cw = H // 4, W // 4
    blk = flags.reshape(ch, 4, cw, 4).transpose(0, 2, 1, 3).reshape(ch, cw, 16)
    nw = ((blk & WATER) > 0).sum(-1); nc = ((blk & COAST) > 0).sum(-1)
    cls = np.where(nw == 0, 0, np.where(nw == 16, 2, 1))
    k3 = np.ones((3, 3), bool)
    landnb = ndimage.binary_dilation(nw < 16, k3)
    waternb = ndimage.binary_dilation(nw > 0, k3)
    coastnb = ndimage.binary_dilation(nc > 0, k3)
    b0 = np.zeros((ch, cw), np.uint8); b2 = np.zeros((ch, cw), np.uint8)
    v63 = np.zeros((ch, cw), np.uint16)
    land = cls == 0
    shore_land = land & waternb
    b2[cls == 1] = 1
    b2[(cls == 2) & coastnb] = 1
    b2[(cls == 2) & ~coastnb] = 2
    v63[land & ~waternb] = 0x0
    v63[shore_land] = 0x8009
    v63[cls == 1] = 0x308d
    v63[(cls == 2) & coastnb] = 0x3089
    v63[(cls == 2) & ~coastnb] = 0x3009
    b0[shore_land] = 0x08
    b0[cls == 1] = 0x80
    v63[mountains] |= 0x2
    c58 = np.stack([b0, np.zeros_like(b0), b2, tex], -1).astype(np.uint8)
    return c58, v63

def legal_textures(tex, water_cells, shore, L=0.9):
    """The 4 base textures form a cycle (0-1-2-3-0). Every stock map keeps touching cells (8-neighbours)
    from being opposite on it (0/2, 1/3); breaking that crashes TileSet::convert_land_tex_to_linear or
    draws hard seams. Build a dryness field whose 8-neighbours differ by at most L < 1, rising to 3.5
    on the shore ring, and cut it into levels: neighbouring cells then differ by at most one step."""
    phi = np.where(water_cells, 9.0, tex.astype(float) + 0.5)
    for _ in range(64):                       # largest L-Lipschitz field below the real ground colour
        new = np.minimum(phi, ndimage.minimum_filter(phi, 3) + L)
        if np.array_equal(new, phi): break
        phi = new
    d = ndimage.distance_transform_cdt(~shore, metric='chessboard')
    phi = np.maximum(phi, 3.5 - L * d)
    t = np.clip(np.floor(phi), 0, 3).astype(np.uint8)
    t[shore] = 3; t[water_cells] = 0
    has = [ndimage.maximum_filter((t == u).astype(np.uint8), 3) > 0 for u in range(4)]
    left = sum(int(((t == (u + 2) % 4) & has[u]).sum()) for u in range(4))
    assert left == 0, f'{left} texture conflicts left'
    return t

def coarse_layers_full(flags, mountains, forest, river, tex):
    """Coarse layers with every feature bit: 0x58 (b0 flags, b1, b2 land/coast/water class, b3 texture)
    and 0x63 (u16 bitfield) -- rules learned from the stock maps."""
    H, W = flags.shape; ch, cw = H // 4, W // 4
    water = (flags & WATER) > 0
    blk = flags.reshape(ch, 4, cw, 4).transpose(0, 2, 1, 3).reshape(ch, cw, 16)
    nw = ((blk & WATER) > 0).sum(-1); nc = ((blk & COAST) > 0).sum(-1)
    cls = np.where(nw == 0, 0, np.where(nw == 16, 2, 1))
    k3 = np.ones((3, 3), bool)
    coastnb = ndimage.binary_dilation(nc > 0, k3)
    dwater = ndimage.distance_transform_cdt(~water, metric='chessboard') if water.any() else np.full(water.shape, 99)
    dcell = dwater.reshape(ch, 4, cw, 4).min((1, 3))
    rcell = river.reshape(ch, 4, cw, 4).any((1, 3))
    land = cls == 0
    b0 = np.zeros((ch, cw), np.uint8); b2 = np.zeros((ch, cw), np.uint8); v = np.zeros((ch, cw), np.uint16)
    # every cell with water in it is coast (class 1), as in the stock maps. Treating mostly-land cells as
    # land left a checkerboard of sand and grass diamonds along the shore.
    b2[cls == 1] = 1
    b2[(cls == 2) & coastnb] = 1
    b2[(cls == 2) & ~coastnb] = 2
    # stock maps also mark the next land cell as beach (0x8009 / b0 0x08, unbuildable); here it stays
    # plain near-shore land (0x20) so the coast keeps room for port cities
    v[land & (dcell <= 7)] = 0x20
    v[cls == 1] = 0x308d
    v[(cls == 2) & coastnb] = 0x3089
    v[(cls == 2) & ~coastnb] = 0x3009
    b0[cls == 1] = 0x80
    m = mountains & land
    v[m] |= 0x2
    f = forest & land & ~mountains
    v[f] |= 0x100; b0[f] |= 0x04
    r = rcell & land & ~mountains
    v[r] |= 0x11; b0[r] |= 0x20
    # textures as in the stock maps: water and coast cells 0, the land ring touching them 3 (dirt, which
    # blends into the beach sand); grass right next to sand renders as hard-edged diamonds
    tex = tex.astype(np.int16).copy()
    tex[cls > 0] = 0
    shore = land & ndimage.binary_dilation(cls > 0, k3)
    tex[shore] = 3
    tex = legal_textures(tex, cls > 0, shore)
    c58 = np.stack([b0, np.zeros_like(b0), b2, tex], -1).astype(np.uint8)
    return c58, v
