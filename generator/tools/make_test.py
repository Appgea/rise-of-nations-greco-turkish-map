"""Build zR_test: the Capitals scenario plus test cities for checking the naming script."""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo, cities, scriptgen, build
src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out', 'GrecoTurkish_Capitals')
dst = os.path.join(build.GAME, 'scenario', 'Custom', 'zR_test'); os.makedirs(dst, exist_ok=True)
W = 512; H = round(W / geo.aspect() / 4) * 4
g = geo.Grid(W, H); yo = (W - H) // 2 // 4 * 4
def tile(lat, lon):
    x, y = g.to_xy(lon, lat); return int(x), int(y) + yo
slots = []
for la, lo, gr, tr in cities.CITIES:
    x, y = g.to_xy(lo, la)
    if 0 <= x < W and 0 <= y < H: slots.append((int(round(x)), int(round(y)) + yo, gr, tr, 9 if tr in cities.MAJOR else 0))
izm = tile(38.45, 27.25); sel = tile(40.66, 23.0); ank = tile(39.93, 32.86); ath = tile(38.05, 23.75)
test = f"""  create_building_near(1, {izm[0]} * wx / {W}, {izm[1]} * wx / {W}, "Small City", 6 * wx / {W});
  create_building_near(2, {sel[0]} * wx / {W}, {sel[1]} * wx / {W}, "Small City", 6 * wx / {W});
  add_reveal_point(1, {izm[0]} * wx / {W}, {izm[1]} * wx / {W}, 12 * wx / {W});
  add_reveal_point(1, {sel[0]} * wx / {W}, {sel[1]} * wx / {W}, 12 * wx / {W});
  add_reveal_point(1, {ank[0]} * wx / {W}, {ank[1]} * wx / {W}, 14 * wx / {W});"""
import re
bhs = open(os.path.join(src, 'GrecoTurkish_Capitals.bhs'), encoding='cp1252').read()
m1 = re.search(r'static int start_x\[\] = \[0, (\d+), (\d+)\];\s*static int start_y\[\] = \[0, (\d+), (\d+)\];', bhs)
s1 = (int(m1.group(1)), int(m1.group(3))); s2 = (int(m1.group(2)), int(m1.group(4)))
intro = 'TEST BUILD: Greek test city at Izmir, Turkish test city at Thessaloniki.'
caps = (next(i for i, s in enumerate(slots) if s[3] == 'Atina'), next(i for i, s in enumerate(slots) if s[3] == 'Ankara'))
out = scriptgen.make_script('zR_test', W, slots, [s1, s2], intro, test, cap_slots=caps)
open(os.path.join(dst, 'zR_test.bhs'), 'wb').write(out.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp1252'))
for ext in ('.scx', '.sce'):
    shutil.copyfile(os.path.join(src, 'GrecoTurkish_Capitals' + ext), os.path.join(dst, 'zR_test' + ext))
print('wrote', dst, 'izmir', izm, 'selanik', sel, 'starts', s1, s2)
