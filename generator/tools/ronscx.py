"""Rise of Nations .scx/.sce reader/writer: gzip'd nested chunks [u32 size][u16 id][u16 ver][payload]."""
import gzip, struct

class Chunk:
    def __init__(self, cid, ver, data=b'', children=None):
        self.cid, self.ver, self.data, self.children = cid, ver, data, children
    def find(self, *path):
        c = self
        for cid in path:
            c = next(x for x in c.children if x.cid == cid)
        return c
    def findall(self, cid):
        return [x for x in self.children if x.cid == cid]
    def encode(self):
        if self.children is not None:
            # for containers the u16 after the id is the child count
            body = b''.join(ch.encode() for ch in self.children); self.ver = len(self.children)
        else:
            body = self.data
        return struct.pack('<IHH', 8 + len(body), self.cid, self.ver) + body

def _tiles(d, s, e):
    o = s; n = 0
    while o < e:
        if e - o < 8: return False
        sz = struct.unpack_from('<I', d, o)[0]
        if sz < 8 or o + sz > e: return False
        o += sz; n += 1
    return n > 0

# chunk ids known to be containers (avoid false positives on raw data)
CONTAINERS = {0x00, 0x0b, 0x24, 0x26, 0x4c, 0x2c, 0x29, 0x02, 0x58, 0x44, 0x63, 0x68, 0x45, 0x5c, 0x60, 0x49,
              0x03, 0x04, 0x07, 0x05, 0x06, 0x09}

def _parse(d, o):
    sz, cid, ver = struct.unpack_from('<IHH', d, o)
    ps, pe = o + 8, o + sz
    if cid in CONTAINERS and (pe == ps or _tiles(d, ps, pe)):
        kids = []; p = ps
        while p < pe:
            k, p = _parse(d, p); kids.append(k)
        return Chunk(cid, ver, children=kids), pe
    return Chunk(cid, ver, d[ps:pe]), pe

def load(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b': raw = gzip.decompress(raw)
    root, end = _parse(raw, 0)
    assert end == len(raw)
    return root

def save(root, path):
    open(path, 'wb').write(gzip.compress(root.encode(), 9))

def dump(c, depth=0, maxdepth=9):
    print('  ' * depth + f'{c.cid:#06x} v{c.ver} ' + (f'[{len(c.children)} kids]' if c.children is not None else f'{len(c.data)}B {c.data[:16].hex(" ")}'))
    if c.children and depth < maxdepth:
        for k in c.children: dump(k, depth + 1, maxdepth)
