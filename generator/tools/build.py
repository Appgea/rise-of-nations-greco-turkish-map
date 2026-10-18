"""Build the Greco-Turkish RoN scenarios from real geography."""
import argparse, os, shutil, struct, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ronscx, geo, terrain, features, cities, resources, scriptgen
from ronscx import Chunk

# game folder: set RON_DIR if Steam installed it somewhere else
GAME = os.environ.get('RON_DIR', 'C:/Program Files (x86)/Steam/steamapps/common/Rise of Nations')
TEMPLATE = GAME + '/conquest/Napoleon/turkey.scx'           # 2 players (France, Turks), 0x6c header
RES_RECORD_SRC = GAME + '/scenario/Custom/italy_mp/italy_mp.scx'
GOODY_RECORD_SRC = GAME + '/scenario/Custom/skirmish/skirmish.sce'
NATION = {'greeks': 5, 'turks': 8}
LAND_THR = 0.35     # tile is land if >= 35% land (slightly widens coasts)
WEST_MTN = 0.82     # mountain score multiplier west of 27E (Greece and the Balkans: more room to build)
# default leader names per nation, used in slot order (the setup screen keeps them for computer players)
LEADERS = {'greeks': ['Eleftherios Venizelos', 'Ioannis Metaxas', 'Anastasios Papoulas'],
           'turks': ['Mustafa Kemal Atatürk', 'İsmet İnönü', 'Fevzi Çakmak']}
VARIANTS = (('frontier', 'Frontier', 'Greco-Turkish War - Frontier'), ('capitals', 'Capitals', 'Greco-Turkish War - Capitals'),
            ('4p', '4P', 'Greco-Turkish War - 4 players'), ('6p', '6P', 'Greco-Turkish War - 6 players'))
# peaks that should always carry a mountain/rock if it fits (lat, lon)
PEAKS = [(35.30, 24.00), (35.23, 24.77), (34.93, 32.86), (40.08, 22.36), (38.53, 22.62), (36.95, 22.35),
         (40.07, 29.22), (38.53, 35.45), (38.13, 34.17), (39.70, 44.30), (39.70, 26.85), (40.17, 24.33)]

def leaf(cid, data): return Chunk(cid, 0, data)

def diag_order(n):
    """Cell order of chunk 0x5b: diagonals from the (n-1, n-1) corner, the last cell left out."""
    Y, X = np.divmod(np.arange(n * n), n)
    return np.lexsort((n - 1 - Y, (n - 1 - X) + (n - 1 - Y)))[:-1]
def box(cid, kids): return Chunk(cid, len(kids), children=kids)
def u32s(*v): return struct.pack(f'<{len(v)}I', *v)

