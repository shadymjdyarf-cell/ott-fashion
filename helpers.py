from functools import wraps
from flask import redirect, session, render_template


OCCASIONS = {
    "gym": "Gym \U0001F3CB",
    "sports": "Sports \u26BD",
    "school": "School \U0001F4DA",
    "casual": "Casual \U0001F455",
    "occasion": "Occasion \U0001F389",
    "trend": "Trend \U0001F525",
    "vintage": "Vintage \U0001F570",
    "halloween": "Halloween \U0001F383",
}


def apology(message, code=400):
    return render_template("apology.html", message=message, code=code), code


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def get_rates():
    import urllib.request
    import json
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        with urllib.request.urlopen(url, timeout=3) as r:
            data = json.loads(r.read())
            return {"KRW": data["rates"]["KRW"], "EGP": data["rates"]["EGP"]}
    except Exception:
        return {"KRW": 1350, "EGP": 48}


def get_rates():
    import urllib.request
    import json
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        with urllib.request.urlopen(url, timeout=3) as r:
            data = json.loads(r.read())
            return {"KRW": data["rates"]["KRW"], "EGP": data["rates"]["EGP"]}
    except Exception:
        return {"KRW": 1350, "EGP": 48}


# Color harmony groups
COLOR_GROUPS = {
    "neutral": ["white", "black", "gray", "grey", "beige", "cream", "ivory", "tan", "nude", "أبيض", "أسود", "رمادي", "بيج"],
    "warm":    ["red", "orange", "yellow", "brown", "coral", "peach", "أحمر", "برتقالي", "أصفر", "بني"],
    "cool":    ["blue", "green", "purple", "teal", "navy", "mint", "أزرق", "أخضر", "بنفسجي", "كحلي"],
    "pink":    ["pink", "rose", "magenta", "وردي", "زهري"],
}

# Style keywords to detect in item names
STYLE_KEYWORDS = {
    "hoodie": "streetwear", "sweatshirt": "streetwear", "cargo": "streetwear",
    "jogger": "streetwear", "sneaker": "streetwear", "cap": "streetwear",
    "blazer": "classic", "suit": "classic", "oxford": "classic", "loafer": "classic",
    "turtleneck": "classic", "trench": "classic",
    "graphic tee": "kpop", "oversized": "kpop", "cropped": "kpop",
    "skirt": "kpop", "pleated": "kpop",
    "linen": "boho", "floral": "boho", "flowy": "boho", "maxi": "boho",
    "minimal": "minimal", "plain": "minimal", "basic": "minimal",
    "vintage": "vintage", "retro": "vintage", "denim": "vintage",
}


def _detect_color_group(color):
    if not color:
        return None
    c = color.lower().strip()
    for group, colors in COLOR_GROUPS.items():
        if any(col in c for col in colors):
            return group
    return None


def _detect_style(name):
    if not name:
        return None
    n = name.lower()
    for kw, style in STYLE_KEYWORDS.items():
        if kw in n:
            return style
    return None


def _classify_item(item):
    """Classify item into: top, bottom, shoes, outer, accessory"""
    name = (item.get("name") or "").lower()
    slots = {
        "top":       ["shirt", "tee", "t-shirt", "blouse", "top", "hoodie", "sweater", "sweatshirt", "tank", "polo", "قميص", "تيشيرت", "بلوزة", "هودي"],
        "bottom":    ["jeans", "pants", "skirt", "shorts", "trouser", "jogger", "cargo", "بنطلون", "جيبة", "شورت"],
        "shoes":     ["shoe", "sneaker", "boot", "sandal", "heel", "loafer", "حذاء", "جزمة", "كوتشي", "سنيكرز"],
        "outer":     ["jacket", "coat", "cardigan", "blazer", "trench", "جاكيت", "بالطو"],
        "accessory": ["bag", "hat", "cap", "scarf", "belt", "watch", "glasses", "necklace", "ring", "earrings", "شنطة", "كاب", "ساعة", "نظارة", "سلسلة"],
    }
    for slot, kws in slots.items():
        if any(k in name for k in kws):
            return slot
    return "other"


