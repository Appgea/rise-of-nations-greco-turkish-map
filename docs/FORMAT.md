# RoN: Extended Edition scenario format notes

These notes were reverse-engineered while building this map, against RoN: EE 1.20. Struct and field names come from
the game's own debug symbols (`sbl\rise.pdb`, read with `generator/tools/pdbtypes.py`) where noted. Everything else
was found by experiment. `generator/tools/ronscx.py` implements the container format.

## Container
A `.scx` (game) or `.sce` (editor) file is gzip-compressed. Inside is a tree of chunks:

```
u32 size | u16 id | u16 ver | payload
```
- For container chunks, `ver` is the child count and the payload is the children.
- Containers used here: `0x00 0x02 0x03 0x04 0x05 0x06 0x07 0x09 0x0b 0x24 0x26 0x29 0x2c 0x44 0x45 0x49 0x4c 0x58 0x5c 0x60 0x63 0x68`.
- The `.sce` can be a byte copy of the `.scx`.

Top level (2-player scenario): `0x6c` header, `0x0b` players, `0x02` map, `0x0a`, `0x03` goody boxes, `0x04` goods,
`0x07`, `0x05`, `0x06`, `0x08`, `0x09`.

## Header `0x6c` = `ScenHeaderChunk6` (384 bytes, from the pdb)
| Offset | Field | Notes |
|---|---|---|
| 0x00 | num_chunks | |
| 0x04 | file_id | |
| 0x08 | name[200] | UTF-16 |
| 0xd0 | team_style | |
| 0xd4 | game_rules | |
| 0xd8 | map_style | |
| 0xdc | map_size | |
| 0xe0 | map_seed | |
| 0xe4 | scenario_flags | **bit 0 must be set or the scenario's `.bhs` script is ignored** |
| 0xe8 | game_speed | |
| 0xec | start_tech | start age, 0 = Ancient |
| 0xf0 | end_tech | 7 = Information |
| 0xf4 | reveal_map | |
| 0xf8 | elimination | |
| 0xfc | victory | 0 = standard |
| 0x100 | score_goal | |
| 0x104 | time_limit | 1 = none |
| 0x108 / 0x10c / 0x110 | wonderwin / popwin / econwin | |
| 0x114 | rush_rules | |
| 0x118 | camera_init_x[8] | start positions, world units (see below) |
| 0x138 | camera_init_y[8] | |
| 0x158 | camera_init_zoom[8] | |
| 0x178 | ai_sea_map | |
| 0x17c | pop_limit | |

Older scenarios use header `0x67` (300 bytes).

## Players `0x0b` → `0x24` per player → `0x6b` = `LeaderPropertiesChunk3` (236 bytes, from the pdb)
| Offset | Field | Notes |
|---|---|---|
| 0x00 | who | player index |
| 0x04 | tribe | nation id: Greeks 5, Turks 8 |
| 0x08 | leader_flags | `FILE_LEADER_*` bits; 0 for normal play (see below) |
| 0x0c | gov | |
| 0x10 | city_name_index | |
| 0x14 | name[200] | UTF-16 leader name |
| 0xdc | is_human | **4 = human, 0 = computer. Multiplayer needs at least 2 human slots** |
| 0xe0 | handicap | |
| 0xe4 | team_color | u8 |
| 0xe8 | difficulty | |

`FILE_LEADER_*` bits:

| Bit | Flag |
|---|---|
| 0x1 | UNIT_AI_OFF |
| 0x2 | PROD_AI_OFF |
| 0x4 | LOCK_TRANSPORT |
| 0x8 | CAN_TRANSPORT_CIV |
| 0x10 | IGNORE_POPCAP |
| 0x20 | ASSIMILATE_IMMED |
| 0x40 | COMBAT_AI_OFF |
| 0x80 | CAN_TRANSPORT_MIL |
| 0x100 | CAN_TRANSPORT_SCT |
| 0x200 | NO_CITY_DEFEAT |
| 0x400 | COOP_SOLO |

The `0x26` chunk holds starting techs. A count of 0 gives a clean Ancient Age start.

## Map `0x02`
The map is W×H tiles, with "coarse" cells of 4×4 tiles.

| Chunk | Content |
|---|---|
| `0x51` | map style string, e.g. `Dirty` |
| `0x58` / `0x10` | 4 bytes per coarse cell (byte 2 non-zero = not buildable) |
| `0x44` / `0x12` | u16 per tile: `0x10` water, `0x20` coastal water, `0x02` river |
| `0x59` | (H+1)×(W+1) float32 vertex heights |
| `0x5b` | engine cache, **must be zeros**; a copy of `0x63` crashes in `CoordInfo::add_geometry` |
| `0x63` / `0x65` | u16 per coarse cell: `0x2` mountain, `0x100` forest, `0x11` river, `0x20` land near shore, `0x308d`/`0x3089`/`0x3009` coast and water classes |
| `0x68` | zeros |
| `0x45` | mountain stamps: `(cy*256 + cx, template_id, n_cells)` with 16 fixed templates (`generator/tools/mtn_templates.json`) |
| `0x5c` | rivers: `0x5d` count, then per river `0x5e` point count and `0x5f` (x, y) points in coarse units |
| `0x49` | unused here |

## Objects
- `0x04` goods (resources) and `0x03` goody boxes hold 520-byte records. Each starts with a UTF-16 name, and the last 8 bytes are the position.
- **Positions are world units of ¾ tile × 256, i.e. `tile × 192`.** The same unit applies to the header start
  positions. Using `tile × 256` misplaces everything and crashes `Good::init` on large maps.

## Engine limits
- **Maps must be square.** A rectangle crashes in `TileSet::convert_land_tex_to_linear`, so pad with sea.
- **512×512 works; 640×640 crashes** in `Terrain::init`.
- **Slopes must be gentle.** Steep vertex heights make "must build on land" errors everywhere.
- **Coast cells are unbuildable:** cells with the coast class in `0x63` or beach bits refuse buildings. Keep the coast
  class off cells that are mostly land.
- A Small City needs about 7×7 tiles of free, flat land.

## Scenario scripts (`.bhs`)
- The game loads `<name>.bhs` next to `<name>.scx`, but only if header `scenario_flags` bit 0 is set.
- **Line endings must be CRLF.** With LF the whole file parses as one comment line and silently does nothing.
- The encoding is Windows-1252. Fold characters outside it (ş, ğ, ı) to ASCII.
- Useful calls: `create_building_near`, `rename_city`, `find_city_with_num`, `find_city_id`,
  `object_position_x/y`, `world_x_size`, `num_cities`, `city_exists`, `set_timer`/`timer_expired`,
  `declare_war`, `popup_dialog`, `victory`, `defeat`. String inequality is written `!(a == b)`.
- See `generator/tools/scriptgen.py` for a complete working script with nearest-place naming and rename-on-capture.

## Debugging crashes
Windows Error Reporting keeps the crash dumps. `rise.pdb` ships in the game's `sbl\` folder, and dbghelp symbolises
the faulting address against it (`generator/tools/sym.py <rva>`). That is how each crash above was traced to its
cause.
