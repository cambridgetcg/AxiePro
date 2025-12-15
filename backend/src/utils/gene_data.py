"""
Axie gene binary mappings.

Gene structure (256 bits total):
- Bits 0-3: Reserved
- Bits 4-8: Class (5 bits)
- Bits 9-12: Reserved
- Bits 13-17: Region (5 bits)
- Bits 18-21: Tag (4 bits)
- Bits 22-25: Body Skin (4 bits)
- Bits 26-29: Reserved
- Bits 30-33: Xmas (4 bits)
- Bits 34-37: Reserved
- Bits 38-41: Pattern (4 bits)
- Bits 42-59: Color (18 bits: 6 per RGB component)
- Bits 60-63: Reserved
- Bits 64-95: Eyes (32 bits)
- Bits 96-127: Mouth (32 bits)
- Bits 128-159: Ears (32 bits)
- Bits 160-191: Horn (32 bits)
- Bits 192-223: Back (32 bits)
- Bits 224-255: Tail (32 bits)

Each body part (32 bits):
- D gene: bits 2-5 (skin) + bits 6-11 (class + part)
- R1 gene: bits 12-15 (skin) + bits 16-21 (class + part)
- R2 gene: bits 22-25 (skin) + bits 26-31 (class + part)
"""

# Class binary mappings (5 bits)
CLASS_GENE_MAP = {
    "0000": "beast",
    "0001": "bug",
    "0010": "bird",
    "0011": "plant",
    "0100": "aquatic",
    "0101": "reptile",
    "1000": "mech",
    "1001": "dawn",
    "1010": "dusk",
}

# Region mappings
REGION_GENE_MAP = {
    "00000": "global",
    "00001": "japan",
}

# Tag mappings
TAG_GENE_MAP = {
    "0000": "normal",
    "0001": "origin",
    "0010": "meo1",
    "0011": "meo2",
}

# Body skin mappings
BODY_SKIN_MAP = {
    "0000": "normal",
    "0001": "frosty",
}

# Pattern mappings (visual appearance)
PATTERN_GENE_MAP = {
    "000000": "pattern_0",
    "000001": "pattern_1",
    "000010": "pattern_2",
    "000011": "pattern_3",
    "000100": "pattern_4",
    "000101": "pattern_5",
}

# Part skin (mystic, etc.)
PART_SKIN_MAP = {
    "0000": "normal",
    "0001": "mystic",
    "0010": "xmas1",
    "0011": "xmas2",
    "0100": "bionic",
    "0101": "summer1",
    "0110": "summer2",
    "0111": "strawberry",
    "1000": "shiny",
}

# Class to 4-bit binary for part genes
PART_CLASS_MAP = {
    "0000": "beast",
    "0001": "bug",
    "0010": "bird",
    "0011": "plant",
    "0100": "aquatic",
    "0101": "reptile",
}

# ============================================================================
# BODY PART MAPPINGS
# Format: {binary_value: (part_id, part_name)}
# The class is determined separately from the class bits
# ============================================================================

