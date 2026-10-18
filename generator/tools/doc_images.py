"""Render the README images: map overview, city-name map and the generator pipeline."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build, geo, cities

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'docs', 'images')
TEXCOL = np.array([(96, 140, 64), (122, 140, 72), (156, 142, 92), (182, 158, 112)], np.float32)
SEA = (28, 62, 128)
K4 = lambda m: np.kron(m, np.ones((4, 4), m.dtype))

def font(size, bold=False):
    for f in (('segoeuib.ttf' if bold else 'segoeui.ttf'), ('arialbd.ttf' if bold else 'arial.ttf')):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', f), size)
        except OSError:
            pass
    return ImageFont.load_default()

def terrain_rgb(T, features=True):
    W, H = T['W'], T['H']
    img = TEXCOL[K4(T['tex'])]
    h = T['heights'][:H, :W]; gy, gx = np.gradient(h)
    img *= np.clip(1.0 + (gy - gx) / 160, 0.6, 1.3)[..., None]
    if features:
        img[K4(T['forest'])] = (34, 88, 40)
        img[K4(T['mt'])] = (150, 140, 128)
        img[T['river']] = (90, 160, 235)
    img[T['water']] = SEA
    return np.clip(img, 0, 255).astype(np.uint8)

def big(arr, scale):
    im = Image.fromarray(arr)
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)

def label(dr, xy, text, f, fill=(255, 255, 255), anchor='mm'):
    dr.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=3, stroke_fill=(0, 0, 0))

def strip(im, h):
    out = Image.new('RGB', (im.width, im.height + h), (16, 24, 44)); out.paste(im, (0, 0)); return out

def overview(T, res, ruins, starts, scale=3):
    im = big(terrain_rgb(T), scale); dr = ImageDraw.Draw(im)
    col = {'Fish': (120, 220, 255), 'Whales': (255, 255, 255), 'Oil': (20, 20, 20)}
    for name, x, y in res:
        c = col.get(name, (255, 200, 0)); r = 2 if name == 'Fish' else 3
        dr.ellipse([x * scale - r, y * scale - r, x * scale + r, y * scale + r], fill=c)
    for _, x, y in ruins:
        dr.rectangle([x * scale - 4, y * scale - 4, x * scale + 4, y * scale + 4], outline=(255, 0, 255), width=2)
    f = font(22, True)
    for variant, pts in starts.items():
        for side, (x, y) in zip(('greeks', 'turks'), pts):
            c = (40, 110, 255) if side == 'greeks' else (230, 30, 30)
            dr.ellipse([x * scale - 10, y * scale - 10, x * scale + 10, y * scale + 10], outline=c, width=4)
            label(dr, (x * scale, y * scale - 24), f'{variant.capitalize()} start', f, fill=c)
    # legend in a strip under the map
    items = [('mountains (mineable)', (150, 140, 128), 'box'), ('forest', (34, 88, 40), 'box'), ('river', (90, 160, 235), 'box'),
             ('resource (real site)', (255, 200, 0), 'dot'), ('oil', (20, 20, 20), 'dot'), ('fish', (120, 220, 255), 'dot'),
             ('whales', (255, 255, 255), 'dot'), ('ancient ruins', (255, 0, 255), 'ring'),
             ('Greek start', (40, 110, 255), 'circle'), ('Turkish start', (230, 30, 30), 'circle')]
    f2 = font(20); cols = 5; cw = im.width // cols
    out = strip(im, 2 * 34 + 20); dr = ImageDraw.Draw(out)
    for i, (txt, c, kind) in enumerate(items):
        x0 = 24 + (i % cols) * cw; y = im.height + 27 + 34 * (i // cols)
        if kind == 'box': dr.rectangle([x0, y - 9, x0 + 18, y + 9], fill=c)
        elif kind == 'dot': dr.ellipse([x0 + 3, y - 6, x0 + 15, y + 6], fill=c, outline=(120, 120, 120))
        elif kind == 'ring': dr.rectangle([x0 + 3, y - 6, x0 + 15, y + 6], outline=c, width=2)
        else: dr.ellipse([x0, y - 9, x0 + 18, y + 9], outline=c, width=3)
        dr.text((x0 + 32, y), txt, font=f2, fill=(235, 235, 235), anchor='lm')
    return out

def city_names(T, slots, scale=3):
    arr = terrain_rgb(T).astype(np.float32)
    arr = (arr * 0.55 + 255 * 0.12).astype(np.uint8)       # dim the terrain so labels read
    im = big(arr, scale); dr = ImageDraw.Draw(im)
    f1, f2 = font(19, True), font(16)
    for x, y, gr, tr, pull in slots:
        X, Y = x * scale, y * scale
        dr.ellipse([X - 3, Y - 3, X + 3, Y + 3], fill=(255, 255, 255))
    boxes = []
    def free(b):
        return (b[0] >= 2 and b[2] <= im.width - 2 and b[1] >= 2 and b[3] <= im.height - 2 and
                all(b[2] < o[0] or b[0] > o[2] or b[3] < o[1] or b[1] > o[3] for o in boxes))
    for x, y, gr, tr, pull in slots:
        if not pull:
            continue
        X, Y = x * scale, y * scale
        # try: names above/below the dot, then both to the right, then both to the left
        for (gx, gy, ga), (tx, ty, ta) in (((X, Y - 24, 'mm'), (X, Y + 22, 'mm')),
                                           ((X + 10, Y - 11, 'lm'), (X + 10, Y + 11, 'lm')),
                                           ((X - 10, Y - 11, 'rm'), (X - 10, Y + 11, 'rm'))):
            b1 = dr.textbbox((gx, gy), gr, font=f1, anchor=ga, stroke_width=3)
            b2 = dr.textbbox((tx, ty), tr, font=f2, anchor=ta, stroke_width=3)
            if free(b1) and free(b2):
                break
        else:
            continue
        boxes += [b1, b2]
        dr.ellipse([X - 6, Y - 6, X + 6, Y + 6], fill=(255, 210, 60), outline=(0, 0, 0))
        label(dr, (gx, gy), gr, f1, fill=(140, 190, 255), anchor=ga)
        label(dr, (tx, ty), tr, f2, fill=(255, 150, 150), anchor=ta)
    out = strip(im, 52); dr = ImageDraw.Draw(out); f3 = font(22, True); y = im.height + 26
    dr.text((24, y), 'Greek name', font=f3, fill=(140, 190, 255), anchor='lm')
    dr.text((190, y), 'Turkish name', font=f3, fill=(255, 150, 150), anchor='lm')
    dr.text((370, y), f'yellow = major historic cities (shown), white = {len(slots)} named places in total', font=font(20),
            fill=(235, 235, 235), anchor='lm')
    return out

def pipeline(T, scale=2):
    W, H = T['W'], T['H']
    land = np.where(T['water'][..., None], np.array(SEA, np.uint8), np.array((235, 225, 200), np.uint8))
    e = T['elev'][:H, :W].astype(np.float32); e = np.clip(e / 2500, 0, 1)
    ramp = np.array([(40, 110, 60), (150, 170, 90), (190, 160, 110), (150, 110, 90), (240, 240, 240)], np.float32)
    idx = e * (len(ramp) - 1); i0 = np.floor(idx).astype(int); i1 = np.minimum(i0 + 1, len(ramp) - 1); t = (idx - i0)[..., None]
    elev = (ramp[i0] * (1 - t) + ramp[i1] * t).astype(np.uint8); elev[T['water']] = SEA
    tex = TEXCOL[K4(T['tex'])].astype(np.uint8); tex[T['water']] = SEA
    panels = [(land, '1  Coastline: Natural Earth 10m land and islands, Greece widened'),
              (elev, '2  Real elevation (Terrarium DEM), later smoothed so cities fit'),
              (tex, '3  Ground colour from NASA Blue Marble'),
              (terrain_rgb(T), '4  Mountains on real ranges, forests, 9 major rivers')]
    pw, ph = W * scale, H * scale; pad, cap = 16, 44
    im = Image.new('RGB', (2 * pw + 3 * pad, 2 * (ph + cap) + 3 * pad), (20, 22, 28)); dr = ImageDraw.Draw(im)
    f = font(22, True)
    for i, (arr, txt) in enumerate(panels):
        cx, cy = pad + (i % 2) * (pw + pad), pad + (i // 2) * (ph + cap + pad)
        dr.text((cx, cy + cap // 2), txt, font=f, fill=(235, 235, 235), anchor='lm')
        im.paste(big(arr, scale), (cx, cy + cap))
    return im

def main():
    os.makedirs(OUT, exist_ok=True)
    W = 512; H = round(W / geo.aspect() / 4) * 4
    T = build.compute_terrain(W, H)
    res, ruins = build.place_resources(T)
    P = build.pad_square(T); yo = P['yoff']
    g = T['g']; slots = []
    for la, lo, gr, tr in cities.CITIES:
        x, y = g.to_xy(lo, la)
        if 0 <= x < W and 0 <= y < H:
            slots.append((int(round(x)), int(round(y)), gr, tr, 9 if tr in cities.MAJOR else 0))
    starts = {}
    for variant, st in cities.STARTS.items():
        pts = []
        for side in ('greeks', 'turks'):
            s = next(s for s in slots if s[3] == st[side])
            x, y = build.good_start(P, s[0], s[1] + yo); pts.append((x, y - yo))
        starts[variant] = pts
    overview(T, res, ruins, starts).save(os.path.join(OUT, 'overview.png'), optimize=True)
    city_names(T, slots).save(os.path.join(OUT, 'city_names.png'), optimize=True)
    pipeline(T).save(os.path.join(OUT, 'pipeline.png'), optimize=True)
    print('wrote', OUT)

if __name__ == '__main__':
    main()
