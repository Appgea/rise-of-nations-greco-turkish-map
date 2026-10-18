# Greco-Turkish War: a real-geography map for Rise of Nations: Extended Edition

A two-player map, Greeks vs Turks, built from real geodata. It covers:
- Greece and the Aegean islands
- western and central Turkey, as far as Ankara, Konya and Antalya
- Cyprus
- the Balkans north to the Danube and beyond (Albania, North Macedonia, Bulgaria, Serbia, southern Romania)
- western Crimea

Every city you found takes the name of the nearest real place, in your own language.

![Map overview](docs/images/overview.png)

## Features
- **Real map, made for play:**
  - 512×512 tiles at about 2.6 km per tile.
  - Coastline and islands come from Natural Earth 10m data, with the Bosphorus, Dardanelles and Gulf of Corinth open.
  - Greece's coasts and islands are widened by about 5 km, so Greece has room to grow.
  - Narrow inlets are filled in, and there are no inland lakes.
- **Smooth, stock-style coasts:** sand beaches blend into dirt and grass the way they do on the game's own maps
  (see [How it works](#how-it-works)).
- **9 major rivers:** Danube, Evros/Meriç, Axios/Vardar, Strymonas, Haliacmon, Sakarya, Kızılırmak, Gediz and
  Büyük Menderes.
- **Mountains on the real ranges** (Pindus, Rhodopes, Balkan, Taurus…), plus mineable outcrops near the towns.
- **Organic forests** placed from NASA Blue Marble imagery.
- **Playable starts:** every start city and every big historic city (38 in all) gets:
  - a clear ring for the city and its farms;
  - a wood about 8–12 tiles out;
  - a mineable rock on another side.
- **516 resources at real sites:** Penteli marble, Ploiești oil, Bor copper, Crimean salt, wine, olive oil, silk,
  fish, whales and more. There are also 17 ancient-ruin goody boxes.
- **City names:** a scenario script renames each new city to the nearest of 291 real places, in the founder's language:

  | | Greek player | Turkish player |
  |---|---|---|
  | Athens | Athina | Atina |
  | Thessaloniki | Thessaloniki | Selanik |
  | Istanbul | Konstantinoupoli | Istanbul |
  | Izmir | Smyrni | Izmir |
  | Bucharest | Voukouresti | Bükres |

  Big historic cities claim their name from further away. A captured city takes the captor's name for it.

![City names](docs/images/city_names.png)

## Screenshots
**Frontier vs AI:** the Greek start at Thessaloniki, with farms, a woodcutter's camp, a mineable rock and the beach.
![Thessaloniki in game](docs/images/ingame_thessaloniki.jpg)

**Capitals:** the Athens start, with a mineable rock to the north, woods on three sides and Penteli marble.
![Athina in game](docs/images/ingame_athina.jpg)

**Coast rendering:** before and after matching the stock-map texture rules.
![Coast before and after](docs/images/coast_before_after.jpg)

## Scenarios
| Scenario | Greeks start | Turks start | Use |
|---|---|---|---|
| `GrecoTurkish_Frontier` | Thessaloniki | Bursa | multiplayer; faster clash around Thrace and the Marmara |
| `GrecoTurkish_Capitals` | Athina | Ankara | multiplayer; long build-up |
| `GrecoTurkish_Frontier_vsAI` | Thessaloniki | Bursa | solo: you play the Greeks, the computer the Turks |
| `GrecoTurkish_Capitals_vsAI` | Athina | Ankara | solo against the computer |

Each side starts in the Ancient Age with a Small City, 5 Citizens and a Scout. The game runs up to the
Information Age. You win by taking every enemy city.

The leaders are Eleftherios Venizelos (Greeks, slot 1) and Mustafa Kemal Atatürk (Turks, slot 2). The computer
plays on Moderate; change `AI_DIFFICULTY` in `generator/tools/build.py` and rebuild for another level.

## Install
1. Download `GrecoTurkish-v1.1.zip` from [Releases](../../releases), or use the `scenarios/` folder of this repo.
2. Find the game folder: Steam → Rise of Nations → ⚙ → Manage → **Browse local files**.
3. Extract the zip so that you get:
   ```
   Rise of Nations\scenario\Custom\GrecoTurkish_Frontier\GrecoTurkish_Frontier.scx (+ .sce, .bhs)
   Rise of Nations\scenario\Custom\GrecoTurkish_Capitals\...
   Rise of Nations\scenario\Custom\GrecoTurkish_Frontier_vsAI\...
   Rise of Nations\scenario\Custom\GrecoTurkish_Capitals_vsAI\...
   ```

## Play against the computer
Go to **Solo Game → Load a Scenario**, open `GrecoTurkish_Frontier_vsAI` (or `_Capitals_vsAI`) and press Load.

## Play with a friend
You play online through Steam; you don't need to be on the same network.
1. Both players install the scenarios. The files must be identical on both PCs.
2. Both players update the game in Steam, so you run the same version.
3. The host goes to **Multiplayer → Online → create a game → Game Rules: Scenario**, then picks
   `GrecoTurkish_Frontier` or `GrecoTurkish_Capitals`.
4. The friend joins from the lobby browser, or the host invites them through Steam (Shift+Tab → friend → Invite to game).
   Slot 1 is the Greeks, slot 2 is the Turks.
5. Start the game. Within about 2 seconds the capitals get their real names.

The multiplayer scenarios have both slots set to Human, because the game refuses multiplayer scenarios with fewer
than 2 humans. If you load one in Solo, you control both nations.

## Rebuild or tweak the map
The `generator/` folder holds the full pipeline. It needs Python 3 (tested with 3.14) on Windows with the game
installed, because it reads a few stock scenario records as templates.

![Pipeline](docs/images/pipeline.png)

```bat
cd generator
pip install -r requirements.txt
python fetch_data.py            :: ~30 MB of open geodata into generator\data (follows the map extent)
python tools\build.py           :: writes the 4 scenarios to generator\out\
python tools\build.py --install :: ...and copies them into the game's scenario\Custom folder
```
If Steam put the game somewhere else, set `RON_DIR` first, e.g. `set RON_DIR=D:\SteamLibrary\steamapps\common\Rise of Nations`.

The build is deterministic: the same code and data always produce the same `.scx` files.

| To change | Edit |
|---|---|
| City names, coordinates, which cities are "major", start cities | `tools/cities.py` |
| Resource sites, oil fields, ruins | `tools/resources.py` |
| Which rivers are drawn | `RIVERS` / `HAND_RIVERS` in `tools/features.py` |
| Map extent (the north edge is computed so the map stays square) | `LON0, LON1, LAT0` in `tools/geo.py` |
| How much Greece is widened | `GROW_BOX`, `GROW_TILES` in `tools/terrain.py` |
| Start kits (clear ring, wood and metal distances) | `start_kit` in `tools/features.py` |
| Mountain density, AI difficulty, leaders, nations | constants at the top of `tools/build.py` |

Other tools:
- `tools/metrics.py 512` and `tools/greece_metric.py 512`: playability reports (city spots, wood and metal near each town).
- `tools/doc_images.py`: regenerates the map images in `docs/images`.
- `tools/make_test.py`: builds a `zR_test` scenario with extra test cities for checking the naming script.
- `tools/ronscx.py`: generic reader and writer for RoN `.scx`/`.sce` chunk files.
- `tools/pdbtypes.py`: looks up struct layouts in the game's own debug symbols (`sbl\rise.pdb`).

## How it works
RoN scenarios are gzip-compressed trees of binary chunks. The generator:
1. rasterises the geodata onto a square Mercator grid;
2. widens Greece and fills small inlets;
3. writes the terrain layers: water and coast flags, vertex heights with stock-like beaches, textures, mountain
   stamps, forests and rivers;
4. places resources, ruins and the start kits;
5. writes a `.bhs` script that places the starting cities and handles the naming.

The coasts look smooth because the textures follow the rule every stock map follows:
- the 4 ground textures form a cycle, and touching cells are never opposite on it;
- the land ring along the coast is "dirt", which blends into the beach.

Breaking this rule gives cell-shaped sand blocks or a crash.

The format notes, including the engine limits that crash the game if you get them wrong, are in
[docs/FORMAT.md](docs/FORMAT.md).

## Status
- Tested in RoN: Extended Edition 1.20:
  - both scenarios load and play in solo;
  - Frontier vs AI loads and plays against the computer;
  - the capitals spawn, get their real names and have wood, metal and farm room.
- Not yet tested: a real two-PC multiplayer game, renaming on capture, and the end-of-game check. Please open an issue
  if something breaks.

## Credits
- Coastlines and rivers: [Natural Earth](https://www.naturalearthdata.com/) (public domain).
- Elevation: [Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) by Mapzen on AWS Open Data. They are
  derived from SRTM, GMTED2010, ETOPO1 and other sources ([attribution](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)).
- Imagery: NASA Blue Marble Next Generation via [NASA GIBS](https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api).

Rise of Nations is a trademark of Microsoft. This is a fan-made map, not affiliated with or endorsed by
Microsoft or Big Huge Games. The repo contains no game files; the generator reads its templates from your own install.
