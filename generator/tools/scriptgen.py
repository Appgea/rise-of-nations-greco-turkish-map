"""Generate the RoN scenario script (.bhs): start setup + real-place city naming."""

KMAX = 128   # max cities tracked over a game

def _arr(vals, kind='int', per_line=16):
    if kind == 'String':
        items = ['"%s"' % v.replace('"', "'") for v in vals]
    else:
        items = [str(int(v)) for v in vals]
    lines = [', '.join(items[i:i + per_line]) for i in range(0, len(items), per_line)]
    return '[' + ',\n    '.join(lines) + ']'

def make_script(title, W, slots, start1, start2, leaders, intro, test_lines='', cap_slots=(-1, -1)):
    """slots: list of (tile_x, tile_y, greek_name, turkish_name[, pull]); start*: (tile_x, tile_y).
    pull (tiles) lets big cities claim a new city's name from further away."""
    n = len(slots)
    pull = _arr([(s[4] if len(s) > 4 else 0) ** 2 for s in slots])
    sx = _arr([s[0] for s in slots]); sy = _arr([s[1] for s in slots])
    gr = _arr([s[2] for s in slots], 'String', 8); tr = _arr([s[3] for s in slots], 'String', 8)
    zeros = _arr([0] * n); kz = _arr([0] * KMAX); ks = _arr([''] * KMAX, 'String', 32)
    return f'''// {title}
// Generated map script: starting cities, and every city takes the name of the nearest real place.
// Greek player (1) gets Greek names, Turkish player (2) gets Turkish names; captured cities are renamed.

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

static int setup_done = 0;
static int cap_slot[] = [-1, {cap_slots[0]}, {cap_slots[1]}];
static int cap_done[] = [0, 0, 0];

int p;
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
int x1;
int y1;
int x2;
int y2;
String cname;
String newname;

run_once {{
  wx = world_x_size();
  off = 6 * wx / {W};
  if (off < 1) {{
    off = 1;
  }}
  x1 = {start1[0]} * wx / {W};
  y1 = {start1[1]} * wx / {W};
  x2 = {start2[0]} * wx / {W};
  y2 = {start2[1]} * wx / {W};

  create_building_near(1, x1, y1, "Small City", 1 * wx / {W});
  if (num_cities(1) == 0) {{
    create_building_near(1, x1, y1, "Small City", 5 * wx / {W});
  }}
  if (num_cities(1) == 0) {{
    create_building_near(1, x1, y1, "Small City", 10 * wx / {W});
  }}
  create_unit(1, x1 + off, y1 + off, "Citizen", 5);
  create_unit(1, x1 + off, y1 + off, "Scout", 1);

  create_building_near(2, x2, y2, "Small City", 1 * wx / {W});
  if (num_cities(2) == 0) {{
    create_building_near(2, x2, y2, "Small City", 5 * wx / {W});
  }}
  if (num_cities(2) == 0) {{
    create_building_near(2, x2, y2, "Small City", 10 * wx / {W});
  }}
  create_unit(2, x2 + off, y2 + off, "Citizen", 5);
  create_unit(2, x2 + off, y2 + off, "Scout", 1);

  declare_war(1, 2);
  declare_war(2, 1);

  set_timer("names", 1);
  set_timer("endcheck", 30);
  setup_done = 1;
{test_lines}
  popup_dialog("{intro}");
}}

trigger NameCities(timer_expired("names"))
{{
  wx = world_x_size();
  for (p = 1; p < 3; p++) {{
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
              best = cap_slot[p];
            }}
            cap_done[p] = 1;
          }}
          if (best >= 0 && freeslot >= 0) {{
            if (p == 1) {{
              newname = gr_name[best];
            }}
            else {{
              newname = tr_name[best];
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
          if (p == 1) {{
            newname = gr_name[k_slot[found]];
          }}
          else {{
            newname = tr_name[k_slot[found]];
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
  if (num_cities(1) == 0) {{
    victory(2);
    defeat(1);
  }}
  else if (num_cities(2) == 0) {{
    victory(1);
    defeat(2);
  }}
  else {{
    set_timer("endcheck", 5);
    enable_trigger("CheckEnd");
  }}
}}

}}
'''
