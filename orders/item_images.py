from pathlib import Path

EMAIL_ASSETS_DIR = Path(__file__).resolve().parent / "email_assets"

# Mirrors TPGamesPlus_FE/src/utils/itemImages.js
ITEM_IMAGES = {
    "Sword of Valor": "item_3d_sword_valor.jpg",
    "Shield of Aegis": "item_3d_shield_aegis.jpg",
    "Potion of Healing": "item_3d_potion_healing.jpg",
    "Mystic Wand": "item_3d_mystic_wand.jpg",
    "Ring of Invisibility": "item_3d_ring_invisibility.jpg",
    "Helmet of Courage": "item_3d_helmet_courage.jpg",
    "Armor of Fortitude": "item_3d_armor_fortitude.jpg",
    "Boots of Speed": "item_3d_boots_speed.jpg",
    "Gloves of Dexterity": "item_3d_gloves_dexterity.jpg",
    "Cape of Shadows": "item_3d_cape_shadows.jpg",
}

LOGO_PATH = EMAIL_ASSETS_DIR / "Tamatem_Plus_Logo_White.png"
LOGO_CID = "tamatem-plus-logo"
ITEM_CID = "order-item-image"


def item_image_path(title):
    filename = ITEM_IMAGES.get(title)
    if not filename:
        return None
    path = EMAIL_ASSETS_DIR / "items" / filename
    return path if path.is_file() else None
