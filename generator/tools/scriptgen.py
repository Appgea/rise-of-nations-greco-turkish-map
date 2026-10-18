"""Generate the RoN scenario script (.bhs): start setup + real-place city naming, for 2 to 8 player slots."""

KMAX = 160   # max cities tracked over a game

def _arr(vals, kind='int', per_line=16):
    if kind == 'String':
        items = ['"%s"' % v.replace('"', "'") for v in vals]
    else:
        items = [str(int(v)) for v in vals]
    lines = [', '.join(items[i:i + per_line]) for i in range(0, len(items), per_line)]
    return '[' + ',\n    '.join(lines) + ']'

def make_script(title, W, slots, starts, intro, test_lines='', cap_slots=None):
    """slots: list of (tile_x, tile_y, greek_name, turkish_name[, pull]); starts: one (tile_x, tile_y) per player slot;
    cap_slots: index into slots of each player's capital name. pull (tiles) lets big cities claim a new city's name
    from further away. Players of the Turks nation get Turkish names, everyone else Greek-side names."""
    n = len(slots); npl = len(starts)
    cap_slots = list(cap_slots or [-1] * npl)
    pull = _arr([(s[4] if len(s) > 4 else 0) ** 2 for s in slots])
    sx = _arr([s[0] for s in slots]); sy = _arr([s[1] for s in slots])
    gr = _arr([s[2] for s in slots], 'String', 8); tr = _arr([s[3] for s in slots], 'String', 8)
    zeros = _arr([0] * n); kz = _arr([0] * KMAX); ks = _arr([''] * KMAX, 'String', 32)
    px = _arr([0] + [x for x, _ in starts]); py = _arr([0] + [y for _, y in starts])
    cap = _arr([-1] + cap_slots); pz = _arr([0] * (npl + 1))
    return f'''// {title}
// Generated map script: starting cities, and every city takes the name of the nearest real place.
// Turks get Turkish names, every other nation Greek-side names; captured cities are renamed by the new owner.
// Save games: run_once does not run again on load, and the start setup is also guarded by setup_done.

scenario
{{

labels {{
}}

static int nslot = {n};
static int slot_x[] = {sx};
static int slot_y[] = {sy};
static String gr_name[] = {gr};
static String tr_name[] = {tr};
static int slot_used[] = {zeros};
static int slot_pull[] = {pull};

static int kmax = {KMAX};
static String k_name[] = {ks};
static int k_owner[] = {kz};
static int k_slot[] = {kz};

static int npl = {npl};
static int start_x[] = {px};
static int start_y[] = {py};
static int cap_slot[] = {cap};
static int cap_done[] = {pz};
static int setup_done = 0;

int p;
int q;
int c;
int n;
int i;
int j;
int best;
int bestd;
int d;
int dx;
int dy;
int cid;
int cx;
int cy;
int found;
int freeslot;
int wx;
int off;
int x;
int y;
int alive;
int enemies;
String cname;
String newname;
String nat;

run_once {{
  if (setup_done == 0) {{
    wx = world_x_size();
    off = 6 * wx / {W};
    if (off < 1) {{
      off = 1;
    }}
    for (p = 1; p <= npl; p++) {{
      if (num_cities(p) == 0) {{
        x = start_x[p] * wx / {W};
        y = start_y[p] * wx / {W};
        create_building_near(p, x, y, "Small City", 1 * wx / {W});
        if (num_cities(p) == 0) {{
          create_building_near(p, x, y, "Small City", 5 * wx / {W});
        }}
        if (num_cities(p) == 0) {{
          create_building_near(p, x, y, "Small City", 10 * wx / {W});
        }}
        create_unit(p, x + off, y + off, "Citizen", 5);
        create_unit(p, x + off, y + off, "Scout", 1);
      }}
    }}
    setup_done = 1;
{test_lines}
    popup_dialog("{intro}");
  }}
  set_timer("names", 1);
  set_timer("endcheck", 30);
}}

trigger NameCities(timer_expired("names"))
{{
  wx = world_x_size();
  for (p = 1; p <= npl; p++) {{
    nat = find_nation(p);
    n = num_cities(p);
    for (c = 0; c <= n; c++) {{
      cname = find_city_with_num(p, c);
      if (!(cname == "")) {{
        found = -1;
        for (j = 0; j < kmax; j++) {{
          if (k_owner[j] > 0) {{
            if (k_name[j] == cname) {{
              found = j;
              break;
            }}
          }}
        }}
        if (found == -1) {{
          cid = find_city_id(cname);
          cx = object_position_x(p, cid) * {W} / wx;
          cy = object_position_y(p, cid) * {W} / wx;
          best = -1;
          bestd = 999999999;
          for (i = 0; i < nslot; i++) {{
            if (slot_used[i] == 0) {{
              dx = slot_x[i] - cx;
              dy = slot_y[i] - cy;
              d = dx * dx + dy * dy - slot_pull[i];
              if (d < bestd) {{
                bestd = d;
                best = i;
              }}
            }}
          }}
          freeslot = -1;
          for (j = 0; j < kmax; j++) {{
            if (k_owner[j] == 0) {{
              freeslot = j;
              break;
            }}
          }}
          if (cap_done[p] == 0) {{
            if (cap_slot[p] >= 0) {{
              if (slot_used[cap_slot[p]] == 0) {{
                best = cap_slot[p];
              }}
            }}
            cap_done[p] = 1;
          }}
          if (best >= 0 && freeslot >= 0) {{
            if (nat == "turks") {{
              newname = tr_name[best];
            }}
            else {{
              newname = gr_name[best];
            }}
            rename_city(p, cid, newname);
            slot_used[best] = 1;
            k_name[freeslot] = newname;
            k_owner[freeslot] = p;
            k_slot[freeslot] = best;
          }}
        }}
        else if (k_owner[found] != p) {{
          cid = find_city_id(cname);
          if (nat == "turks") {{
            newname = tr_name[k_slot[found]];
          }}
          else {{
            newname = gr_name[k_slot[found]];
          }}
          if (!(newname == cname)) {{
            rename_city(p, cid, newname);
          }}
          k_name[found] = newname;
          k_owner[found] = p;
        }}
      }}
    }}
  }}
  for (j = 0; j < kmax; j++) {{
    if (k_owner[j] > 0) {{
      if (!city_exists(k_name[j])) {{
        slot_used[k_slot[j]] = 0;
        k_owner[j] = 0;
        k_name[j] = "";
      }}
    }}
  }}
  set_timer("names", 2);
  enable_trigger("NameCities");
}}

trigger CheckEnd(timer_expired("endcheck"))
{{
  // a player without cities is out; the game ends when every remaining player is allied with the others
  // (peace treaties alone don't end it)
  for (p = 1; p <= npl; p++) {{
    if (!is_defeated(p)) {{
      if (num_cities(p) == 0) {{
        defeat(p);
      }}
    }}
  }}
  alive = 0;
  enemies = 0;
  for (p = 1; p <= npl; p++) {{
    if (!is_defeated(p)) {{
      alive = alive + 1;
      for (q = p + 1; q <= npl; q++) {{
        if (!is_defeated(q)) {{
          if (!have_alliance(p, q)) {{
            enemies = 1;
          }}
        }}
      }}
    }}
  }}
  if (alive > 0 && enemies == 0) {{
    for (p = 1; p <= npl; p++) {{
      if (!is_defeated(p)) {{
        victory(p);
      }}
    }}
  }}
  else {{
    set_timer("endcheck", 5);
    enable_trigger("CheckEnd");
  }}
}}

}}
'''
