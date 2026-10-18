import ctypes, sys, os
from ctypes import wintypes as W
G = r'C:\Program Files (x86)\Steam\steamapps\common\Rise of Nations'
dbg = ctypes.WinDLL(r'C:\Windows\System32\dbghelp.dll')
ctypes.windll.kernel32.GetCurrentProcess.restype = W.HANDLE
hp = ctypes.windll.kernel32.GetCurrentProcess()
dbg.SymSetOptions(0x00000002 | 0x00000010 | 0x00000040)  # UNDNAME | DEFERRED | LOAD_LINES
dbg.SymInitializeW.argtypes = [W.HANDLE, W.LPCWSTR, W.BOOL]
assert dbg.SymInitializeW(hp, G + r'\sbl;' + G, False)
dbg.SymLoadModuleExW.restype = ctypes.c_ulonglong
dbg.SymLoadModuleExW.argtypes = [W.HANDLE, W.HANDLE, W.LPCWSTR, W.LPCWSTR, ctypes.c_ulonglong, W.DWORD, ctypes.c_void_p, W.DWORD]
BASE = 0x400000
base = dbg.SymLoadModuleExW(hp, None, G + r'\riseofnations.exe', None, BASE, 0x1000000, None, 0)
print('loaded base', hex(base))
class SYMBOL_INFOW(ctypes.Structure):
    _fields_ = [('SizeOfStruct', W.ULONG), ('TypeIndex', W.ULONG), ('Reserved', ctypes.c_ulonglong * 2), ('Index', W.ULONG),
                ('Size', W.ULONG), ('ModBase', ctypes.c_ulonglong), ('Flags', W.ULONG), ('Value', ctypes.c_ulonglong),
                ('Address', ctypes.c_ulonglong), ('Register', W.ULONG), ('Scope', W.ULONG), ('Tag', W.ULONG),
                ('NameLen', W.ULONG), ('MaxNameLen', W.ULONG), ('Name', W.WCHAR * 1024)]
class LINE(ctypes.Structure):
    _fields_ = [('SizeOfStruct', W.DWORD), ('Key', ctypes.c_void_p), ('LineNumber', W.DWORD), ('FileName', W.LPWSTR), ('Address', ctypes.c_ulonglong)]
def lookup(addr):
    si = SYMBOL_INFOW(); si.SizeOfStruct = 88; si.MaxNameLen = 1000
    disp = ctypes.c_ulonglong()
    ok = dbg.SymFromAddrW(W.HANDLE(hp), ctypes.c_ulonglong(addr), ctypes.byref(disp), ctypes.byref(si))
    ln = LINE(); ln.SizeOfStruct = ctypes.sizeof(LINE); d2 = W.DWORD()
    okl = dbg.SymGetLineFromAddrW64(W.HANDLE(hp), ctypes.c_ulonglong(addr), ctypes.byref(d2), ctypes.byref(ln))
    return (si.Name if ok else '?'), disp.value, ((ln.FileName, ln.LineNumber) if okl else None)
if __name__ == "__main__":
  pass
for name in ('SymFromAddrW','SymGetLineFromAddrW64'):
    getattr(dbg,name).argtypes=None
for a in (sys.argv[1:] if __name__ == "__main__" else []):
    rva = int(a, 16)
    print(a, lookup(BASE + rva))
