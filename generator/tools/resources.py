"""Real-world resource sites: (lat, lon, RoN resource name). Fish/whales are generated along coasts."""

RARE = [
    # Greece
    (37.82, 22.66, 'Wine'),        # Nemea
    (40.63, 22.07, 'Wine'),        # Naousa
    (37.05, 22.00, 'Olive Oil'),   # Kalamata
    (38.50, 22.40, 'Olive Oil'),   # Amfissa
    (35.20, 24.90, 'Olive Oil'),   # Crete
    (39.20, 26.30, 'Olive Oil'),   # Lesbos
    (38.05, 23.87, 'Marble'),      # Penteli
    (37.05, 25.15, 'Marble'),      # Paros
    (37.72, 24.03, 'Silver'),      # Laurion
    (39.45, 22.20, 'Horses'),      # Thessaly
    (36.70, 24.40, 'Sulphur'),     # Milos
    (36.66, 24.52, 'Obsidian'),    # Milos
    (39.30, 22.60, 'Cotton'),      # Thessaly
    (41.15, 24.90, 'Tobacco'),     # Xanthi
    (38.55, 22.60, 'Aluminum'),    # Parnassos bauxite
    (40.50, 21.68, 'Coal'),        # Ptolemaida lignite
    (40.25, 21.95, 'Spice'),       # Kozani saffron
    (38.48, 22.50, 'Relics'),      # Delphi
    (37.64, 21.63, 'Relics'),      # Olympia
    (39.80, 20.90, 'Wool'),        # Epirus
    # Turkey
    (38.60, 34.85, 'Wine'),        # Cappadocia
    (40.62, 27.10, 'Wine'),        # Sarkoy
    (39.40, 26.90, 'Olive Oil'),   # Ayvalik / Edremit
    (37.80, 27.60, 'Olive Oil'),   # Aydin
    (36.95, 30.80, 'Citrus'),      # Antalya
    (36.85, 34.90, 'Citrus'),      # Mersin
    (36.95, 35.55, 'Cotton'),      # Cukurova
    (37.60, 27.45, 'Cotton'),      # Soke
    (36.85, 39.00, 'Cotton'),      # Harran
    (41.50, 35.90, 'Tobacco'),     # Bafra
    (38.75, 33.40, 'Salt'),        # Tuz Golu
    (41.20, 41.60, 'Copper'),      # Murgul
    (38.27, 39.76, 'Copper'),      # Ergani
    (40.45, 39.50, 'Silver'),      # Gumushane
    (41.45, 31.80, 'Coal'),        # Zonguldak
    (38.65, 34.45, 'Horses'),      # Cappadocia "land of beautiful horses"
    (39.90, 32.60, 'Wool'),        # Angora
    (41.25, 32.70, 'Spice'),       # Safranbolu saffron
    (40.15, 29.10, 'Silk'),        # Bursa
    (38.70, 29.40, 'Dye'),         # Usak carpets
    (38.65, 42.25, 'Obsidian'),    # Nemrut volcano
    (40.60, 27.60, 'Marble'),      # Marmara Island
    (38.75, 30.60, 'Marble'),      # Afyon
    (37.42, 31.85, 'Aluminum'),    # Seydisehir
    (39.70, 37.00, 'Gypsum'),      # Sivas
    (36.10, 32.80, 'Bananas'),     # Anamur
    (37.94, 27.34, 'Relics'),      # Ephesus
    (39.96, 26.24, 'Relics'),      # Troy
    (37.22, 38.92, 'Relics'),      # Gobekli Tepe
    (40.69, 39.66, 'Relics'),      # Sumela
    (40.51, 43.57, 'Relics'),      # Ani
    (39.70, 44.20, 'Sulphur'),     # Ararat
    # Balkans
    (41.95, 25.40, 'Tobacco'),     # Haskovo
    (41.35, 21.55, 'Tobacco'),     # Prilep
    (41.52, 23.39, 'Wine'),        # Melnik
    (41.45, 21.95, 'Wine'),        # Tikves
    (42.70, 24.07, 'Copper'),      # Chelopech
    (42.90, 20.85, 'Silver'),      # Trepca
    (42.60, 23.03, 'Coal'),        # Pernik
    (42.60, 21.00, 'Coal'),        # Kosovo lignite
    (41.60, 20.60, 'Wool'),        # Albanian highlands
    (42.62, 25.40, 'Spice'),       # Valley of the Roses
    (41.12, 20.80, 'Relics'),      # Ohrid
    (39.75, 20.02, 'Relics'),      # Butrint
    # Cyprus
    (35.09, 32.89, 'Copper'),      # Skouriotissa
    (35.20, 33.00, 'Citrus'),      # Morphou
    (34.75, 32.95, 'Wine'),        # Commandaria
    # Neighbours
    (36.20, 37.30, 'Spice'),       # Aleppo
    (35.95, 39.10, 'Cotton'),      # Raqqa
    (36.30, 43.30, 'Relics'),      # Nineveh
    (41.80, 42.80, 'Furs'),        # Caucasus
    (34.90, 36.00, 'Dye'),         # Phoenician coast
    (44.08, 22.10, 'Copper'),      # Bor
    (44.42, 21.94, 'Copper'),      # Majdanpek
    (45.23, 25.94, 'Salt'),        # Slanic Prahova
    (45.05, 26.35, 'Wine'),        # Dealu Mare
    (44.60, 20.20, 'Horses'),      # Sumadija
    (45.30, 33.80, 'Salt'),        # Crimean salt lakes
    (44.70, 34.00, 'Wine'),        # Crimea (Massandra)
]

# oil fields (each spawns a small cluster)
OIL = [
    (40.65, 19.65, 2),   # Patos-Marinza, Albania
    (40.85, 24.50, 1),   # Prinos (offshore)
    (37.65, 21.25, 1),   # Katakolo (offshore)
    (39.60, 20.40, 1),   # Epirus seeps
    (43.40, 24.40, 1),   # Dolni Dabnik
    (44.95, 25.95, 3),   # Ploiesti
    (44.75, 24.95, 1),   # Arges
    (37.90, 41.10, 2),   # Batman
    (37.80, 38.40, 1),   # Adiyaman
    (41.40, 27.30, 1),   # Hamitabat (Thrace)
    (41.95, 31.20, 1),   # Black Sea (offshore)
    (36.60, 35.90, 1),   # Iskenderun gulf (offshore)
    (35.47, 44.39, 2),   # Kirkuk
    (35.80, 43.20, 1),   # Qayyarah
    (36.70, 42.00, 1),   # Rumeilan
    (35.30, 40.30, 1),   # Deir ez-Zor
]

# ancient sites -> RoN ruins (goody boxes)
RUINS = [
    (37.73, 22.76),  # Mycenae
    (35.30, 25.16),  # Knossos
    (40.48, 22.32),  # Vergina
    (39.55, 20.79),  # Dodona
    (40.76, 22.52),  # Pella
    (39.13, 27.18),  # Pergamon
    (37.92, 29.12),  # Hierapolis
    (37.71, 28.72),  # Aphrodisias
    (37.67, 32.83),  # Catalhoyuk
    (37.98, 38.74),  # Mount Nemrut
    (40.02, 34.62),  # Hattusa
    (41.55, 21.97),  # Stobi
    (38.49, 28.04),  # Sardis
    (36.20, 36.16),  # Antioch
    (42.15, 24.75),  # Philippopolis theatre
    (44.74, 21.21),  # Viminacium
    (44.55, 28.77),  # Histria
    (45.62, 23.31),  # Sarmizegetusa
    (44.61, 33.49),  # Chersonesos
]