# EYES PARTS (6 bits for part within class)
EYES_PARTS = {
    "beast": {
        "000000": ("eyes-chubby", "Chubby"),
        "000001": ("eyes-chubby", "Chubby"),  # Duplicate for coverage
        "000010": ("eyes-little-peas", "Little Peas"),
        "000011": ("eyes-little-peas", "Little Peas"),
        "000100": ("eyes-puppy", "Puppy"),
        "000101": ("eyes-puppy", "Puppy"),
        "001000": ("eyes-zeal", "Zeal"),
        "001001": ("eyes-zeal", "Zeal"),
        "001010": ("eyes-gerbil", "Gerbil"),
        "001011": ("eyes-gerbil", "Gerbil"),
        "001100": ("eyes-scar", "Scar"),
        "001101": ("eyes-scar", "Scar"),
    },
    "bug": {
        "000000": ("eyes-bookworm", "Bookworm"),
        "000010": ("eyes-neo", "Neo"),
        "000100": ("eyes-nerdy", "Nerdy"),
        "001000": ("eyes-kotaro", "Kotaro"),
        "001010": ("eyes-papi", "Papi"),
        "001100": ("eyes-yen", "Yen"),
    },
    "bird": {
        "000000": ("eyes-mavis", "Mavis"),
        "000010": ("eyes-lucas", "Lucas"),
        "000100": ("eyes-little-owl", "Little Owl"),
        "001000": ("eyes-robin", "Robin"),
        "001010": ("eyes-sky-mavis", "Sky Mavis"),
        "001100": ("eyes-peacock", "Peacock"),
    },
    "plant": {
        "000000": ("eyes-papi", "Papi"),
        "000010": ("eyes-confused", "Confused"),
        "000100": ("eyes-blossom", "Blossom"),
        "001000": ("eyes-cucumber-slice", "Cucumber Slice"),
        "001010": ("eyes-meta", "Meta"),
        "001100": ("eyes-watermelon", "Watermelon"),
    },
    "aquatic": {
        "000000": ("eyes-gero", "Gero"),
        "000010": ("eyes-sleepless", "Sleepless"),
        "000100": ("eyes-clear", "Clear"),
        "001000": ("eyes-telescope", "Telescope"),
        "001010": ("eyes-antenna", "Antenna"),
        "001100": ("eyes-goldfish", "Goldfish"),
    },
    "reptile": {
        "000000": ("eyes-topaz", "Topaz"),
        "000010": ("eyes-scar", "Scar"),
        "000100": ("eyes-tricky", "Tricky"),
        "001000": ("eyes-dokuganryu", "Dokuganryu"),
        "001010": ("eyes-gecko", "Gecko"),
        "001100": ("eyes-crimson-gecko", "Crimson Gecko"),
    },
}

# EARS PARTS
EARS_PARTS = {
    "beast": {
        "000000": ("ears-nut-cracker", "Nut Cracker"),
        "000010": ("ears-nyan", "Nyan"),
        "000100": ("ears-innocent-lamb", "Innocent Lamb"),
        "001000": ("ears-zen", "Zen"),
        "001010": ("ears-puppy", "Puppy"),
        "001100": ("ears-belieber", "Belieber"),
    },
    "bug": {
        "000000": ("ears-larva", "Larva"),
        "000010": ("ears-ant", "Ant"),
        "000100": ("ears-beetle-spike", "Beetle Spike"),
        "001000": ("ears-ear-breathing", "Ear Breathing"),
        "001010": ("ears-leaf-bug", "Leaf Bug"),
        "001100": ("ears-tassels", "Tassels"),
    },
    "bird": {
        "000000": ("ears-pink-cheek", "Pink Cheek"),
        "000010": ("ears-early-bird", "Early Bird"),
        "000100": ("ears-owl", "Owl"),
        "001000": ("ears-curly", "Curly"),
        "001010": ("ears-peace-maker", "Peace Maker"),
        "001100": ("ears-risky-bird", "Risky Bird"),
    },
    "plant": {
        "000000": ("ears-leafy", "Leafy"),
        "000010": ("ears-clover", "Clover"),
        "000100": ("ears-rosa", "Rosa"),
        "001000": ("ears-sakura", "Sakura"),
        "001010": ("ears-hollow", "Hollow"),
        "001100": ("ears-lotus", "Lotus"),
    },
    "aquatic": {
        "000000": ("ears-nimo", "Nimo"),
        "000010": ("ears-bubblemaker", "Bubblemaker"),
        "000100": ("ears-seaslug", "Seaslug"),
        "001000": ("ears-gill", "Gill"),
        "001010": ("ears-inkling", "Inkling"),
        "001100": ("ears-tiny-fan", "Tiny Fan"),
    },
    "reptile": {
        "000000": ("ears-small-frill", "Small Frill"),
        "000010": ("ears-curved-spine", "Curved Spine"),
        "000100": ("ears-friezard", "Friezard"),
        "001000": ("ears-swirl", "Swirl"),
        "001010": ("ears-sidebarb", "Sidebarb"),
        "001100": ("ears-pogona", "Pogona"),
    },
}