def suggest_outfit(items, occasion, weather=None, mood=None):
    """Smart outfit suggestion with reasons"""
    import random

    if not items:
        return [], "Add a few pieces to your wardrobe first - then I can style you!", []

    pool = [i for i in items if i["occasion"] == occasion]
    if len(pool) < 3:
        pool = items

    slots = {"top": [], "bottom": [], "shoes": [], "outer": [], "accessory": [], "other": []}
    for item in pool:
        slot = _classify_item(item)
        slots[slot].append(item)
        item["_color_group"] = _detect_color_group(item.get("color", ""))
        item["_style"] = _detect_style(item.get("name", ""))

    chosen = []
    reasons = []

    # TOP
    if slots["top"]:
        neutrals = [i for i in slots["top"] if i["_color_group"] == "neutral"]
        if neutrals and random.random() < 0.7:
            top = random.choice(neutrals)
            reasons.append(f"Chose {top['name']} as a neutral base - easy to match")
        else:
            top = random.choice(slots["top"])
            reasons.append(f"Picked {top['name']} as your main top")
        chosen.append(top)

    # BOTTOM
    if slots["bottom"] and occasion not in ["gym"]:
        top_color = chosen[0]["_color_group"] if chosen else None
        matched = [i for i in slots["bottom"] if i["_color_group"] != top_color or not i["_color_group"]]
        bottom = random.choice(matched) if matched else random.choice(slots["bottom"])
        reasons.append(f"Added {bottom['name']} - contrasts well with the top")
        chosen.append(bottom)

    # SHOES
    if slots["shoes"]:
        shoes = random.choice(slots["shoes"])
        reasons.append(f"{shoes['name']} - comfortable choice")
        chosen.append(shoes)

    # OUTER
    if slots["outer"] and (weather == "cold" or occasion in ["occasion", "casual"]):
        outer = random.choice(slots["outer"])
        reasons.append(f"{outer['name']} for layering")
        chosen.append(outer)

    # ACCESSORY
    if slots["accessory"] and random.random() < 0.8:
        acc = random.choice(slots["accessory"])
        reasons.append(f"{acc['name']} - finishing touch")
        chosen.append(acc)

    if not chosen:
        chosen = pool[:3]
        reasons.append("Selected from what is available")

    # Tip
    mood_tips = {
        "confident": "Stand tall - this outfit is made for walking into the room.",
        "chill": "Relaxed vibes only - comfort meets style.",
        "bold": "Bold choice - own it.",
        "soft": "Soft tones, soft energy - beautiful.",
        "playful": "Fun and fresh - perfect for a good mood.",
    }
    weather_tips = {
        "hot": "Breathable fabrics - keep it light today.",
        "cold": "Layer up - warmth plus style.",
    }
    if mood and mood in mood_tips:
        tip = mood_tips[mood]
    elif weather and weather in weather_tips:
        tip = weather_tips[weather]
    else:
        general_tips = [
            "Keep it to 3 colors max for a clean look.",
            "Fitting matters more than the price tag.",
            "Add one statement piece - the rest stays simple.",
            "Confidence is the best accessory.",
        ]
        tip = random.choice(general_tips)

    return chosen, tip, reasons

CONFIDENCE_MESSAGES = [
    "Confidence is not in the clothes - it is in the one wearing them",
    "The style that feels right, is the right style",
    "There is no wrong body - only wrong clothes",
    "You are better than any trend",
    "Wear what makes you happy, not what pleases others",
    "Comfort matters more than brand",
    "Every piece you wear tells a story",
    "Beauty starts from within",
    "Being you - that is your best look",
    "There is no perfect size - only perfect confidence",
    "Your smile is your best accessory",
    "Style is not money - it is personality",
    "Real beauty comes from how you carry yourself",
    "You are not a copy of anyone - that is your beauty",
    "The right outfit is the one that feels like you",
]


def get_confidence():
    import random
    return random.choice(CONFIDENCE_MESSAGES)


