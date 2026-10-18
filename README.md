# Greco-Turkish War: a real-geography map for Rise of Nations: Extended Edition

A two-player skirmish map, Greeks vs Turks, built from real geodata. It covers Greece, Turkey to 40°E
(Trabzon–Malatya), Cyprus, Albania, North Macedonia, Bulgaria and south Serbia. Every city you found takes
the name of the nearest real place, in your own language.

![Map overview](docs/images/overview.png)

## Features
- **Real map:** coastline, islands, lakes, and open Bosphorus and Dardanelles straits, all from Natural Earth 10m data.
  The real elevation is smoothed so that cities and buildings fit.
- **30 real rivers:** Evros/Meriç, Axios/Vardar, Strymonas, Haliacmon, Pineios, Sakarya, Kızılırmak, Yeşilırmak,
  Gediz, Büyük Menderes, Seyhan, Ceyhan, Euphrates, Tigris…
- **Mountains on the real ranges** (Pindus, Taurus, Pontic…), with small mineable outcrops next to most historic towns.
- **Forests and ground colour** from NASA Blue Marble imagery, thinned out so there's room to build.
- **398 resources at real sites:** marble at Penteli, wine, olive oil, silver, copper, silk, oil fields, fish and
  whales. There are also 15 ancient-ruin goody boxes.
- **City names:** a scenario script renames each new city to the nearest of 276 real places, in the founder's
  language:

  | | Greek player | Turkish player |
  |---|---|---|
  | Athens | Athina | Atina |
  | Thessaloniki | Thessaloniki | Selanik |
  | Istanbul | Konstantinoupoli | Istanbul |
  | Izmir | Smyrni | Izmir |

  Big historic cities claim their name from further away. A captured city takes the captor's name for it.

![City names](docs/images/city_names.png)

## Screenshots
| Capitals: Athens start, with Penteli marble next door | Frontier: Thessaloniki start, with rivers on both sides |
|---|---|
| ![Athina in game](docs/images/ingame_athina.jpg) | ![Thessaloniki in game](docs/images/ingame_thessaloniki.jpg) |

## Scenarios
| Scenario | Greeks start | Turks start | Feel |
|---|---|---|---|
| `GrecoTurkish_Capitals` | Athina | Ankara | long build-up, capitals far apart |
| `GrecoTurkish_Frontier` | Thessaloniki | Bursa | faster clash around Thrace and the Marmara |

Each side starts in the Ancient Age with a Small City, 5 Citizens and a Scout. The game runs up to the
Information Age. You win by taking every enemy city.

The leaders are Eleftherios Venizelos (Greeks, slot 1) and Mustafa Kemal Atatürk (Turks, slot 2).

## Install
1. Download `GrecoTurkish-v1.0.zip` from [Releases](../../releases), or use the `scenarios/` folder of this repo.
2. Find the game folder: Steam → Rise of Nations → ⚙ → Manage → **Browse local files**.
3. Extract so that you get:
   ```
   Rise of Nations\scenario\Custom\GrecoTurkish_Capitals\GrecoTurkish_Capitals.scx (+ .sce, .bhs)
   Rise of Nations\scenario\Custom\GrecoTurkish_Frontier\GrecoTurkish_Frontier.scx (+ .sce, .bhs)
   ```

## Play with a friend (multiplayer)
1. Both players install the scenarios as above. The files must be identical on both PCs.
2. Both players update the game in Steam, so you run the same version.
3. The host goes to **Multiplayer → create a game → Game Rules: Scenario**, then picks `GrecoTurkish_Frontier` or `GrecoTurkish_Capitals`.
4. The friend joins. Slot 1 is the Greeks, slot 2 is the Turks.
5. Start the game. Within about 2 seconds the capitals get their real names.

## Solo
Use **Solo Game → Load a Scenario**. Both slots are set to Human, because multiplayer refuses scenarios with fewer
than 2 human players. Solo therefore gives you control of both nations, with no AI opponent. Click a unit of the
other nation to switch sides.

## Rebuild or tweak the map
The `generator/` folder holds the full pipeline. It needs Python 3 (tested with 3.14) on Windows with the game installed, because
it reads a few stock scenario records as templates.

![Pipeline](docs/images/pipeline.png)

```bat
cd generator
pip install -r requirements.txt
python fetch_data.py            :: ~30 MB of open geodata into generator\data
python tools\build.py           :: writes generator\out\GrecoTurkish_*\
python tools\build.py --install :: ...and copies them into the game's scenario\Custom folder
```
If Steam put the game somewhere else, set `RON_DIR` first, e.g. `set RON_DIR=D:\SteamLibrary\steamapps\common\Rise of Nations`.

The build is deterministic: a fresh clone with freshly downloaded data reproduces the shipped `.scx` files byte for byte.

| To change | Edit |
|---|---|
| City names, coordinates, which cities are "major", start cities | `tools/cities.py` |
| Resource sites, oil fields, ruins | `tools/resources.py` |
| Which rivers are drawn | `RIVERS` / `HAND_RIVERS` in `tools/features.py` |
| Map extent | `LON0, LON1, LAT0, LAT1` in `tools/geo.py` |
| Map size | `python tools\build.py --W 384` (512 works; 640 crashes the game) |
| Coast width, mountain density, leaders, nations | constants at the top of `tools/build.py` |

Other tools:
- `tools/metrics.py 512`: playability report (city spots, wood and metal near each town).
- `tools/doc_images.py`: regenerates the images in `docs/images`.
- `tools/make_test.py`: builds a `zR_test` scenario with extra test cities for checking the naming script.
- `tools/ronscx.py`: generic reader and writer for RoN `.scx`/`.sce` chunk files.
- `tools/pdbtypes.py`: looks up struct layouts in the game's own debug symbols (`sbl\rise.pdb`).

## How it works
RoN scenarios are gzip-compressed trees of binary chunks. The generator:
1. rasterises the geodata onto a Mercator grid at about 3.5 km per tile;
2. writes the terrain layers (water and coast flags, vertex heights, textures, mountain stamps, forests and rivers);
3. places resources and ruins;
4. pads the map to a square, which the engine requires;
5. writes a `.bhs` script that places the starting cities and handles the naming.

The format notes, including the engine limits that crash the game if you get them wrong, are in
[docs/FORMAT.md](docs/FORMAT.md).

## Status
- Tested in RoN: Extended Edition 1.20: both scenarios load, the capitals spawn and get their real names, and resources
  sit at their real locations.
- Not yet tested: a real two-PC multiplayer game, renaming on capture, and the end-of-game check. Please open an issue
  if something breaks.

## Credits
- Coastlines, lakes and rivers: [Natural Earth](https://www.naturalearthdata.com/) (public domain).
- Elevation: [Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) by Mapzen on AWS Open Data. They are
  derived from SRTM, GMTED2010, ETOPO1 and other sources ([attribution](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)).
- Imagery: NASA Blue Marble Next Generation via [NASA GIBS](https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api).

Rise of Nations is a trademark of Microsoft. This is a fan-made map, not affiliated with or endorsed by
Microsoft or Big Huge Games. The repo contains no game files; the generator reads its templates from your own install.
