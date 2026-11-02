from datetime import datetime
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shop.models import InventoryStatus

SMASH_SPRITES_CATALOG: list[dict[str, str]] = [
    {"name": "Balle Smash", "url": "/items/item_list29.png"},
    {"name": "Trophée aide", "url": "/items/item_img01.png"},
    {"name": "Poké Ball", "url": "/items/item_img02.png"},
    {"name": "Master Ball", "url": "/items/item_img03.png"},
    {"name": "Marteau en or", "url": "/items/item_list44.png"},
    {"name": "Marteau", "url": "/items/item_list08.png"},
    {"name": "Bob-omb", "url": "/items/item_list11.png"},
    {"name": "Super étoile", "url": "/items/item_list37.png"},
    {"name": "Étoile Warp", "url": "/items/item_list38.png"},
    {"name": "Super champi", "url": "/items/item_list03.png"},
    {"name": "Champi poison", "url": "/items/item_list36.png"},
    {"name": "Fleur de feu", "url": "/items/item_list48.png"},
    {"name": "Carapace à épines", "url": "/items/item_list17.png"},
    {"name": "Carapace verte", "url": "/items/item_list52.png"},
    {"name": "Bill Balle", "url": "/items/item_list42.png"},
    {"name": "Éclair", "url": "/items/item_list41.png"},
    {"name": "Peau de banane", "url": "/items/item_list59.png"},
    {"name": "Bloc POW", "url": "/items/item_list63.png"},
    {"name": "Super feuille", "url": "/items/item_list25.png"},
    {"name": "Barre de feu", "url": "/items/item_list46.png"},
    {"name": "Batte de base-ball", "url": "/items/item_list43.png"},
    {"name": "Épée laser", "url": "/items/item_list06.png"},
    {"name": "Bâton étoile", "url": "/items/item_list07.png"},
    {"name": "Faux de la Mort", "url": "/items/item_img13.png"},
    {"name": "Fer létal", "url": "/items/item_img04.png"},
    {"name": "Bâton", "url": "/items/item_img05.png"},
    {"name": "Sceptre de Lip", "url": "/items/item_list45.png"},
    {"name": "Massue minerai", "url": "/items/item_list47.png"},
    {"name": "Pistolaser", "url": "/items/item_list10.png"},
    {"name": "Nintendo Scope", "url": "/items/item_list09.png"},
    {"name": "Flingue rageur", "url": "/items/item_img12.png"},
    {"name": "Pistobanane", "url": "/items/item_img08.png"},
    {"name": "Steel Diver", "url": "/items/item_list50.png"},
    {"name": "Foreuse", "url": "/items/item_list21.png"},
    {"name": "Jarre magique", "url": "/items/item_list49.png"},
    {"name": "Bombinet", "url": "/items/item_img06.png"},
    {"name": "Fausse balle Smash", "url": "/items/item_img07.png"},
    {"name": "Bombe à détection", "url": "/items/item_list51.png"},
    {"name": "Bombe gluante", "url": "/items/item_list54.png"},
    {"name": "Bombe intelligente", "url": "/items/item_list55.png"},
    {"name": "Bombe X", "url": "/items/item_list12.png"},
    {"name": "Bombe Hocotate", "url": "/items/item_list13.png"},
    {"name": "Tête Brûlée", "url": "/items/item_list14.png"},
    {"name": "Trou noir", "url": "/items/item_img11.png"},
    {"name": "Super anneau étoile", "url": "/items/item_img10.png"},
    {"name": "Balle diabolique", "url": "/items/item_img16.png"},
    {"name": "Bumper", "url": "/items/item_list16.png"},
    {"name": "Congélo", "url": "/items/item_list53.png"},
    {"name": "Mr. Saturn", "url": "/items/item_list15.png"},
    {"name": "Noix Mojo", "url": "/items/item_list56.png"},
    {"name": "Boule fumée", "url": "/items/item_list57.png"},
    {"name": "Piège", "url": "/items/item_list58.png"},
    {"name": "Unira", "url": "/items/item_list60.png"},
    {"name": "Ballon de foot", "url": "/items/item_list61.png"},
    {"name": "Missile teigneux", "url": "/items/item_list62.png"},
    {"name": "Boomerang", "url": "/items/item_list64.png"},
    {"name": "Scarabée", "url": "/items/item_list18.png"},
    {"name": "Cocotte", "url": "/items/item_list19.png"},
    {"name": "Ruche", "url": "/items/item_list20.png"},
    {"name": "Œil-qui-tue", "url": "/items/item_list65.png"},
    {"name": "Boss Galaga", "url": "/items/item_list22.png"},
    {"name": "Chronomètre", "url": "/items/item_list05.png"},
    {"name": "Caisse de métal", "url": "/items/item_list39.png"},
    {"name": "Masque de lapin", "url": "/items/item_list04.png"},
    {"name": "Curry extrafort", "url": "/items/item_list40.png"},
    {"name": "Badge Franklin", "url": "/items/item_list23.png"},
    {"name": "Attaque en vrille", "url": "/items/item_list24.png"},
    {"name": "Bouclier dorsal", "url": "/items/item_list66.png"},
    {"name": "Ceinture-fusée", "url": "/items/item_list67.png"},
    {"name": "Drapeau spécial", "url": "/items/item_list68.png"},
    {"name": "Maxi-tomate", "url": "/items/item_list02.png"},
    {"name": "Réceptacle de cœur", "url": "/items/item_list34.png"},
    {"name": "Fée en bouteille", "url": "/items/item_list35.png"},
    {"name": "Pousse apaisante", "url": "/items/item_img15.png"},
    {"name": "Champ de soin", "url": "/items/item_img14.png"},
    {"name": "Nourriture", "url": "/items/item_list33.png"},
    {"name": "Morceaux de Dragoon", "url": "/items/item_list01.png"},
    {"name": "Morceaux de la genèse", "url": "/items/item_list30.png"},
    {"name": "Champinocif ambulant", "url": "/items/item_img09.png"},
    {"name": "Caisse explosive", "url": "/items/item_list31.png"},
    {"name": "Sac de sable", "url": "/items/item_list32.png"},
    {"name": "Caisse", "url": "/items/item_list26.png"},
    {"name": "Caisse roulante", "url": "/items/item_list69.png"},
    {"name": "Tonneau", "url": "/items/item_list27.png"},
    {"name": "Capsule", "url": "/items/item_list28.png"},
    {"name": "Ballon surprise", "url": "/items/item_list70.png"},
    {"name": "Herbe", "url": "/items/item_list71.png"},
]