# MOUTH PARTS
MOUTH_PARTS = {
    "beast": {
        "000000": ("mouth-nut-cracker", "Nut Cracker"),
        "000010": ("mouth-goda", "Goda"),
        "000100": ("mouth-axie-kiss", "Axie Kiss"),
        "001000": ("mouth-confident", "Confident"),
        "001010": ("mouth-imp", "Imp"),
        "001100": ("mouth-merry", "Merry"),
    },
    "bug": {
        "000000": ("mouth-mosquito", "Mosquito"),
        "000010": ("mouth-pincer", "Pincer"),
        "000100": ("mouth-cute-bunny", "Cute Bunny"),
        "001000": ("mouth-square-teeth", "Square Teeth"),
        "001010": ("mouth-herbivore", "Herbivore"),
        "001100": ("mouth-dango", "Dango"),
    },
    "bird": {
        "000000": ("mouth-doubletalk", "Doubletalk"),
        "000010": ("mouth-peace-maker", "Peace Maker"),
        "000100": ("mouth-hungry-bird", "Hungry Bird"),
        "001000": ("mouth-little-owl", "Little Owl"),
        "001010": ("mouth-mr-squeaky", "Mr. Squeaky"),
        "001100": ("mouth-risky-bird", "Risky Bird"),
    },
    "plant": {
        "000000": ("mouth-zigzag", "Zigzag"),
        "000010": ("mouth-herbivore", "Herbivore"),
        "000100": ("mouth-serious", "Serious"),
        "001000": ("mouth-humorless", "Humorless"),
        "001010": ("mouth-rudolph", "Rudolph"),
        "001100": ("mouth-silence-whisper", "Silence Whisper"),
    },
    "aquatic": {
        "000000": ("mouth-lam", "Lam"),
        "000010": ("mouth-catfish", "Catfish"),
        "000100": ("mouth-risky-fish", "Risky Fish"),
        "001000": ("mouth-piranha", "Piranha"),
        "001010": ("mouth-hungry-bird", "Hungry Bird"),
        "001100": ("mouth-toothless-bite", "Toothless Bite"),
    },
    "reptile": {
        "000000": ("mouth-kotaro", "Kotaro"),
        "000010": ("mouth-tiny-turtle", "Tiny Turtle"),
        "000100": ("mouth-razor-bite", "Razor Bite"),
        "001000": ("mouth-bumpy", "Bumpy"),
        "001010": ("mouth-dagger", "Dagger"),
        "001100": ("mouth-venom-bite", "Venom Bite"),
    },
}

