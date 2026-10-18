"""Find structs in rise.pdb that have a member matching argv[1]; print their member offsets."""
import ctypes, sys
from ctypes import wintypes as W
WANTARGS = sys.argv[1:]; sys.argv = [sys.argv[0]]
import sym
dbg, hp, base = sym.dbg, sym.hp, sym.base
want = set(WANTARGS)
TI_SYMNAME, TI_TYPEID, TI_FINDCHILDREN, TI_OFFSET, TI_CHILDCOUNT, TI_SYMTAG, TI_LENGTH = 1, 4, 7, 10, 13, 0, 2
dbg.SymGetTypeInfo.argtypes = [W.HANDLE, ctypes.c_ulonglong, W.ULONG, ctypes.c_int, ctypes.c_void_p]
def name(t):
    p = ctypes.c_wchar_p()
    if dbg.SymGetTypeInfo(hp, base, t, TI_SYMNAME, ctypes.byref(p)): return p.value
    return None
def u32(t, kind):
    v = W.DWORD()
    return v.value if dbg.SymGetTypeInfo(hp, base, t, kind, ctypes.byref(v)) else None
def u64(t, kind):
    v = ctypes.c_ulonglong()
    return v.value if dbg.SymGetTypeInfo(hp, base, t, kind, ctypes.byref(v)) else None
def children(t):
    n = u32(t, TI_CHILDCOUNT) or 0
    if not n: return []
    class P(ctypes.Structure): _fields_ = [('Count', W.ULONG), ('Start', W.ULONG), ('Ids', W.ULONG * n)]
    p = P(n, 0)
    return list(p.Ids) if dbg.SymGetTypeInfo(hp, base, t, TI_FINDCHILDREN, ctypes.byref(p)) else []
seen = set(); hits = []
CB = ctypes.WINFUNCTYPE(W.BOOL, ctypes.POINTER(sym.SYMBOL_INFOW), W.ULONG, ctypes.c_void_p)
def cb(si, size, ctx):
    s = si.contents
    if s.Tag == 11 and s.TypeIndex not in seen:   # SymTagUDT
        seen.add(s.TypeIndex)
        for c in children(s.TypeIndex):
            if name(c) in want: hits.append((s.Name, s.TypeIndex)); break
        if ('size=%d' % (u64(s.TypeIndex, TI_LENGTH) or 0)) in want: hits.append((s.Name, s.TypeIndex))
    return True
dbg.SymEnumTypesW.argtypes = [W.HANDLE, ctypes.c_ulonglong, CB, ctypes.c_void_p]
dbg.SymEnumTypesW(hp, base, CB(cb), None)
print('udts', len(seen))
for n_, t in hits:
    print('==', n_, 'size', u64(t, TI_LENGTH))
    rows = []
    for c in children(t):
        off = u32(c, TI_OFFSET)
        if off is not None: rows.append((off, name(c), u64(u32(c, TI_TYPEID), TI_LENGTH)))
    for off, nm, ln in sorted(rows): print('  ', hex(off), nm, ln)