def fetch_trends_from_rss(source="all"):
    """Fetch fashion trends from various RSS sources"""
    import urllib.request
    import re
    import html as html_lib

    all_feeds = {
        "vogue":      [("Vogue", "https://www.vogue.com/feed/rss")],
        "hypebeast":  [("Hypebeast", "https://hypebeast.com/feed")],
        "highsnobiety": [("Highsnobiety", "https://www.highsnobiety.com/feed/")],
        "korean":     [
            ("Koreaboo", "https://www.koreaboo.com/feed/"),
            ("Soompi", "https://www.soompi.com/feed"),
        ],
    }

    if source == "all":
        feeds = []
        for lst in all_feeds.values():
            feeds.extend(lst)
    elif source in all_feeds:
        feeds = all_feeds[source]
    else:
        feeds = all_feeds["korean"]

    keywords = [
        "fashion", "style", "trend", "runway", "korean", "korea",
        "aesthetic", "look", "outfit", "streetwear", "idol", "kpop",
        "seoul", "ulzzang", "wear", "clothing"
    ]

    results = []
    for name, url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode("utf-8", errors="ignore")
            items = re.findall(r"<item>(.*?)</item>", raw, re.DOTALL)
            if not items:
                items = re.findall(r"<entry>(.*?)</entry>", raw, re.DOTALL)
            for item in items[:10]:
                t_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item)
                if not t_match:
                    t_match = re.search(r"<title>(.*?)</title>", item)
                if not t_match:
                    continue
                title = t_match.group(1).strip()
                tl = title.lower()
                if not any(k in tl for k in keywords):
                    continue
                img = ""
                m = re.search(r'<media:content[^>]*url="([^"]+)"', item)
                if not m:
                    m = re.search(r'<media:thumbnail[^>]*url="([^"]+)"', item)
                if not m:
                    m = re.search(r'<enclosure[^>]*url="([^"]+)"[^>]*type="image', item)
                if not m:
                    m = re.search(r'<img[^>]*src="([^"]+)"', item)
                if m:
                    img = m.group(1)
                clean = re.sub(r"<.*?>", "", title).strip()
                clean = html_lib.unescape(clean)
                if 10 < len(clean) <= 80:
                    results.append({"title": clean, "image": img, "source": name})
        except Exception:
            continue
    return results[:20]


def get_seasonal_theme():
    from datetime import datetime
    month = datetime.now().month
    themes = {
        1:  ("Winter Cozy", "❄️", "#87CEEB"),
        2:  ("Valentine",   "💕", "#FF69B4"),
        3:  ("Spring",      "🌸", "#FFB6C1"),
        4:  ("Spring",      "🌸", "#FFB6C1"),
        5:  ("Summer",      "☀️", "#FFD700"),
        6:  ("Summer",      "☀️", "#FFD700"),
        7:  ("Summer Vibes", "🏖️", "#00CED1"),
        8:  ("Late Summer", "🌊", "#20B2AA"),
        9:  ("Pre-Fall",    "🍃", "#DAA520"),
        10: ("Halloween",   "🎃", "#FF6600"),
        11: ("Autumn",      "🍂", "#8B4513"),
        12: ("Christmas",   "🎄", "#DC143C"),
    }
    return themes.get(month, ("Default", "✨", "#E67E22"))


def get_seasonal_theme():
    from datetime import datetime
    month = datetime.now().month
    themes = {
        1:  ("Winter Cozy", "❄️", "#87CEEB"),
        2:  ("Valentine",   "💕", "#FF69B4"),
        3:  ("Spring",      "🌸", "#FFB6C1"),
        4:  ("Spring",      "🌸", "#FFB6C1"),
        5:  ("Summer",      "☀️", "#FFD700"),
        6:  ("Summer",      "☀️", "#FFD700"),
        7:  ("Summer Vibes", "🏖️", "#00CED1"),
        8:  ("Late Summer", "🌊", "#20B2AA"),
        9:  ("Pre-Fall",    "🍃", "#DAA520"),
        10: ("Halloween",   "🎃", "#FF6600"),
        11: ("Autumn",      "🍂", "#8B4513"),
        12: ("Christmas",   "🎄", "#DC143C"),
    }
    return themes.get(month, ("Default", "✨", "#E67E22"))