# ---------------------------------------------------------------- terrain
def compute_terrain(W, H):
    g = geo.Grid(W, H); ch, cw = H // 4, W // 4
    land, _ = geo.land_fraction(g)
    elev = geo.elevation(g)
    water, flags = terrain.tile_layers(g, land, land_thr=LAND_THR)
    cl = features.cell_land(water)
    emax, rel = features.relief(elev, H, W)
    river, polys = features.river_layers(g, water)
    rcell = river.reshape(ch, 4, cw, 4).any((1, 3))
    sites = []; site_names = []
    for la, lo, _, tr in cities.CITIES:
        x, y = g.to_xy(lo, la)
        if 0 <= x < W and 0 <= y < H: sites.append((int(y // 4), int(x // 4))); site_names.append(tr)
    site_mask = np.zeros((ch, cw), bool)
    for sy, sx in sites: site_mask[sy, sx] = True
    keep_clear = ndimage.binary_dilation(site_mask, np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool))   # town sites stay buildable
    allowed = cl & ~rcell & ~keep_clear
    coastal = ndimage.binary_dilation(~cl, np.ones((3, 3), bool))
    # Greece/Balkans (west of ~27E) are rugged and narrow: fewer impassable mountains there
    lon_c = geo.LON0 + (np.arange(cw) + 0.5) * 4 / W * (geo.LON1 - geo.LON0)
    west = np.where(lon_c < 27.0, WEST_MTN, 1.0)[None, :]
    score = (rel / 1000 + emax / 5000) * np.where(coastal, 0.85, 1.0) * west
    mt, recs = features.stamp_ranges(score, allowed, cap_cells=int(0.07 * cl.sum()))
    # make sure famous peaks (Crete, Troodos, Olympus...) get at least a small mountain
    for la, lo in PEAKS:
        x, y = g.to_xy(lo, la); cx, cy = int(x // 4), int(y // 4)
        if mt[max(cy - 1, 0):cy + 2, max(cx - 1, 0):cx + 2].any(): continue
        for tid in (features.ROCK_TID, 14, 12):
            done = False
            for oy in (0, 1, -1, 2):
                for ox in (0, 1, -1, 2):
                    hit = features._fits(features.TEMPLATES[tid], cy + oy, cx + ox, allowed & ~mt)
                    if hit is not None:
                        features._place(mt, recs, tid, cy + oy, cx + ox, *hit); done = True; break
                if done: break
            if done: break
    rock_ok = cl & ~rcell & ~site_mask      # outcrops may sit beside other towns' zones, never on a town
    major_sites = [s for s, c in zip(sites, site_names) if c in cities.MAJOR]
    mt, recs, n_site = features.rocks_near_sites(mt, recs, rock_ok, score, major_sites, rmin=2, rmax=3)
    mt, recs = features.add_rocks(mt, recs, allowed, score, max_gap=7)
    green, bright = terrain.vegetation(g)
    gc = green.reshape(ch, 4, cw, 4).mean((1, 3)); bc = bright.reshape(ch, 4, cw, 4).mean((1, 3))
    fidx = gc * 4 + (90 - bc) / 120
    fallow = cl & ~mt & ~rcell & ~keep_clear & ~ndimage.binary_dilation(mt, np.ones((3, 3), bool))
    forest = features.forests(fidx, fallow, real_frac=0.11, max_gap=7)
    rng = np.random.default_rng(11)
    forest = features.wood_near_sites(forest, fallow, major_sites, rng)
    # start cities and every big historic city get a kit: open ground for the city and its farms,
    # a wood and a mine nearby (start cities first, so theirs are never cleared by a neighbour's)
    land_ok = cl & ~rcell
    kits = {}
    starts = sorted({c for st in cities.STARTS.values() for c, _, _ in st})
    for name in starts + sorted(set(site_names) & cities.MAJOR - set(starts)):
        kits[name] = features.start_kit(mt, recs, forest, land_ok, score, sites[site_names.index(name)], rng,
                                        clear_r=1.8 if name in starts else 1.4)
    for name in starts:   # re-assert the start kits' clear disks
        features.start_kit(mt, recs, forest, land_ok, score, sites[site_names.index(name)], rng)
    tex = terrain.textures(green, water)
    flags = flags.copy(); flags[river] |= terrain.RIVER
    heights = terrain.vertex_heights(water, elev, river, mt)
    c58, v63 = terrain.coarse_layers_full(flags, mt, forest, river, tex)
    return dict(g=g, W=W, H=H, water=water, flags=flags, heights=heights, mt=mt, recs=recs, forest=forest,
                river=river, polys=polys, tex=tex, c58=c58, v63=v63, elev=elev, kits=kits)

def pad_square(T):
    """Fallback for engines that only take square maps: add open sea above and below."""
    W, H = T['W'], T['H']
    extra = W - H; top = (extra // 2) // 4 * 4; bot = extra - top
    pt = lambda a, v: np.pad(a, ((top, bot), (0, 0)) + ((0, 0),) * (a.ndim - 2), constant_values=v)
    pc = lambda a, v: np.pad(a, ((top // 4, bot // 4), (0, 0)) + ((0, 0),) * (a.ndim - 2), constant_values=v)
    T = dict(T)
    T['water'] = pt(T['water'], True); T['river'] = pt(T['river'], False)
    T['flags'] = pt(T['flags'], terrain.WATER)
    T['heights'] = np.pad(T['heights'], ((top, bot), (0, 0)), constant_values=-273).astype(np.float32)
    T['mt'] = pc(T['mt'], False); T['forest'] = pc(T['forest'], False); T['tex'] = pc(T['tex'], 0)
    T['recs'] = [(((p // 256) + top // 4) * 256 + p % 256, t, n) for p, t, n in T['recs']]
    T['polys'] = [(nm, [(x, y + top // 4) for x, y in pts]) for nm, pts in T['polys']]
    T['c58'], T['v63'] = terrain.coarse_layers_full(T['flags'], T['mt'], T['forest'], T['river'], T['tex'])
    T['H'] = W; T['yoff'] = top
    return T

def good_start(T, x, y, rmax=28, half=3):
    """Nearest tile to (x, y) where a city (7x7 tiles) plus a 1-tile margin sits entirely on dry,
    buildable land: no water/coast/river tiles, no coast, forest or mountain cells, height above 15."""
    flags = T['flags']; c58 = T['c58']; v63 = T['v63']; H, W = flags.shape
    cell_ok = (c58[..., 2] == 0) & ~T['mt'] & ~T['forest']
    tile_ok = (flags == 0) & np.kron(cell_ok, np.ones((4, 4), bool)) & (T['heights'][:H, :W] > 8)
    k = 2 * half + 1
    fits = ndimage.minimum_filter(tile_ok.astype(np.uint8), size=k, mode='constant', cval=0) > 0
    ys, xs = np.nonzero(fits)
    if len(xs) == 0: return int(x), int(y)
    d = (xs - x) ** 2 + (ys - y) ** 2
    i = int(np.argmin(d))
    if d[i] > rmax * rmax: print('  warning: start far from target', x, y, '->', xs[i], ys[i])
    return int(xs[i]), int(ys[i])

# ---------------------------------------------------------------- resources
def _snap(T, x, y, ok, rmax=12):
    """Nearest tile (x,y) where ok is True."""
    H, W = ok.shape
    xi, yi = int(x), int(y)
    for r in range(rmax + 1):
        best = None
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r: continue
                xx, yy = xi + dx, yi + dy
                if 0 <= xx < W and 0 <= yy < H and ok[yy, xx]:
                    d = dx * dx + dy * dy
                    if best is None or d < best[0]: best = (d, xx, yy)
        if best: return best[1], best[2]
    return None

def place_resources(T):
    g, water, W, H = T['g'], T['water'], T['W'], T['H']
    mt_t = np.kron(T['mt'], np.ones((4, 4), bool))
    fo_t = np.kron(T['forest'], np.ones((4, 4), bool))
    free_land = ~water & ~mt_t & ~fo_t & ~T['river']
    dland = ndimage.distance_transform_cdt(water, metric='chessboard')
    out = []          # (name, tile_x, tile_y)
    # fish: shallow water 2-5 tiles from shore, spaced out
    cand = np.argwhere(water & (dland >= 2) & (dland <= 4))
    rng = np.random.RandomState(7); rng.shuffle(cand)
    taken = np.zeros_like(water)
    for y, x in cand:
        if taken[max(y - 7, 0):y + 8, max(x - 7, 0):x + 8].any(): continue
        taken[y, x] = True; out.append(('Fish', x + 0.5, y + 0.5))
    # whales: open Mediterranean/Aegean (not the Black Sea), far from shore
    lon_bs, lat_bs = 27.6, 40.9
    deep = np.argwhere(water & (dland >= 10)); rng.shuffle(deep)
    wt = np.zeros_like(water)
    for y, x in deep:
        lo, la = g.to_lonlat(x, y)
        if la > lat_bs and lo > lon_bs: continue
        if wt[max(y - 30, 0):y + 31, max(x - 30, 0):x + 31].any(): continue
        wt[y, x] = True; out.append(('Whales', x + 0.5, y + 0.5))
    # oil clusters
    for la, lo, k in resources.OIL:
        x, y = g.to_xy(lo, la)
        if not (0 <= x < W and 0 <= y < H): continue
        offshore = water[min(int(y), H - 1), min(int(x), W - 1)]
        ok = water.copy() if offshore else free_land.copy()
        for j in range(k + 1):
            p = _snap(T, x + 3 * np.cos(j * 2.1), y + 3 * np.sin(j * 2.1), ok)
            if p:
                out.append(('Oil', p[0] + 0.5, p[1] + 0.5)); ok[max(p[1] - 2, 0):p[1] + 3, max(p[0] - 2, 0):p[0] + 3] = False
    # rare resources
    for la, lo, name in resources.RARE:
        x, y = g.to_xy(lo, la)
        if not (0 <= x < W and 0 <= y < H): continue
        p = _snap(T, x, y, free_land)
        if p: out.append((name, p[0] + 0.5, p[1] + 0.5))
    ruins = []
    for la, lo in resources.RUINS:
        x, y = g.to_xy(lo, la)
        p = _snap(T, x, y, free_land)
        if p: ruins.append(('Goody Box', p[0] + 0.5, p[1] + 0.5))
    return out, ruins

def _template_record(path, cid):
    r = ronscx.load(path)
    c = r.find(cid); n = struct.unpack('<I', c.children[0].data)[0]
    return c.children[1].data[:len(c.children[1].data) // n]

def records(items, tmpl):
    rs = len(tmpl); out = bytearray()
    for name, x, y in items:
        rec = bytearray(tmpl)
        nm = name.encode('utf-16le') + b'\0\0'
        rec[:64] = (nm + bytes(64))[:64]
        # object positions are in world units of 3/4 tile, x256 (verified: stock fish all land on water)
        struct.pack_into('<II', rec, rs - 8, int(x * 192), int(y * 192))
        out += rec
    return bytes(out)

# ---------------------------------------------------------------- chunks
def map_chunk(old, T):
    W, H = T['W'], T['H']; ch, cw = H // 4, W // 4; n = cw * ch
    kids = []
    for c in old.children:
        if c.cid == 0x58:
            kids.append(box(0x58, [leaf(0x0f, u32s(n, cw, ch)), leaf(0x10, T['c58'].tobytes())]))
        elif c.cid == 0x44:
            kids.append(box(0x44, [leaf(0x11, u32s(W * H, W, H)), leaf(0x12, T['flags'].astype('<u2').tobytes())]))
        elif c.cid == 0x59:
            kids.append(leaf(0x59, T['heights'].astype('<f4').tobytes()))
        elif c.cid == 0x5b:
            # 0x5b = the 0x63 cells in the renderer's diagonal order (verified on every stock map). The engine
            # blends beaches and coasts from it; left as zeros, coast cells render as hard-edged sand blocks.
            kids.append(leaf(0x5b, T['v63'].ravel()[diag_order(T['v63'].shape[0])].astype('<u2').tobytes()))
        elif c.cid == 0x63:
            kids.append(box(0x63, [leaf(0x64, u32s(n)), leaf(0x65, T['v63'].astype('<u2').tobytes())]))
        elif c.cid == 0x68:
            kids.append(box(0x68, [leaf(0x69, u32s(n)), leaf(0x6a, bytes(n))]))
        elif c.cid == 0x45:
            recs = T['recs']
            kids.append(box(0x45, [leaf(0x46, u32s(len(recs))),
                                   leaf(0x47, b''.join(struct.pack('<3I', *r) for r in recs))]))
        elif c.cid == 0x49:
            kids.append(box(0x49, [leaf(0x4a, u32s(0)), leaf(0x4b, b'')]))
        elif c.cid == 0x5c:
            rk = [leaf(0x5d, u32s(len(T['polys'])))]
            for _, pts in T['polys']:
                rk.append(leaf(0x5e, u32s(len(pts))))
                rk += [leaf(0x5f, struct.pack('<2i', x, y)) for x, y in pts]
            kids.append(box(0x5c, rk))
        else:
            kids.append(c)
    return box(0x02, kids)

def set_players(root, slots):
    """slots: (nation id, leader name, team) per player. Extra slots are copies of the template's second player.
    Every slot is human (multiplayer refuses scenarios with fewer than 2 humans); the setup screen turns slots
    into computer players and changes nations and teams."""
    import copy
    P = root.find(0x0b)
    base = P.children[1]
    P.children = [P.children[i] if i < 2 else copy.deepcopy(base) for i in range(len(slots))]
    for i, (p, (nat, lead, team)) in enumerate(zip(P.children, slots)):
        info = p.find(0x6b); d = bytearray(info.data)
        struct.pack_into('<i', d, 0, i); struct.pack_into('<i', d, 4, nat)
        # LeaderPropertiesChunk3 (rise.pdb): 0x08 leader_flags (template has conquest transport locks),
        # 0x10 city_name_index, 0xdc is_human (4 = human), 0xe4 team_color, 0xe8 difficulty
        struct.pack_into('<i', d, 0x08, 0); struct.pack_into('<i', d, 0x10, 0)
        struct.pack_into('<i', d, 0xdc, 4); d[0xe4] = i; struct.pack_into('<i', d, 0xe8, 0)
        nm = lead.encode('utf-16le') + b'\0\0'
        d[20:220] = (nm + bytes(200))[:200]
        info.data = bytes(d)
        t = p.find(0x26)
        t.children = [leaf(t.children[0].cid, u32s(0)), leaf(t.children[1].cid, b'')]
        # DiploDataChunk (who, diplo, treaty) per player: 0 war / 2 ally by default team; self (i, 0, 0)
        dip = [c for c in p.children if c.cid == 0x29][0]
        ents = b''.join(struct.pack('<3i', j, 0, 0) if j == i else
                        struct.pack('<3i', j, 2 if slots[j][2] == team else 0, 1) for j in range(len(slots)))
        dip.children = [leaf(dip.children[0].cid, u32s(len(slots))), leaf(dip.children[1].cid, ents)]

def set_header(root, title, starts):
    h = root.children[0]; assert h.cid == 0x6c
    d = bytearray(h.data)
    nm = title.encode('utf-16le') + b'\0\0'
    d[8:8 + 120] = (nm + bytes(120))[:120]
    xs = [-1] * 8; ys = [-1] * 8
    for i, (x, y) in enumerate(starts):
        xs[i] = int(x * 192); ys[i] = int(y * 192)
    struct.pack_into('<8i', d, 0x118, *xs); struct.pack_into('<8i', d, 0x138, *ys)
    # game settings: start age Ancient (0), end age Information (7), Standard victory (0), no time limit (1)
    struct.pack_into('<i', d, 0xec, 0); struct.pack_into('<i', d, 0xf0, 7)
    struct.pack_into('<i', d, 0xfc, 0); struct.pack_into('<i', d, 0x104, 1)
    # scenario_flags: 1 = use the scenario's own .bhs script, 2 = SCENARIO_ALLOW_SETUP_OVERRIDE (nations, teams and
    # computer players can be changed on the setup screen); team_style 11 = CUSTOM_OPEN
    struct.pack_into('<i', d, 0xe4, 1 | 2); struct.pack_into('<i', d, 0xd0, 11)
    h.data = bytes(d)

def put_list(root, cid, payload, count):
    c = root.find(cid)
    c.children = [leaf(c.children[0].cid, u32s(count)), leaf(c.children[1].cid, payload)]

# ---------------------------------------------------------------- preview
def preview(path, T, res, ruins, slots, starts, scale=3):
    W, H = T['W'], T['H']
    texcol = np.array([(96, 140, 64), (122, 140, 72), (156, 142, 92), (182, 158, 112)], np.float32)
    img = texcol[np.kron(T['tex'], np.ones((4, 4), np.uint8))]
    h = T['heights'][:H, :W]; gy, gx = np.gradient(h)
    img *= np.clip(1.0 + (gy - gx) / 160, 0.6, 1.3)[..., None]
    img[np.kron(T['forest'], np.ones((4, 4), bool))] = (34, 88, 40)
    img[np.kron(T['mt'], np.ones((4, 4), bool))] = (150, 140, 128)
    img[T['river']] = (90, 160, 235)
    img[T['water']] = (28, 62, 128)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W * scale, H * scale), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    col = {'Fish': (120, 220, 255), 'Whales': (255, 255, 255), 'Oil': (20, 20, 20)}
    for name, x, y in res:
        c = col.get(name, (255, 200, 0)); r = 2 if name == 'Fish' else 3
        dr.ellipse([x * scale - r, y * scale - r, x * scale + r, y * scale + r], fill=c)
    for _, x, y in ruins:
        dr.rectangle([x * scale - 3, y * scale - 3, x * scale + 3, y * scale + 3], outline=(255, 0, 255), width=2)
    for i, (x, y) in enumerate(starts):
        c = (40, 110, 255) if i == 0 else (230, 30, 30)
        dr.ellipse([x * scale - 8, y * scale - 8, x * scale + 8, y * scale + 8], outline=c, width=3)
    im.save(path)

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--W', type=int, default=512)
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out'))
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--mod', action='store_true', help='also copy into mods/GrecoTurkishWar (the Steam Workshop mod; '
                    're-publish it from Tools & Extras > Steam Workshop)')
    ap.add_argument('--rect', action='store_true', help='rectangular map (crashes RoN EE 1.20 in TileSet code)')
    a = ap.parse_args()
    W = a.W; H = round(W / geo.aspect() / 4) * 4
    T = compute_terrain(W, H)
    g = T['g']
    res, ruins = place_resources(T)
    slots = []
    for la, lo, gr, tr in cities.CITIES:
        x, y = g.to_xy(lo, la)
        if 0 <= x < W and 0 <= y < H:
            slots.append((int(round(x)), int(round(y)), gr, tr, 9 if tr in cities.MAJOR else 0))
    suffix = ''
    if not a.rect:
        T = pad_square(T); yo = T['yoff']; suffix = ''
        res = [(n, x, y + yo) for n, x, y in res]; ruins = [(n, x, y + yo) for n, x, y in ruins]
        slots = [(x, y + yo, gr, tr, w) for x, y, gr, tr, w in slots]
    res_tmpl = _template_record(RES_RECORD_SRC, 0x04)
    goody_tmpl = _template_record(GOODY_RECORD_SRC, 0x03)
    print(f'map {W}x{H} ({g.km_per_tile():.2f} km/tile): mountains {len(T["recs"])} stamps / {int(T["mt"].sum())} cells, '
          f'forest {int(T["forest"].sum())} cells, rivers {len(T["polys"])}, resources {len(res)}, ruins {len(ruins)}, '
          f'city names {len(slots)}')
    made = []
    intro = ('Greco-Turkish War on a real map of the Aegean, Anatolia and the Balkans. '
             'Every city you found takes the real name of the nearest place, in your own language; '
             'captured cities are renamed by their new owner. Take all enemy cities to win.')
    for variant, label, title in VARIANTS:
        st = cities.STARTS[variant]
        def pos(trname):
            cy, cx = T['kits'][trname]; return good_start(T, cx * 4 + 2, cy * 4 + 2 + T.get('yoff', 0))
        starts = [pos(c) for c, _, _ in st]
        used = {'greeks': 0, 'turks': 0}; pslots = []
        for c, nat, team in st:
            pslots.append((NATION[nat], LEADERS[nat][used[nat] % len(LEADERS[nat])], team)); used[nat] += 1
        root = ronscx.load(TEMPLATE)
        root.children = [map_chunk(c, T) if c.cid == 0x02 else c for c in root.children]
        for c in root.children:
            if c.cid in (0x05, 0x06, 0x07): c.children = []
        put_list(root, 0x04, records(res, res_tmpl), len(res))
        put_list(root, 0x03, records(ruins, goody_tmpl), len(ruins))
        set_players(root, pslots)
        set_header(root, title, starts)
        name = 'GrecoTurkish_' + label + suffix
        d = os.path.join(a.out, name); os.makedirs(d, exist_ok=True)
        ronscx.save(root, os.path.join(d, name + '.scx'))
        shutil.copyfile(os.path.join(d, name + '.scx'), os.path.join(d, name + '.sce'))
        caps = [next(i for i, s_ in enumerate(slots) if s_[3] == c) for c, _, _ in st]
        bhs = scriptgen.make_script(title, W, slots, starts, intro, cap_slots=caps)
        # RoN's script reader needs CRLF line endings (with LF the whole file is one line = one comment)
        open(os.path.join(d, name + '.bhs'), 'wb').write(bhs.replace(chr(13) + chr(10), chr(10)).replace(chr(10), chr(13) + chr(10)).encode('cp1252'))
        preview(os.path.join(d, 'preview.png'), T, res, ruins, slots, starts)
        made.append((name, d))
        print('wrote', d)
    if a.install:
        for name, d in made:
            dst = os.path.join(GAME, 'scenario', 'Custom', name)
            os.makedirs(dst, exist_ok=True)
            for ext in ('.scx', '.sce', '.bhs'):
                shutil.copyfile(os.path.join(d, name + ext), os.path.join(dst, name + ext))
            print('installed', dst)
    if a.mod:
        for name, d in made:
            dst = os.path.join(GAME, 'mods', 'GrecoTurkishWar', 'scenario', 'Custom', name)
            os.makedirs(dst, exist_ok=True)
            for ext in ('.scx', '.sce', '.bhs'):
                shutil.copyfile(os.path.join(d, name + ext), os.path.join(dst, name + ext))
            print('mod', dst)

if __name__ == '__main__':
    main()
