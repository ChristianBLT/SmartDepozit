def clean_filename(name: str) -> str:
    return "".join(x for x in name if x.isalnum() or x in "._- ")


def detect_basic_color_from_rgb(r: float, g: float, b: float) -> str:
    brightness = (r + g + b) / 3
    if brightness < 45:
        return "Negru"
    if brightness > 215:
        return "Alb"
    if r > 150 and g < 100 and b < 100:
        return "Roșu"
    if b > 150 and r < 120:
        return "Albastru"
    if g > 150 and r < 120:
        return "Verde"
    if abs(r - g) < 20 and abs(g - b) < 20:
        return "Gri"
    return "Multicolor"


def guess_tip_ro_from_labels_en(labels_en: list[str]) -> str:
    if any(x in labels_en for x in ["sunglasses", "eyewear", "glasses"]):
        return "Ochelari"
    if any(x in labels_en for x in ["sneakers", "shoe", "footwear", "boot"]):
        return "Pantof"
    if any(x in labels_en for x in ["jacket", "coat", "outerwear"]):
        return "Geacă"
    if any(x in labels_en for x in ["hat", "cap", "fedora"]):
        return "Pălărie"
    if any(x in labels_en for x in ["t-shirt", "shirt", "top"]):
        return "Tricou"
    if any(x in labels_en for x in ["pants", "trousers", "jeans"]):
        return "Pantaloni"
    return "Articol"


def extract_size_from_text(text: str) -> str:
    for m in ["XS", "S", "M", "L", "XL", "XXL"]:
        ml = m.lower()
        if f"size {ml}" in text or f" {ml} " in text:
            return m
    return "Standard"


def is_keyword_match(value: str, keywords: list[str]) -> bool:
    return any(k in value for k in keywords)