SMASH_ITEM_IMAGES: dict[str, str] = {
    "trophee aide": "/items/item_img01.png",
    "poke ball": "/items/item_img02.png",
    "pokeball": "/items/item_img02.png",
    "master ball": "/items/item_img03.png",
    "fer letal": "/items/item_img04.png",
    "baton": "/items/item_img05.png",
    "bombinet": "/items/item_img06.png",
    "fausse balle smash": "/items/item_img07.png",
    "pistobanane": "/items/item_img08.png",
    "champinocif ambulant": "/items/item_img09.png",
    "super anneau etoile": "/items/item_img10.png",
    "trou noir": "/items/item_img11.png",
    "flingue rageur": "/items/item_img12.png",
    "faux de la mort": "/items/item_img13.png",
    "champ de soin": "/items/item_img14.png",
    "pousse apaisante": "/items/item_img15.png",
    "balle diabolique": "/items/item_img16.png",
    "morceaux de dragoon": "/items/item_list01.png",
    "maxi-tomate": "/items/item_list02.png",
    "super champi": "/items/item_list03.png",
    "champignon": "/items/item_list03.png",
    "masque de lapin": "/items/item_list04.png",
    "chronometre": "/items/item_list05.png",
    "epee laser": "/items/item_list06.png",
    "baton etoile": "/items/item_list07.png",
    "marteau": "/items/item_list08.png",
    "nintendo scope": "/items/item_list09.png",
    "pistolaser": "/items/item_list10.png",
    "bob-omb": "/items/item_list11.png",
    "bombe x": "/items/item_list12.png",
    "bombe hocotate": "/items/item_list13.png",
    "tete brulee": "/items/item_list14.png",
    "mr. saturn": "/items/item_list15.png",
    "bumper": "/items/item_list16.png",
    "carapace a epines": "/items/item_list17.png",
    "scarabee": "/items/item_list18.png",
    "cocotte": "/items/item_list19.png",
    "ruche": "/items/item_list20.png",
    "foreuse": "/items/item_list21.png",
    "boss galaga": "/items/item_list22.png",
    "badge franklin": "/items/item_list23.png",
    "attaque en vrille": "/items/item_list24.png",
    "super feuille": "/items/item_list25.png",
    "caisse": "/items/item_list26.png",
    "tonneau": "/items/item_list27.png",
    "capsule": "/items/item_list28.png",
    "balle smash": "/items/item_list29.png",
    "morceaux de la genese": "/items/item_list30.png",
    "caisse explosive": "/items/item_list31.png",
    "sac de sable": "/items/item_list32.png",
    "nourriture": "/items/item_list33.png",
    "receptacle de coeur": "/items/item_list34.png",
    "fee en bouteille": "/items/item_list35.png",
    "champi poison": "/items/item_list36.png",
    "super etoile": "/items/item_list37.png",
    "etoile": "/items/item_list37.png",
    "etoile warp": "/items/item_list38.png",
    "caisse de metal": "/items/item_list39.png",
    "curry extrafort": "/items/item_list40.png",
    "eclair": "/items/item_list41.png",
    "bill balle": "/items/item_list42.png",
    "batte de base-ball": "/items/item_list43.png",
    "marteau en or": "/items/item_list44.png",
    "marteau dore": "/items/item_list44.png",
    "sceptre de lip": "/items/item_list45.png",
    "barre de feu": "/items/item_list46.png",
    "massue minerai": "/items/item_list47.png",
    "fleur de feu": "/items/item_list48.png",
    "jarre magique": "/items/item_list49.png",
    "steel diver": "/items/item_list50.png",
    "bombe a detection": "/items/item_list51.png",
    "carapace verte": "/items/item_list52.png",
    "congelo": "/items/item_list53.png",
    "bombe gluante": "/items/item_list54.png",
    "bombe intelligente": "/items/item_list55.png",
    "noix mojo": "/items/item_list56.png",
    "boule fumee": "/items/item_list57.png",
    "piege": "/items/item_list58.png",
    "peau de banane": "/items/item_list59.png",
    "unira": "/items/item_list60.png",
    "ballon de foot": "/items/item_list61.png",
    "missile teigneux": "/items/item_list62.png",
    "bloc pow": "/items/item_list63.png",
    "boomerang": "/items/item_list64.png",
    "oeil-qui-tue": "/items/item_list65.png",
    "bouclier dorsal": "/items/item_list66.png",
    "ceinture-fusee": "/items/item_list67.png",
    "drapeau special": "/items/item_list68.png",
    "caisse roulante": "/items/item_list69.png",
    "ballon surprise": "/items/item_list70.png",
    "herbe": "/items/item_list71.png",
}