STYLES = {
    "kpop": "K-Pop",
    "oldmoney": "Old Money",
    "street": "Street",
    "minimal": "Minimal",
    "boho": "Boho",
    "classic": "Classic",
    "retro": "Retro",
    "korean": "Korean",
    "vintage": "Vintage",
}


def fetch_pexafy_images(query="fashion", count=20):
    import urllib.request
    import urllib.parse
    import json
    from config import PEXAFY_API_KEY

    try:
        url = "https://api.pexafy.com/v1/search?query=" + urllib.parse.quote(query) + "&per_page=" + str(count)
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": "Bearer " + PEXAFY_API_KEY,
                "Accept": "application/json",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        results = []
        items = data.get("results") or data.get("data") or data.get("images") or []
        for img in items:
            url_field = img.get("url") or img.get("image") or img.get("src") or ""
            if url_field:
                results.append({
                    "url": url_field,
                    "thumb": img.get("thumbnail") or img.get("preview") or url_field,
                    "alt": img.get("alt") or img.get("title") or "Fashion image",
                })
        return results
    except Exception as e:
        print("Pexafy error:", e)
        return []


# Track used image URLs globally
_USED_IMAGES = set()

# Unsplash Collections IDs (curated by humans - all fashion)
# These are real Unsplash collections for streetwear / fashion
KOREAN_FASHION_COLLECTIONS = [
    "8916698",      # Korean Street Style
    "3330448",      # Street Fashion
    "3178572",      # Fashion
    "1032546",      # Street Style
    "1431929",      # Fashion Photography
    "4788049",      # Korean aesthetic
    "6755446",      # Streetwear
]

# Rejection list - anything nature/food/objects
REJECT = [
    "food", "cake", "pizza", "coffee", "meal", "restaurant", "drink",
    "tree", "flower", "leaf", "plant", "garden", "forest", "nature",
    "mountain", "sky", "sunset", "ocean", "beach", "clouds", "landscape",
    "cat", "dog", "animal", "bird", "insect",
    "car", "bike", "bus", "train",
    "building", "architecture", "house", "interior", "room",
    "phone", "laptop", "computer", "book", "painting",
    "rack", "hanger", "mannequin", "closet", "shelf",
    "old man", "elderly", "grandfather", "grandmother",
    "still life", "flat lay", "product",
]

MUST_HAVE = [
    "man", "men", "guy", "boy", "male", "gentleman",
    "woman", "women", "girl", "female", "lady",
    "wearing", "wears", "worn", "wear",
    "outfit", "person", "people", "model", "portrait",
    "korean", "seoul", "asian", "korea",
    "street", "fashion",
]


def _is_valid(alt):
    if not alt:
        return False
    alt = alt.lower()
    if any(r in alt for r in REJECT):
        return False
    return any(m in alt for m in MUST_HAVE)


def fetch_fashion_images(query="fashion", count=20, page=1, randomize=False):
    """Fetch from Unsplash Collections - NO DUPLICATES"""
    import random
    import urllib.request
    import json
    from config import UNSPLASH_ACCESS_KEY

    results = []
    seen_this_call = set()  # dedup within this call
    tried = set()

    collections = KOREAN_FASHION_COLLECTIONS.copy()
    random.shuffle(collections)

    for coll_id in collections:
        if len(results) >= count:
            break
        if coll_id in tried:
            continue
        tried.add(coll_id)
        try:
            url = (
                "https://api.unsplash.com/collections/" + coll_id + "/photos?"
                + "per_page=" + str(min(count * 2, 30))
                + "&page=" + str(random.randint(1, 5))
            )
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": "Client-ID " + UNSPLASH_ACCESS_KEY,
                    "Accept-Version": "v1",
                }
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            for img in data:
                # Use image ID for unique check
                img_id = img.get("id", "")
                urls = img.get("urls", {})
                url_val = urls.get("small", "")

                # Skip if empty or already seen (global or local)
                if not url_val or not img_id:
                    continue
                if img_id in seen_this_call or url_val in _USED_IMAGES:
                    continue

                alt = img.get("alt_description") or ""
                seen_this_call.add(img_id)
                _USED_IMAGES.add(url_val)
                _USED_IMAGES.add(img_id)
                results.append({
                    "url": urls.get("regular", url_val),
                    "thumb": url_val,
                    "alt": alt or "Korean fashion",
                })
                if len(results) >= count:
                    break
        except Exception as e:
            print("Collection error:", e)
            continue

    return results[:count]