# HORN PARTS
HORN_PARTS = {
    "beast": {
        "000000": ("horn-little-branch", "Little Branch"),
        "000010": ("horn-imp", "Imp"),
        "000100": ("horn-merry", "Merry"),
        "001000": ("horn-pocky", "Pocky"),
        "001010": ("horn-dual-blade", "Dual Blade"),
        "001100": ("horn-arco", "Arco"),
    },
    "bug": {
        "000000": ("horn-lagging", "Lagging"),
        "000010": ("horn-caterpillars", "Caterpillars"),
        "000100": ("horn-antenna", "Antenna"),
        "001000": ("horn-pliers", "Pliers"),
        "001010": ("horn-parasite", "Parasite"),
        "001100": ("horn-leaf-bug", "Leaf Bug"),
    },
    "bird": {
        "000000": ("horn-eggshell", "Eggshell"),
        "000010": ("horn-cuckoo", "Cuckoo"),
        "000100": ("horn-trump", "Trump"),
        "001000": ("horn-feather-spear", "Feather Spear"),
        "001010": ("horn-kestrel", "Kestrel"),
        "001100": ("horn-wing-horn", "Wing Horn"),
    },
    "plant": {
        "000000": ("horn-beech", "Beech"),
        "000010": ("horn-bamboo-shoot", "Bamboo Shoot"),
        "000100": ("horn-rose-bud", "Rose Bud"),
        "001000": ("horn-cactus", "Cactus"),
        "001010": ("horn-strawberry-shortcake", "Strawberry Shortcake"),
        "001100": ("horn-watermelon", "Watermelon"),
    },
    "aquatic": {
        "000000": ("horn-babylonia", "Babylonia"),
        "000010": ("horn-teal-shell", "Teal Shell"),
        "000100": ("horn-clamshell", "Clamshell"),
        "001000": ("horn-anemone", "Anemone"),
        "001010": ("horn-shoal-star", "Shoal Star"),
        "001100": ("horn-oranda", "Oranda"),
    },
    "reptile": {
        "000000": ("horn-unko", "Unko"),
        "000010": ("horn-scaly-spear", "Scaly Spear"),
        "000100": ("horn-cerastes", "Cerastes"),
        "001000": ("horn-scaly-spoon", "Scaly Spoon"),
        "001010": ("horn-incisor", "Incisor"),
        "001100": ("horn-bumpy", "Bumpy"),
    },
}

# BACK PARTS
BACK_PARTS = {
    "beast": {
        "000000": ("back-ronin", "Ronin"),
        "000010": ("back-hero", "Hero"),
        "000100": ("back-jaguar", "Jaguar"),
        "001000": ("back-risky-beast", "Risky Beast"),
        "001010": ("back-hamaya", "Hamaya"),
        "001100": ("back-hasagi", "Hasagi"),
    },
    "bug": {
        "000000": ("back-snail-shell", "Snail Shell"),
        "000010": ("back-garish-worm", "Garish Worm"),
        "000100": ("back-buzz-buzz", "Buzz Buzz"),
        "001000": ("back-sandal", "Sandal"),
        "001010": ("back-scarab", "Scarab"),
        "001100": ("back-spiky-wing", "Spiky Wing"),
    },
    "bird": {
        "000000": ("back-balloon", "Balloon"),
        "000010": ("back-raven", "Raven"),
        "000100": ("back-pigeon-post", "Pigeon Post"),
        "001000": ("back-kingfisher", "Kingfisher"),
        "001010": ("back-tri-feather", "Tri Feather"),
        "001100": ("back-cupid", "Cupid"),
    },
    "plant": {
        "000000": ("back-turnip", "Turnip"),
        "000010": ("back-bidens", "Bidens"),
        "000100": ("back-watering-can", "Watering Can"),
        "001000": ("back-shiitake", "Shiitake"),
        "001010": ("back-mint", "Mint"),
        "001100": ("back-pumpkin", "Pumpkin"),
    },
    "aquatic": {
        "000000": ("back-hermit", "Hermit"),
        "000010": ("back-goldfish", "Goldfish"),
        "000100": ("back-anemone", "Anemone"),
        "001000": ("back-sponge", "Sponge"),
        "001010": ("back-perch", "Perch"),
        "001100": ("back-blue-moon", "Blue Moon"),
    },
    "reptile": {
        "000000": ("back-bone-sail", "Bone Sail"),
        "000010": ("back-tri-spikes", "Tri Spikes"),
        "000100": ("back-green-thorns", "Green Thorns"),
        "001000": ("back-indian-star", "Indian Star"),
        "001010": ("back-red-ear", "Red Ear"),
        "001100": ("back-croc", "Croc"),
    },
}