def _normalize_item_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name.lower().replace("œ", "oe").strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def resolve_gage_image(name: str, custom_url: str | None = None) -> str:
    if custom_url:
        return custom_url
    key = _normalize_item_name(name)
    if key in SMASH_ITEM_IMAGES:
        return SMASH_ITEM_IMAGES[key]
    for k, url in SMASH_ITEM_IMAGES.items():
        if k in key or key in k:
            return url
    return "/items/item_list29.png"


class GageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    price: int = Field(ge=0, le=100_000, description="Prix en Tilt (0 = Gratuit)")
    reward: int = Field(default=50, ge=0, le=100_000, description="Gain en Tilt si le gage est respecté")
    image_url: str | None = Field(default=None, max_length=255)
    is_available: bool = True


class GageUpdate(BaseModel):
    """Seuls les champs fournis sont modifiés."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    price: int | None = Field(default=None, ge=0, le=100_000)
    reward: int | None = Field(default=None, ge=0, le=100_000)
    image_url: str | None = Field(default=None, max_length=255)
    is_available: bool | None = None
    is_archived: bool | None = None


class GageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: int
    reward: int = 50
    image_url: str | None = None
    is_available: bool
    is_archived: bool

    @model_validator(mode="after")
    def _fill_default_image(self) -> "GageRead":
        self.image_url = resolve_gage_image(self.name, self.image_url)
        return self


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gage: GageRead
    status: InventoryStatus
    purchase_price: int
    purchased_at: datetime
    used_at: datetime | None