def fetch_unsplash_images(query="korean fashion", count=20, page=1):
    """Fetch fashion images from Unsplash API"""
    import urllib.request
    import urllib.parse
    import json
    from config import UNSPLASH_ACCESS_KEY

    try:
        url = (
            "https://api.unsplash.com/search/photos?"
            + "query=" + urllib.parse.quote(query)
            + "&per_page=" + str(count)
            + "&page=" + str(page)
            + "&orientation=portrait"
        )
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": "Client-ID " + UNSPLASH_ACCESS_KEY,
                "Accept-Version": "v1",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        results = []
        for img in data.get("results", []):
            urls = img.get("urls", {})
            results.append({
                "url": urls.get("regular", ""),
                "thumb": urls.get("small", ""),
                "alt": img.get("alt_description") or "Fashion inspiration",
                "author": img.get("user", {}).get("name", ""),
            })
        return results
    except Exception as e:
        print("Unsplash error:", e)
        return []


def fetch_pixabay_images(query="fashion", count=20, page=1, randomize=False):
    """Fetch images from Pixabay API with optional randomization"""
    import urllib.request
    import urllib.parse
    import json
    import random
    from config import PIXABAY_API_KEY

    try:
        if randomize:
            page = random.randint(1, 20)
        order = "latest" if randomize else "popular"
        url = (
            "https://pixabay.com/api/?"
            + "key=" + PIXABAY_API_KEY
            + "&q=" + urllib.parse.quote(query)
            + "&per_page=" + str(min(count, 200))
            + "&page=" + str(page)
            + "&image_type=photo"
            + "&orientation=vertical"
            + "&order=" + order
            + "&safesearch=true"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        results = []
        for img in data.get("hits", []):
            results.append({
                "url": img.get("largeImageURL", img.get("webformatURL", "")),
                "thumb": img.get("webformatURL", ""),
                "alt": img.get("tags", "Fashion image"),
            })
        return results
    except Exception as e:
        print("Pixabay error:", e)
        return []


# Curated queries - flat lays (no people), menswear, wardrobe, modest fashion
DIVERSITY_QUERIES = [
    "outfit flatlay clothes",
    "menswear style outfit",
    "wardrobe clothing rack",
    "shoes sneakers flatlay",
    "minimal outfit flatlay",
    "capsule wardrobe clothes",
    "folded clothes minimal",
    "clothing store rack",
    "mens fashion suit",
    "handbag accessories flatlay",
    "winter coat outfit",
    "summer outfit clothes flatlay",
]


def fetch_fashion_images(query="fashion", count=20, page=1, randomize=False):
    """Fetch diverse fashion images - flatlays + menswear + wardrobe"""
    import random

    # If query is generic, pick from diverse list
    generic_queries = ["fashion", "korean fashion", "korean street fashion"]
    if query in generic_queries or query == "":
        query = random.choice(DIVERSITY_QUERIES)
    else:
        # Improve specific queries
        improvements = {
            "korean fashion": "korean outfit flatlay",
            "korean street fashion": "korean street outfit",
            "casual street style": "casual outfit flatlay",
            "gym workout fitness": "gym clothes flatlay",
            "sportswear athlete": "sportswear clothes flatlay",
            "student school outfit": "school outfit clothes",
            "elegant evening outfit": "elegant outfit clothes",
            "trendy fashion": "trendy outfit flatlay",
            "vintage retro fashion": "vintage clothes flatlay",
            "halloween costume": "halloween outfit clothes",
        }
        query = improvements.get(query, query)

    # Try Unsplash
    imgs = fetch_unsplash_images(query, count, page)
    if imgs and len(imgs) >= 5:
        return imgs

    # Fallback to Pixabay
    pix = fetch_pixabay_images(query, count, page, randomize)
    if pix:
        return pix

    return imgs or []


def translate_text(text, target_lang="ar"):
    """Translate text using MyMemory free API"""
    if not text or target_lang == "en":
        return text
    import urllib.request
    import urllib.parse
    import json
    try:
        src = "en"
        if target_lang == "ar":
            target = "ar-EG"
        elif target_lang == "ko":
            target = "ko-KR"
        else:
            return text
        url = (
            "https://api.mymemory.translated.net/get?"
            + "q=" + urllib.parse.quote(text[:500])
            + "&langpair=" + src + "|" + target
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        result = data.get("responseData", {}).get("translatedText", text)
        return result if result else text
    except Exception:
        return text


# Seasonal emojis - changes based on month
SEASONAL_AVATARS = {
    1:  "❄️",   # Winter
    2:  "💕",   # Valentine
    3:  "🌸",   # Spring
    4:  "🌷",   # Spring
    5:  "☀️",   # Summer
    6:  "🏖️",  # Summer
    7:  "🌊",   # Summer
    8:  "🍉",   # Late summer
    9:  "🍃",   # Pre-fall
    10: "🎃",   # Halloween
    11: "🍂",   # Autumn
    12: "🎄",   # Christmas
}


def get_seasonal_avatar():
    from datetime import datetime
    month = datetime.now().month
    return SEASONAL_AVATARS.get(month, "😊")


EMOJI_AVATARS = [
    "🦊", "🐱", "🐼", "🦋", "🌸", "🌺",
    "⭐", "✨", "💫", "🌙", "☀️", "🌈",
    "🎨", "🎧", "📚", "🎮", "🍕", "🍦",
    "💜", "💚", "🧡", "❤️", "🖤", "🤍",
    "🐰", "🐨", "🐸", "🦁", "🐯", "🦄",
]


def get_seasonal_dicebear(username="user"):
    """Get DiceBear avatar with seasonal color palette + seasonal emoji overlay"""
    from datetime import datetime
    month = datetime.now().month

    # Season: (dicebear seed suffix, background colors, overlay emoji)
    seasons = {
        1:  ("winter",    "b6e3f4,c0aede,d1d4f9", "❄️"),
        2:  ("heart",     "ffd5dc,ffdfbf",         "💕"),
        3:  ("spring",    "ffdfbf,c0aede,d1d4f9", "🌸"),
        4:  ("flower",    "ffd5dc,d1d4f9,ffdfbf", "🌷"),
        5:  ("summer",    "ffdfbf,b6e3f4",         "☀️"),
        6:  ("sun",       "ffdfbf,ffd5dc",         "🌞"),
        7:  ("beach",     "b6e3f4,ffdfbf",         "🏖️"),
        8:  ("ocean",     "b6e3f4,c0aede",         "🌊"),
        9:  ("autumn",    "ffdfbf,d1d4f9",         "🍃"),
        10: ("halloween", "ffdfbf,c0aede",         "🎃"),
        11: ("autumn",    "ffdfbf,d1d4f9",         "🍂"),
        12: ("christmas", "ffdfbf,b6e3f4",         "🎄"),
    }

    seed_suffix, bg, emoji = seasons.get(month, ("default", "b6e3f4,c0aede,d1d4f9", "😊"))
    full_seed = f"{username}-{seed_suffix}"
    url = f"https://api.dicebear.com/7.x/thumbs/svg?seed={full_seed}&backgroundColor={bg}"
    return url, emoji


# DiceBear styles available for users to pick
DICEBEAR_STYLES = [
    {"id": "thumbs",      "name": "Thumbs"},
    {"id": "adventurer",  "name": "Adventurer"},
    {"id": "avataaars",   "name": "Avataaars"},
    {"id": "big-smile",   "name": "Big Smile"},
    {"id": "bottts",      "name": "Robot"},
    {"id": "croodles",    "name": "Croodles"},
    {"id": "fun-emoji",   "name": "Fun Emoji"},
    {"id": "lorelei",     "name": "Lorelei"},
    {"id": "micah",       "name": "Micah"},
    {"id": "miniavs",     "name": "Miniavs"},
    {"id": "notionists",  "name": "Notionists"},
    {"id": "open-peeps",  "name": "Open Peeps"},
    {"id": "personas",    "name": "Personas"},
    {"id": "pixel-art",   "name": "Pixel Art"},
]


def get_dicebear_url(style, username):
    """Generate DiceBear URL for specific style"""
    return f"https://api.dicebear.com/7.x/{style}/svg?seed={username}&backgroundColor=f5b041,e67e22,27ae60,1e8449"


# ============ DAILY QUOTES ============
DAILY_QUOTES = [
    {"en": "Style is a way to say who you are without having to speak.", "ar": "الستايل طريقة تقول بيها مين أنت من غير ما تتكلم.", "ko": "스타일은 말하지 않고도 자신을 표현하는 방법입니다."},
    {"en": "Confidence is the best outfit. Own it and rock it.", "ar": "الثقة أحلى لبس. امتلكها والبسها.", "ko": "자신감이 최고의 옷입니다."},
    {"en": "Fashion fades, style is eternal.", "ar": "الموضة بتعدي، الستايل بيفضل.", "ko": "패션은 사라지고 스타일은 영원합니다."},
    {"en": "You are never fully dressed without a smile.", "ar": "مش كامل لبسك من غير ضحكتك.", "ko": "미소 없이는 완전히 옷을 입은 것이 아닙니다."},
    {"en": "Elegance is not standing out, but being remembered.", "ar": "الأناقة مش إنك تبان، لكن إنك تفضل في الذاكرة.", "ko": "우아함은 눈에 띄는 것이 아니라 기억되는 것입니다."},
    {"en": "The best color you can wear is confidence.", "ar": "أحلى لون ممكن تلبسه هو الثقة.", "ko": "당신이 입을 수 있는 최고의 색은 자신감입니다."},
    {"en": "Style is knowing who you are and what you want to say.", "ar": "الستايل هو إنك تعرف مين أنت وعايز تقول إيه.", "ko": "스타일은 자신이 누구인지 아는 것입니다."},
]


def get_daily_quote(lang="en"):
    from datetime import datetime
    day = datetime.now().timetuple().tm_yday
    q = DAILY_QUOTES[day % len(DAILY_QUOTES)]
    return q.get(lang, q["en"])


# ============ ACHIEVEMENTS ============
ACHIEVEMENTS = {
    "first_item":    {"icon": "🌱", "name_en": "First Piece",      "name_ar": "أول قطعة",       "name_ko": "첫 아이템"},
    "ten_items":     {"icon": "👕", "name_en": "Wardrobe Starter", "name_ar": "بداية الخزانة",  "name_ko": "옷장 시작"},
    "fifty_items":   {"icon": "🏆", "name_en": "Fashion Guru",     "name_ar": "خبير موضة",      "name_ko": "패션 구루"},
    "first_outfit":  {"icon": "🎨", "name_en": "Stylist Rookie",   "name_ar": "مبتدئ التنسيق",  "name_ko": "스타일리스트 루키"},
    "ten_outfits":   {"icon": "✨", "name_en": "Style Master",     "name_ar": "أستاذ الستايل",  "name_ko": "스타일 마스터"},
    "first_wish":    {"icon": "💭", "name_en": "Dreamer",          "name_ar": "الحالم",         "name_ko": "꿈꾸는 자"},
    "ten_wishes":    {"icon": "💫", "name_en": "Big Dreamer",      "name_ar": "حالم كبير",      "name_ko": "큰 꿈"},
    "week_streak":   {"icon": "🔥", "name_en": "Week Warrior",     "name_ar": "محارب الأسبوع",  "name_ko": "주간 전사"},
    "korean_fan":    {"icon": "🇰🇷", "name_en": "K-Fashion Fan",   "name_ar": "معجب K-موضة",    "name_ko": "K-패션 팬"},
    "sharer":        {"icon": "📤", "name_en": "Sharer",           "name_ar": "المشارك",        "name_ko": "공유자"},
}


def check_achievements(user_id, db):
    """Check and award new achievements, return list of newly earned"""
    try:
        user = db.execute("SELECT achievements FROM users WHERE id = ?", user_id)
        if not user:
            return []
        current = (user[0]["achievements"] or "").split(",")
        current = [a for a in current if a]
        newly_earned = []

        counts = {
            "items": db.execute("SELECT COUNT(*) AS c FROM items WHERE user_id = ?", user_id)[0]["c"],
            "outfits": db.execute("SELECT COUNT(*) AS c FROM outfits WHERE user_id = ?", user_id)[0]["c"],
            "wishlist": db.execute("SELECT COUNT(*) AS c FROM wishlist WHERE user_id = ?", user_id)[0]["c"],
        }

        def award(key):
            if key not in current:
                current.append(key)
                newly_earned.append(key)

        if counts["items"] >= 1:  award("first_item")
        if counts["items"] >= 10: award("ten_items")
        if counts["items"] >= 50: award("fifty_items")
        if counts["outfits"] >= 1: award("first_outfit")
        if counts["outfits"] >= 10: award("ten_outfits")
        if counts["wishlist"] >= 1: award("first_wish")
        if counts["wishlist"] >= 10: award("ten_wishes")

        # Style check
        korean_items = db.execute(
            "SELECT COUNT(*) AS c FROM items WHERE user_id = ? AND (style LIKE '%korean%' OR style LIKE '%kpop%')",
            user_id
        )[0]["c"]
        if korean_items >= 3: award("korean_fan")

        # Streak
        user_row = db.execute("SELECT streak FROM users WHERE id = ?", user_id)[0]
        if (user_row["streak"] or 0) >= 7: award("week_streak")

        if newly_earned:
            db.execute("UPDATE users SET achievements = ? WHERE id = ?",
                       ",".join(current), user_id)
        return newly_earned
    except Exception as e:
        print("Achievement error:", e)
        return []


def get_user_achievements(user_id, db, lang="en"):
    """Return list of user's achievements with icons/names"""
    try:
        user = db.execute("SELECT achievements FROM users WHERE id = ?", user_id)
        if not user:
            return []
        keys = (user[0]["achievements"] or "").split(",")
        keys = [k for k in keys if k]
        result = []
        for k in keys:
            if k in ACHIEVEMENTS:
                a = ACHIEVEMENTS[k]
                name_key = "name_" + lang if lang in ["en", "ar", "ko"] else "name_en"
                result.append({
                    "key": k,
                    "icon": a["icon"],
                    "name": a.get(name_key, a["name_en"]),
                })
        return result
    except Exception:
        return []


def update_streak(user_id, db):
    """Update daily streak"""
    from datetime import date, timedelta
    try:
        row = db.execute("SELECT streak, last_active FROM users WHERE id = ?", user_id)
        if not row:
            return 1
        today = date.today()
        last = row[0]["last_active"]
        streak = row[0]["streak"] or 1

        if last:
            if isinstance(last, str):
                from datetime import datetime
                last = datetime.strptime(last[:10], "%Y-%m-%d").date()
            diff = (today - last).days
            if diff == 0:
                pass  # Same day
            elif diff == 1:
                streak += 1
            else:
                streak = 1
        else:
            streak = 1

        db.execute("UPDATE users SET streak = ?, last_active = ? WHERE id = ?",
                   streak, str(today), user_id)
        return streak
    except Exception as e:
        print("Streak error:", e)
        return 1