# TAIL PARTS
TAIL_PARTS = {
    "beast": {
        "000000": ("tail-cottontail", "Cottontail"),
        "000010": ("tail-hare", "Hare"),
        "000100": ("tail-nut-cracker", "Nut Cracker"),
        "001000": ("tail-gerbil", "Gerbil"),
        "001010": ("tail-shiba", "Shiba"),
        "001100": ("tail-rice", "Rice"),
    },
    "bug": {
        "000000": ("tail-gravel-ant", "Gravel Ant"),
        "000010": ("tail-pupae", "Pupae"),
        "000100": ("tail-thorny-caterpillar", "Thorny Caterpillar"),
        "001000": ("tail-fish-snack", "Fish Snack"),
        "001010": ("tail-twin-tail", "Twin Tail"),
        "001100": ("tail-maki", "Maki"),
    },
    "bird": {
        "000000": ("tail-swallow", "Swallow"),
        "000010": ("tail-feather-fan", "Feather Fan"),
        "000100": ("tail-the-last-one", "The Last One"),
        "001000": ("tail-cloud", "Cloud"),
        "001010": ("tail-granmas-fan", "Granma's Fan"),
        "001100": ("tail-post-fight", "Post Fight"),
    },
    "plant": {
        "000000": ("tail-yam", "Yam"),
        "000010": ("tail-carrot", "Carrot"),
        "000100": ("tail-cattail", "Cattail"),
        "001000": ("tail-hatsune", "Hatsune"),
        "001010": ("tail-potato-leaf", "Potato Leaf"),
        "001100": ("tail-hot-butt", "Hot Butt"),
    },
    "aquatic": {
        "000000": ("tail-nimo", "Nimo"),
        "000010": ("tail-tadpole", "Tadpole"),
        "000100": ("tail-ranchu", "Ranchu"),
        "001000": ("tail-navaga", "Navaga"),
        "001010": ("tail-koi", "Koi"),
        "001100": ("tail-shrimp", "Shrimp"),
    },
    "reptile": {
        "000000": ("tail-wall-gecko", "Wall Gecko"),
        "000010": ("tail-iguana", "Iguana"),
        "000100": ("tail-tiny-dino", "Tiny Dino"),
        "001000": ("tail-snake-jar", "Snake Jar"),
        "001010": ("tail-gila", "Gila"),
        "001100": ("tail-grass-snake", "Grass Snake"),
    },
}

# Collect all parts by type
PARTS_BY_TYPE = {
    "eyes": EYES_PARTS,
    "ears": EARS_PARTS,
    "mouth": MOUTH_PARTS,
    "horn": HORN_PARTS,
    "back": BACK_PARTS,
    "tail": TAIL_PARTS,
}

# Class stats bonuses
CLASS_STATS = {
    "beast": {"hp": 31, "speed": 35, "skill": 31, "morale": 43},
    "bug": {"hp": 35, "speed": 31, "skill": 35, "morale": 39},
    "bird": {"hp": 27, "speed": 43, "skill": 35, "morale": 35},
    "plant": {"hp": 43, "speed": 31, "skill": 31, "morale": 35},
    "aquatic": {"hp": 39, "speed": 39, "skill": 35, "morale": 27},
    "reptile": {"hp": 39, "speed": 35, "skill": 31, "morale": 35},
    "mech": {"hp": 31, "speed": 39, "skill": 43, "morale": 27},
    "dawn": {"hp": 35, "speed": 35, "skill": 39, "morale": 31},
    "dusk": {"hp": 43, "speed": 27, "skill": 35, "morale": 35},
}

# Part class stat bonuses (per matching part)
PART_STAT_BONUSES = {
    "beast": {"speed": 1, "morale": 3},
    "bug": {"hp": 1, "morale": 3},
    "bird": {"speed": 3, "morale": 1},
    "plant": {"hp": 3, "morale": 1},
    "aquatic": {"speed": 3, "hp": 1},
    "reptile": {"hp": 3, "speed": 1},
}

# Secret class combinations
SECRET_CLASS_COMBINATIONS = {
    # (class1, class2): result_class
    ("beast", "bug"): "mech",
    ("bug", "beast"): "mech",
    ("aquatic", "bird"): "dawn",
    ("bird", "aquatic"): "dawn",
    ("plant", "reptile"): "dusk",
    ("reptile", "plant"): "dusk",
}
