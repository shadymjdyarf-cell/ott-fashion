import os
import uuid
import base64
from flask import Flask, flash, redirect, render_template, request, session, Response, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from cs50 import SQL

from helpers import (
    apology, login_required, OCCASIONS, STYLES,
    get_rates, suggest_outfit, get_confidence,
    get_seasonal_theme, fetch_trends_from_rss,
    fetch_fashion_images,
)

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = "ott-secret-key-2026"
Session(app)

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

db = SQL("sqlite:///ott.db")


# ==================== AUTH ====================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username or not email or not password:
            return apology("All fields are required", 400)
        if password != confirmation:
            return apology("Passwords do not match", 400)

        try:
            user_id = db.execute(
                "INSERT INTO users (username, email, hash, city, country) VALUES (?, ?, ?, ?, ?)",
                username, email, generate_password_hash(password),
                request.form.get("city", ""),
                request.form.get("country", ""),
            )
        except Exception:
            return apology("Username or email already taken", 400)

        session["user_id"] = user_id
        flash("Welcome to OTT")
        return redirect("/")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("Invalid username or password", 403)
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm", "")
        if not username or not email or not new_password:
            return apology("All fields are required", 400)
        if new_password != confirm:
            return apology("Passwords do not match", 400)
        rows = db.execute("SELECT id FROM users WHERE username = ? AND email = ?", username, email)
        if len(rows) != 1:
            return apology("Username and email do not match", 403)
        db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new_password), rows[0]["id"])
        flash("Password reset - please login")
        return redirect("/login")
    return render_template("forgot.html")


# ==================== LANGUAGE ====================

@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in ["en", "ar", "ko"]:
        session["lang"] = lang
    return redirect(request.referrer or "/")


# ==================== CONTEXT ====================

@app.context_processor
def inject_globals():
    from translations import get_text
    lang = session.get("lang", "en")
    season_name, season_emoji, season_color = get_seasonal_theme()
    return {
        "lang": lang,
        "t": lambda key: get_text(key, lang),
        "season_name": season_name,
        "season_emoji": season_emoji,
        "season_color": season_color,
    }


# ==================== HOME ====================

@app.route("/")
@login_required
def index():
    import random
    from helpers import get_daily_quote, update_streak, check_achievements, get_user_achievements
    uid = session["user_id"]
    lang = session.get("lang", "en")

    # Update streak
    streak = update_streak(uid, db)

    # Check for new achievements
    new_achievements = check_achievements(uid, db)
    for a in new_achievements:
        flash("New achievement unlocked! " + a.replace("_", " ").title())

    user = db.execute("SELECT * FROM users WHERE id = ?", uid)[0]
    stats = {
        "wardrobe": db.execute("SELECT COUNT(*) AS c FROM items WHERE user_id = ?", uid)[0]["c"],
        "wishlist": db.execute("SELECT COUNT(*) AS c FROM wishlist WHERE user_id = ?", uid)[0]["c"],
        "outfits": db.execute("SELECT COUNT(*) AS c FROM outfits WHERE user_id = ?", uid)[0]["c"],
    }
    viral_items = db.execute(
        "SELECT * FROM items WHERE user_id = ? AND is_viral = 1 ORDER BY created_at DESC LIMIT 4",
        uid
    )
    confidence = get_confidence()
    daily_quote = get_daily_quote(lang)
    achievements = get_user_achievements(uid, db, lang)

    queries = [
        "korean street fashion", "korean fashion outfit", "seoul street style",
        "korean streetwear", "kpop fashion", "korean style",
    ]
    query = random.choice(queries)
    page = random.randint(1, 5)
    discover_images = fetch_fashion_images(query, 20, page)

    return render_template(
        "dashboard.html",
        user=user, stats=stats, occasions=OCCASIONS,
        confidence=confidence, viral_items=viral_items,
        discover_images=discover_images,
        streak=streak, daily_quote=daily_quote,
        achievements=achievements,
    )

# ==================== WARDROBE ====================

@app.route("/wardrobe")
@login_required
def wardrobe():
    uid = session["user_id"]
    occ = request.args.get("occasion", "")
    style = request.args.get("style", "")
    query = "SELECT * FROM items WHERE user_id = ?"
    params = [uid]
    if occ and occ in OCCASIONS:
        query += " AND occasion = ?"
        params.append(occ)
    if style and style in STYLES:
        query += " AND style = ?"
        params.append(style)
    query += " ORDER BY created_at DESC"
    items = db.execute(query, *params)

    search_query = "korean street fashion"
    if occ:
        occ_map = {
            "gym": "gym workout fitness",
            "sports": "sportswear athlete",
            "school": "student school outfit",
            "casual": "casual street style",
            "occasion": "elegant evening outfit",
            "trend": "trendy fashion",
            "vintage": "vintage retro fashion",
            "halloween": "halloween costume",
        }
        search_query = occ_map.get(occ, "korean street fashion")
    if style:
        style_map = {
            "kpop": "kpop idol fashion",
            "oldmoney": "old money classic outfit",
            "street": "streetwear urban fashion",
            "minimal": "minimalist fashion",
            "boho": "boho chic fashion",
            "classic": "classic elegant fashion",
            "retro": "retro vintage fashion",
            "korean": "korean street fashion",
            "vintage": "vintage outfit",
        }
        search_query = style_map.get(style, style + " fashion")

    inspiration = fetch_fashion_images(search_query, 12)
    return render_template(
        "wardrobe.html", items=items, occasions=OCCASIONS, styles=STYLES,
        active=occ, active_style=style, inspiration=inspiration
    )


@app.route("/wardrobe/add", methods=["GET", "POST"])
@login_required
def add_item():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        occasion = request.form.get("occasion", "")
        if not name or occasion not in OCCASIONS:
            return apology("Name and occasion are required", 400)

        image_path = None
        file = request.files.get("image")
        if file and file.filename:
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
                fname = str(uuid.uuid4()) + "." + ext
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
                image_path = "uploads/" + fname

        db.execute(
            "INSERT INTO items (user_id, name, occasion, color, image_path, notes, style) VALUES (?, ?, ?, ?, ?, ?, ?)",
            session["user_id"], name, occasion,
            request.form.get("color", ""),
            image_path,
            request.form.get("notes", ""),
            request.form.get("style", ""),
        )
        flash("Item added to wardrobe")
        return redirect("/wardrobe")
    return render_template("add_item.html", occasions=OCCASIONS, styles=STYLES)


@app.route("/wardrobe/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    db.execute("DELETE FROM items WHERE id = ? AND user_id = ?", item_id, session["user_id"])
    flash("Item removed")
    return redirect("/wardrobe")


@app.route("/wardrobe/viral/<int:item_id>", methods=["POST"])
@login_required
def toggle_viral(item_id):
    row = db.execute("SELECT is_viral FROM items WHERE id = ? AND user_id = ?", item_id, session["user_id"])
    if row:
        new_val = 0 if row[0]["is_viral"] else 1
        db.execute("UPDATE items SET is_viral = ? WHERE id = ?", new_val, item_id)
    return redirect("/wardrobe")


# ==================== WISHLIST ====================

@app.route("/wishlist", methods=["GET", "POST"])
@login_required
def wishlist():
    uid = session["user_id"]
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            return apology("Name is required", 400)
        try:
            price = float(request.form.get("price_usd") or 0)
        except ValueError:
            price = 0
        image_path = None
        file = request.files.get("image")
        if file and file.filename:
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
                fname = str(uuid.uuid4()) + "." + ext
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
                image_path = "uploads/" + fname
        db.execute(
            "INSERT INTO wishlist (user_id, name, description, image_path, price_usd, link, is_diy, priority, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            uid, name,
            request.form.get("description", ""),
            image_path, price,
            request.form.get("link", ""),
            1 if request.form.get("is_diy") else 0,
            request.form.get("priority", "medium"),
            request.form.get("status", "thinking"),
        )
        flash("Wish added")
        return redirect("/wishlist")

    # Filter by priority/status if provided
    priority = request.args.get("priority", "").strip()
    status = request.args.get("status", "").strip()
    query = "SELECT * FROM wishlist WHERE user_id = ?"
    params = [uid]
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, created_at DESC"
    items = db.execute(query, *params)
    rates = get_rates()
    return render_template("wishlist.html", items=items, rates=rates,
                           active_priority=priority, active_status=status)


@app.route("/wishlist/delete/<int:wish_id>", methods=["POST"])
@login_required
def delete_wish(wish_id):
    db.execute("DELETE FROM wishlist WHERE id = ? AND user_id = ?", wish_id, session["user_id"])
    flash("Wish removed")
    return redirect("/wishlist")


# ==================== TRENDS ====================

@app.route("/trends")
@login_required
def trends():
    from helpers import translate_text
    lang = session.get("lang", "en")
    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute(
            "SELECT * FROM trends WHERE term LIKE ? OR description LIKE ? ORDER BY term",
            "%" + q + "%", "%" + q + "%"
        )
    else:
        rows = db.execute("SELECT * FROM trends ORDER BY term")
    rows = [dict(r) for r in rows]
    for t in rows:
        if lang != "en":
            t["term"] = translate_text(t["term"], lang)
            t["description"] = translate_text(t["description"], lang)
        if not t.get("image_url"):
            imgs = fetch_fashion_images(t["term"] + " fashion", 1)
            if imgs:
                t["image_url"] = imgs[0].get("thumb") or imgs[0].get("url", "")
                try:
                    db.execute("UPDATE trends SET image_url = ? WHERE id = ?", t["image_url"], t["id"])
                except Exception:
                    pass
    return render_template("trends.html", trends=rows, q=q)


@app.route("/trends/refresh", methods=["POST"])
@login_required
def refresh_trends():
    source = request.form.get("source", "all")
    items = fetch_trends_from_rss(source)
    added = 0
    for it in items:
        try:
            title = it["title"]
            image = it.get("image", "")
            src = it.get("source", "RSS")
            # Skip super long titles (not trends)
            if len(title) > 80:
                continue
            existing = db.execute("SELECT id FROM trends WHERE term = ?", title[:60])
            if existing:
                continue
            db.execute(
                "INSERT INTO trends (term, description, era, image_url) VALUES (?, ?, ?, ?)",
                title[:60], title + " - from " + src, src, image
            )
            added += 1
        except Exception:
            pass
    flash("Refreshed " + str(added) + " trends from " + source)
    return redirect("/trends")


@app.route("/trends/add", methods=["POST"])
@login_required
def add_trend():
    term = request.form.get("term", "").strip()
    era = request.form.get("era", "").strip()
    description = request.form.get("description", "").strip()
    palette = request.form.get("palette", "").strip()
    if not term:
        flash("Term is required")
        return redirect("/trends")
    try:
        db.execute(
            "INSERT INTO trends (term, description, era, palette) VALUES (?, ?, ?, ?)",
            term, description or term, era, palette
        )
        flash("Trend added: " + term)
    except Exception:
        flash("Term already exists")
    return redirect("/trends")


@app.route("/stylist", methods=["GET", "POST"])
@login_required
def stylist():
    import random
    result = None
    tip = None
    reasons = []
    inspiration = []
    chosen_occasion = "casual"

    if request.method == "POST":
        occasion = request.form.get("occasion", "casual")
        weather = request.form.get("weather", "")
        mood = request.form.get("mood", "")
        chosen_occasion = occasion

        items = db.execute("SELECT * FROM items WHERE user_id = ?", session["user_id"])
        result, tip, reasons = suggest_outfit(items, occasion, weather, mood)

        occ_queries = {
            "gym": "korean gym outfit",
            "sports": "korean sportswear outfit",
            "school": "korean student outfit",
            "casual": "korean casual outfit",
            "occasion": "korean formal outfit",
            "trend": "korean trendy outfit",
            "vintage": "korean vintage outfit",
            "halloween": "korean halloween outfit",
        }
        query = occ_queries.get(occasion, "korean outfit")
        random_page = random.randint(1, 10)
        inspiration = fetch_fashion_images(query, 16, random_page, randomize=True)

        if result:
            try:
                db.execute(
                    "INSERT INTO outfits (user_id, title, occasion, item_ids) VALUES (?, ?, ?, ?)",
                    session["user_id"], occasion + " outfit", occasion,
                    ",".join(str(i["id"]) for i in result)
                )
            except Exception:
                pass

    history = db.execute(
        "SELECT * FROM outfits WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        session["user_id"]
    )
    return render_template(
        "stylist.html",
        occasions=OCCASIONS,
        result=result,
        tip=tip,
        reasons=reasons,
        history=history,
        inspiration=inspiration,
        chosen_occasion=chosen_occasion,
    )


# ==================== PROFILE ====================

@app.route("/profile")
@login_required
def profile():
    from helpers import get_seasonal_dicebear, EMOJI_AVATARS, DICEBEAR_STYLES, get_dicebear_url
    uid = session["user_id"]
    user = db.execute("SELECT * FROM users WHERE id = ?", uid)[0]
    counts = {
        "item_count": db.execute("SELECT COUNT(*) AS c FROM items WHERE user_id = ?", uid)[0]["c"],
        "wishlist": db.execute("SELECT COUNT(*) AS c FROM wishlist WHERE user_id = ?", uid)[0]["c"],
        "outfits": db.execute("SELECT COUNT(*) AS c FROM outfits WHERE user_id = ?", uid)[0]["c"],
    }
    recent_items = db.execute("SELECT * FROM items WHERE user_id = ? ORDER BY created_at DESC LIMIT 6", uid)

    seasonal_url, seasonal_emoji = get_seasonal_dicebear(user["username"])
    user_style = user["avatar_style"] or "thumbs"
    user_dicebear_url = get_dicebear_url(user_style, user["username"])

    # Get previews for each style
    style_previews = [
        {"id": s["id"], "name": s["name"], "url": get_dicebear_url(s["id"], user["username"])}
        for s in DICEBEAR_STYLES
    ]

    return render_template(
        "profile.html",
        user=user,
        counts=counts,
        recent_items=recent_items,
        dicebear_url=user_dicebear_url,
        seasonal_url=seasonal_url,
        seasonal_emoji=seasonal_emoji,
        emoji_avatars=EMOJI_AVATARS,
        style_previews=style_previews,
    )


@app.route("/set_emoji_avatar", methods=["POST"])
@login_required
def set_emoji_avatar():
    emoji = request.form.get("emoji", "").strip()
    if not emoji:
        flash("Pick an emoji first")
        return redirect("/profile")
    db.execute(
        "UPDATE users SET avatar_emoji = ?, avatar_type = 'emoji', avatar_path = '' WHERE id = ?",
        emoji, session["user_id"]
    )
    flash("Avatar updated")
    return redirect("/profile")


@app.route("/reset_avatar", methods=["POST"])
@login_required
def reset_avatar():
    db.execute(
        "UPDATE users SET avatar_emoji = '', avatar_type = 'seasonal', avatar_path = '' WHERE id = ?",
        session["user_id"]
    )
    flash("Avatar reset to seasonal")
    return redirect("/profile")


# ==================== CAMERA ====================

@app.route("/camera")
@login_required
def camera():
    return render_template("camera.html")


@app.route("/camera/save", methods=["POST"])
@login_required
def camera_save():
    try:
        data = request.get_json()
        image_data = data.get("image", "")
        theme = data.get("theme", "Camera")
        if not image_data or not image_data.startswith("data:image"):
            return jsonify({"ok": False, "error": "Invalid image"})
        header, encoded = image_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        fname = str(uuid.uuid4()) + ".png"
        path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
        with open(path, "wb") as f:
            f.write(img_bytes)
        db.execute(
            "INSERT INTO items (user_id, name, occasion, image_path, notes) VALUES (?, ?, ?, ?, ?)",
            session["user_id"], theme + " photo", "trend",
            "uploads/" + fname, "Captured with " + theme
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ==================== DISCOVER ====================

@app.route("/discover")
@login_required
def discover():
    import random
    q = request.args.get("q", "").strip()
    if not q:
        q = random.choice([
            "korean street fashion",
            "seoul street style",
            "kpop fashion",
            "korean outfit",
            "hongdae street style",
            "korean fashion week",
        ])

    # Random page for fresh results each time
    random_page = random.randint(1, 15)
    images = fetch_fashion_images(q, 24, random_page, randomize=True)

    return render_template("discover.html", images=images, q=q)


@app.route("/discover/save", methods=["POST"])
@login_required
def discover_save():
    name = request.form.get("name", "").strip()
    image_url = request.form.get("image", "").strip()
    if not name:
        return redirect(request.referrer or "/discover")
    db.execute(
        "INSERT INTO wishlist (user_id, name, description, link) VALUES (?, ?, ?, ?)",
        session["user_id"], name, "Saved from Discover", image_url
    )
    flash("Saved to wishlist")
    return redirect(request.referrer or "/discover")


# ==================== HELP ====================

@app.route("/help")
def help_page():
    return render_template("help.html")


# ==================== EXPORT / DELETE ====================

@app.route("/export")
@login_required
def export_data():
    import json
    uid = session["user_id"]
    data = {
        "user": dict(db.execute("SELECT id, username, email, city, country FROM users WHERE id = ?", uid)[0]),
        "items": [dict(r) for r in db.execute("SELECT * FROM items WHERE user_id = ?", uid)],
        "wishlist": [dict(r) for r in db.execute("SELECT * FROM wishlist WHERE user_id = ?", uid)],
        "outfits": [dict(r) for r in db.execute("SELECT * FROM outfits WHERE user_id = ?", uid)],
    }
    output = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    return Response(
        output, mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=ott-data.json"}
    )


@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    username = request.form.get("confirm_username", "").strip()
    password = request.form.get("confirm_password", "")
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]
    if username != user["username"]:
        return apology("Username does not match", 400)
    if not check_password_hash(user["hash"], password):
        return apology("Wrong password", 403)
    uid = session["user_id"]
    db.execute("DELETE FROM items WHERE user_id = ?", uid)
    db.execute("DELETE FROM wishlist WHERE user_id = ?", uid)
    db.execute("DELETE FROM outfits WHERE user_id = ?", uid)
    db.execute("DELETE FROM users WHERE id = ?", uid)
    session.clear()
    flash("Account deleted")
    return redirect("/login")


# ==================== API ====================

@app.route("/api/images")
@login_required
def api_images():
    q = request.args.get("q", "korean fashion")
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    images = fetch_fashion_images(q, 20, page)
    return jsonify({"images": images, "page": page, "query": q})


@app.route("/api/home-images")
@login_required
def api_home_images():
    import os
    import random
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    per_page = 20
    pins_dir = os.path.join("static", "pins")
    images = []
    if os.path.isdir(pins_dir):
        files = [f for f in os.listdir(pins_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        random.shuffle(files)
        start = (page - 1) * per_page
        end = start + per_page
        selected = files[start:end]
        images = [{"thumb": "pins/" + f, "url": "pins/" + f, "alt": "Korean fashion"} for f in selected]
    return jsonify({"images": images, "page": page})


@app.route("/upload_avatar", methods=["POST"])
@login_required
def upload_avatar():
    file = request.files.get("avatar")
    if not file or not file.filename:
        flash("Please choose a file")
        return redirect("/profile")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ["png", "jpg", "jpeg", "gif", "webp"]:
        flash("Invalid file type")
        return redirect("/profile")

    fname = "avatar_" + str(session["user_id"]) + "_" + str(uuid.uuid4())[:8] + "." + ext
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
    db.execute(
        "UPDATE users SET avatar_path = ? WHERE id = ?",
        "uploads/" + fname,
        session["user_id"]
    )
    flash("Profile picture updated")
    return redirect("/profile")


@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    city = request.form.get("city", "").strip()
    country = request.form.get("country", "").strip()
    bio = request.form.get("bio", "").strip()[:300]

    if not username or not email:
        flash("Username and email required")
        return redirect("/profile")

    try:
        db.execute(
            "UPDATE users SET username = ?, email = ?, city = ?, country = ?, bio = ? WHERE id = ?",
            username, email, city, country, bio, session["user_id"]
        )
        flash("Profile updated")
    except Exception:
        flash("Username or email already taken")
    return redirect("/profile")


@app.route("/upload_avatar/remove", methods=["POST"])
@login_required
def remove_avatar():
    db.execute("UPDATE users SET avatar_path = '' WHERE id = ?", session["user_id"])
    flash("Profile picture removed")
    return redirect("/profile")


@app.route("/trend/<int:trend_id>")
@login_required
def trend_detail(trend_id):
    import random
    row = db.execute("SELECT * FROM trends WHERE id = ?", trend_id)
    if not row:
        return apology("Trend not found", 404)
    trend = dict(row[0])

    # Fetch examples from Unsplash for this trend
    query = trend["term"] + " outfit fashion"
    examples = fetch_fashion_images(query, 20, random.randint(1, 5), randomize=True)

    # Fetch how-to-wear content (auto-generated if missing)
    how_to = trend.get("how_to_wear") or ""
    key_items = trend.get("key_items") or ""

    return render_template(
        "trend_detail.html",
        trend=trend,
        examples=examples,
        how_to=how_to,
        key_items=key_items,
    )


@app.route("/set_avatar_style", methods=["POST"])
@login_required
def set_avatar_style():
    style = request.form.get("style", "").strip()
    valid_styles = ["thumbs", "adventurer", "avataaars", "big-smile", "bottts",
                    "croodles", "fun-emoji", "lorelei", "micah", "miniavs",
                    "notionists", "open-peeps", "personas", "pixel-art"]
    if style not in valid_styles:
        flash("Invalid avatar style")
        return redirect("/profile")
    db.execute(
        "UPDATE users SET avatar_style = ?, avatar_type = 'dicebear', avatar_path = '', avatar_emoji = '' WHERE id = ?",
        style, session["user_id"]
    )
    flash("Avatar style updated")
    return redirect("/profile")


@app.route("/outfits")
@login_required
def outfit_history():
    import json as json_lib
    uid = session["user_id"]
    rows = db.execute(
        "SELECT * FROM outfits WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        uid
    )
    outfits = []
    for r in rows:
        o = dict(r)
        ids = [i for i in (o.get("item_ids") or "").split(",") if i.strip().isdigit()]
        items = []
        for iid in ids[:8]:
            item = db.execute("SELECT * FROM items WHERE id = ? AND user_id = ?", int(iid), uid)
            if item:
                items.append(dict(item[0]))
        o["items"] = items
        outfits.append(o)

    # Stats
    stats = {
        "total": len(rows),
        "by_occasion": {},
    }
    for r in rows:
        occ = r["occasion"] or "casual"
        stats["by_occasion"][occ] = stats["by_occasion"].get(occ, 0) + 1

    return render_template("outfit_history.html", outfits=outfits, stats=stats)


@app.route("/wardrobe/bulk_delete", methods=["POST"])
@login_required
def bulk_delete_items():
    ids = request.form.getlist("item_ids")
    if not ids:
        flash("No items selected")
        return redirect("/wardrobe")
    count = 0
    for iid in ids:
        try:
            db.execute(
                "DELETE FROM items WHERE id = ? AND user_id = ?",
                int(iid), session["user_id"]
            )
            count += 1
        except Exception:
            pass
    flash(f"Deleted {count} items")
    return redirect("/wardrobe")


@app.route("/wardrobe/duplicates")
@login_required
def find_duplicates():
    uid = session["user_id"]
    items = db.execute("SELECT * FROM items WHERE user_id = ? ORDER BY name", uid)
    # Group by lowercase name
    groups = {}
    for item in items:
        key = item["name"].lower().strip()
        if key not in groups:
            groups[key] = []
        groups[key].append(dict(item))
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    return render_template("duplicates.html", duplicates=duplicates)


@app.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    results = {"items": [], "wishlist": [], "trends": [], "query": q}
    if not q:
        return render_template("search.html", **results)

    uid = session["user_id"]
    like = "%" + q + "%"

    results["items"] = db.execute(
        "SELECT * FROM items WHERE user_id = ? AND (name LIKE ? OR notes LIKE ? OR color LIKE ? OR style LIKE ?)",
        uid, like, like, like, like
    )
    results["wishlist"] = db.execute(
        "SELECT * FROM wishlist WHERE user_id = ? AND (name LIKE ? OR description LIKE ?)",
        uid, like, like
    )
    results["trends"] = db.execute(
        "SELECT * FROM trends WHERE term LIKE ? OR description LIKE ?",
        like, like
    )
    return render_template("search.html", **results)




# ============ PROGRESS TRACKING ============
@app.route("/progress")
@login_required
def progress():
    uid = session["user_id"]
    # Stats
    total_items = db.execute("SELECT COUNT(*) AS c FROM items WHERE user_id = ?", uid)[0]["c"]
    total_outfits = db.execute("SELECT COUNT(*) AS c FROM outfits WHERE user_id = ?", uid)[0]["c"]
    total_wishes = db.execute("SELECT COUNT(*) AS c FROM wishlist WHERE user_id = ?", uid)[0]["c"]
    # Top occasion
    occ_rows = db.execute(
        "SELECT occasion, COUNT(*) AS c FROM items WHERE user_id = ? GROUP BY occasion ORDER BY c DESC LIMIT 1",
        uid
    )
    top_occasion = occ_rows[0]["occasion"] if occ_rows else "—"
    # Top color
    color_rows = db.execute(
        "SELECT color, COUNT(*) AS c FROM items WHERE user_id = ? AND color != '' GROUP BY color ORDER BY c DESC LIMIT 1",
        uid
    )
    top_color = color_rows[0]["color"] if color_rows else "—"
    # Top style
    style_rows = db.execute(
        "SELECT style, COUNT(*) AS c FROM items WHERE user_id = ? AND style != '' GROUP BY style ORDER BY c DESC LIMIT 1",
        uid
    )
    top_style = style_rows[0]["style"] if style_rows else "—"
    # Most worn
    worn_rows = db.execute(
        "SELECT name, worn_count FROM items WHERE user_id = ? ORDER BY worn_count DESC LIMIT 5",
        uid
    )
    user = db.execute("SELECT streak FROM users WHERE id = ?", uid)[0]
    return render_template("progress.html",
        total_items=total_items, total_outfits=total_outfits, total_wishes=total_wishes,
        top_occasion=top_occasion, top_color=top_color, top_style=top_style,
        most_worn=worn_rows, streak=user["streak"] or 1)


# ============ STYLE JOURNAL ============
@app.route("/journal", methods=["GET", "POST"])
@login_required
def journal():
    uid = session["user_id"]
    if request.method == "POST":
        note = request.form.get("note", "").strip()
        mood = request.form.get("mood", "neutral")
        if note:
            db.execute("INSERT INTO journal (user_id, note, mood) VALUES (?, ?, ?)", uid, note, mood)
            flash("Journal entry added")
        return redirect("/journal")
    entries = db.execute("SELECT * FROM journal WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", uid)
    return render_template("journal.html", entries=entries)


@app.route("/journal/delete/<int:eid>", methods=["POST"])
@login_required
def delete_journal(eid):
    db.execute("DELETE FROM journal WHERE id = ? AND user_id = ?", eid, session["user_id"])
    flash("Entry deleted")
    return redirect("/journal")


# ============ PERSONAL CHALLENGES ============
CHALLENGE_TEMPLATES = [
    ("Wear a new color", "Try a color you never wore before", 1),
    ("Style 5 outfits", "Create 5 different outfits", 5),
    ("Try a new occasion", "Add an item for a new occasion", 1),
    ("Add 5 items", "Grow your wardrobe", 5),
    ("Write 3 journal entries", "Document your style journey", 3),
]


@app.route("/challenges", methods=["GET", "POST"])
@login_required
def challenges():
    uid = session["user_id"]
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "new":
            import random
            t = random.choice(CHALLENGE_TEMPLATES)
            db.execute(
                "INSERT INTO challenges (user_id, title, description, target) VALUES (?, ?, ?, ?)",
                uid, t[0], t[1], t[2]
            )
            flash("New challenge started")
        elif action == "progress":
            cid = request.form.get("challenge_id")
            row = db.execute("SELECT * FROM challenges WHERE id = ? AND user_id = ?", cid, uid)
            if row:
                c = row[0]
                new_prog = (c["progress"] or 0) + 1
                completed = 1 if new_prog >= c["target"] else 0
                db.execute("UPDATE challenges SET progress = ?, completed = ? WHERE id = ?",
                           new_prog, completed, cid)
                if completed:
                    flash("Challenge completed! 🎉")
                else:
                    flash("Progress updated")
        elif action == "delete":
            cid = request.form.get("challenge_id")
            db.execute("DELETE FROM challenges WHERE id = ? AND user_id = ?", cid, uid)
        return redirect("/challenges")
    active = db.execute("SELECT * FROM challenges WHERE user_id = ? AND completed = 0 ORDER BY created_at DESC", uid)
    completed = db.execute("SELECT * FROM challenges WHERE user_id = ? AND completed = 1 ORDER BY created_at DESC", uid)
    return render_template("challenges.html", active=active, completed=completed)


# ============ SAVE TABS ============
@app.route("/tabs", methods=["GET", "POST"])
@login_required
def tabs():
    uid = session["user_id"]
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "save":
            name = request.form.get("name", "").strip()
            filters = request.form.get("filters", "").strip()
            if name:
                db.execute("INSERT INTO saved_tabs (user_id, name, filters) VALUES (?, ?, ?)", uid, name, filters)
                flash("Tab saved")
        elif action == "delete":
            tid = request.form.get("tab_id")
            db.execute("DELETE FROM saved_tabs WHERE id = ? AND user_id = ?", tid, uid)
        return redirect("/tabs")
    saved = db.execute("SELECT * FROM saved_tabs WHERE user_id = ? ORDER BY created_at DESC", uid)
    return render_template("tabs.html", saved=saved)


# ============ CALENDAR (Personal Occasions) ============
@app.route("/calendar", methods=["GET", "POST"])
@login_required
def calendar():
    uid = session["user_id"]
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "add":
            title = request.form.get("title", "").strip()
            date = request.form.get("date", "").strip()
            occ = request.form.get("occasion", "casual")
            if title and date:
                try:
                    db.execute("INSERT INTO personal_calendar (user_id, title, date, occasion) VALUES (?, ?, ?, ?)",
                               uid, title, date, occ)
                    flash("Event added")
                except Exception:
                    flash("Error adding event")
        elif action == "delete":
            eid = request.form.get("event_id")
            db.execute("DELETE FROM personal_calendar WHERE id = ? AND user_id = ?", eid, uid)
        return redirect("/calendar")
    events = db.execute("SELECT * FROM personal_calendar WHERE user_id = ? ORDER BY date", uid)
    return render_template("calendar.html", events=events, occasions=OCCASIONS)


# ============ SHARE OUTFIT ============
@app.route("/outfit/<int:outfit_id>")
def public_outfit(outfit_id):
    row = db.execute("SELECT * FROM outfits WHERE id = ?", outfit_id)
    if not row:
        return apology("Outfit not found", 404)
    o = dict(row[0])
    ids = [i for i in (o.get("item_ids") or "").split(",") if i.strip().isdigit()]
    items = []
    for iid in ids[:10]:
        item = db.execute("SELECT * FROM items WHERE id = ?", int(iid))
        if item:
            items.append(dict(item[0]))
    u = db.execute("SELECT username FROM users WHERE id = ?", o["user_id"])
    o["author"] = u[0]["username"] if u else "Someone"
    o["items"] = items
    return render_template("public_outfit.html", outfit=o)


# ============ WEATHER (Open-Meteo - Free) ============
@app.route("/weather")
@login_required
def weather():
    import urllib.request
    import json as json_lib
    # Get user city (default: Cairo)
    user = db.execute("SELECT city FROM users WHERE id = ?", session["user_id"])[0]
    city = (user["city"] or "Cairo").strip()

    # Simple city → coordinates mapping (top cities)
    cities = {
        "cairo": (30.0444, 31.2357), "alexandria": (31.2001, 29.9187),
        "giza": (30.0131, 31.2089), "luxor": (25.6872, 32.6396),
        "aswan": (24.0889, 32.8998), "paris": (48.8566, 2.3522),
        "london": (51.5074, -0.1278), "new york": (40.7128, -74.0060),
        "seoul": (37.5665, 126.9780), "tokyo": (35.6762, 139.6503),
        "dubai": (25.2048, 55.2708), "istanbul": (41.0082, 28.9784),
        "berlin": (52.5200, 13.4050), "rome": (41.9028, 12.4964),
        "madrid": (40.4168, -3.7038), "los angeles": (34.0522, -118.2437),
    }
    lat, lon = cities.get(city.lower(), (30.0444, 31.2357))

    weather_data = None
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto"
        req = urllib.request.Request(url, headers={"User-Agent": "OTT-App/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json_lib.loads(r.read())
        cur = data.get("current", {})
        temp = cur.get("temperature_2m")
        code = cur.get("weather_code", 0)
        wind = cur.get("wind_speed_10m")

        # Weather code → emoji + description
        codes = {
            0: ("☀️", "Clear sky"), 1: ("🌤️", "Mostly clear"),
            2: ("⛅", "Partly cloudy"), 3: ("☁️", "Overcast"),
            45: ("🌫️", "Foggy"), 48: ("🌫️", "Foggy"),
            51: ("🌦️", "Light drizzle"), 53: ("🌦️", "Drizzle"),
            55: ("🌧️", "Heavy drizzle"), 61: ("🌧️", "Light rain"),
            63: ("🌧️", "Rain"), 65: ("⛈️", "Heavy rain"),
            71: ("🌨️", "Light snow"), 73: ("❄️", "Snow"),
            75: ("❄️", "Heavy snow"), 80: ("🌦️", "Showers"),
            81: ("🌧️", "Showers"), 82: ("⛈️", "Heavy showers"),
            95: ("⛈️", "Thunderstorm"), 96: ("⛈️", "Storm"),
        }
        emoji, desc = codes.get(code, ("🌡️", "Weather"))

        # Suggest outfit type based on temp
        if temp is None:
            suggestion = "Check the weather!"
        elif temp >= 28:
            suggestion = "Hot day — go for light, breathable fabrics"
        elif temp >= 18:
            suggestion = "Mild day — perfect for casual outfits"
        elif temp >= 10:
            suggestion = "Cool day — add a light jacket"
        else:
            suggestion = "Cold day — layer up with a coat"

        weather_data = {
            "temp": temp, "code": code, "emoji": emoji,
            "desc": desc, "wind": wind, "suggestion": suggestion,
            "city": city.title(),
        }
    except Exception as e:
        print("Weather error:", e)

    return render_template("weather.html", weather=weather_data, city=city.title())


# ============ KOREAN SIZE CONVERTER ============
@app.route("/korean-size")
@login_required
def korean_size():
    return render_template("korean_size.html")


# ============ KOREAN HASHTAGS ============
@app.route("/k-hashtags")
@login_required
def k_hashtags():
    hashtags = [
        {"tag": "#KPopStyle", "desc": "K-pop idol fashion"},
        {"tag": "#SeoulStreet", "desc": "Seoul street fashion"},
        {"tag": "#Ulzzang", "desc": "Best-face Korean aesthetic"},
        {"tag": "#HongdaeStyle", "desc": "Hongdae district look"},
        {"tag": "#KBeauty", "desc": "Korean beauty trends"},
        {"tag": "#OutfitOfTheDay", "desc": "Daily outfits"},
        {"tag": "#OOTD", "desc": "Outfit of the day"},
        {"tag": "#KoreanFashion", "desc": "General Korean fashion"},
        {"tag": "#아이돌패션", "desc": "Idol fashion (Korean)"},
        {"tag": "#서울패션", "desc": "Seoul fashion (Korean)"},
        {"tag": "#KStyle", "desc": "Korean style"},
        {"tag": "#Aesthetic", "desc": "Aesthetic looks"},
        {"tag": "#Y2KKorean", "desc": "Y2K Korean vibe"},
        {"tag": "#MinimalK", "desc": "Minimal Korean style"},
        {"tag": "#OverSizeLook", "desc": "Oversized outfit"},
        {"tag": "#Streetwear", "desc": "Streetwear global"},
        {"tag": "#KPopIdol", "desc": "K-pop idols"},
        {"tag": "#Kdrama", "desc": "K-drama fashion"},
        {"tag": "#DramaFashion", "desc": "Drama character style"},
        {"tag": "#FashionKorea", "desc": "Korea fashion"},
    ]
    return render_template("k_hashtags.html", hashtags=hashtags)


# ============ BEFORE / AFTER ============
@app.route("/before-after", methods=["GET", "POST"])
@login_required
def before_after():
    uid = session["user_id"]
    if request.method == "POST":
        before = request.files.get("before")
        after = request.files.get("after")
        title = request.form.get("title", "").strip() or "Transformation"
        note = request.form.get("note", "").strip()

        before_path = None
        after_path = None

        if before and before.filename:
            ext = before.filename.rsplit(".", 1)[-1].lower()
            if ext in ["png", "jpg", "jpeg", "webp"]:
                fname = "before_" + str(uuid.uuid4())[:8] + "." + ext
                before.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
                before_path = "uploads/" + fname

        if after and after.filename:
            ext = after.filename.rsplit(".", 1)[-1].lower()
            if ext in ["png", "jpg", "jpeg", "webp"]:
                fname = "after_" + str(uuid.uuid4())[:8] + "." + ext
                after.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
                after_path = "uploads/" + fname

        if before_path and after_path:
            try:
                db.execute(
                    "INSERT INTO before_after (user_id, title, note, before_path, after_path) VALUES (?, ?, ?, ?, ?)",
                    uid, title, note, before_path, after_path
                )
                flash("Transformation saved")
            except Exception as e:
                flash("Error: table not found")
        else:
            flash("Both images required")
        return redirect("/before-after")

    try:
        transformations = db.execute(
            "SELECT * FROM before_after WHERE user_id = ? ORDER BY created_at DESC",
            uid
        )
    except Exception:
        transformations = []
    return render_template("before_after.html", transformations=transformations)


@app.route("/before-after/delete/<int:tid>", methods=["POST"])
@login_required
def delete_transformation(tid):
    try:
        db.execute("DELETE FROM before_after WHERE id = ? AND user_id = ?", tid, session["user_id"])
        flash("Deleted")
    except Exception:
        pass
    return redirect("/before-after")


# ============ PRICE TRACKING ============
@app.route("/wishlist/<int:wish_id>/price", methods=["POST"])
@login_required
def update_price(wish_id):
    row = db.execute("SELECT * FROM wishlist WHERE id = ? AND user_id = ?", wish_id, session["user_id"])
    if not row:
        return apology("Not found", 404)
    try:
        new_price = float(request.form.get("price", 0))
    except ValueError:
        new_price = 0
    note = request.form.get("note", "").strip()
    db.execute("UPDATE wishlist SET price_usd = ? WHERE id = ?", new_price, wish_id)
    db.execute("INSERT INTO price_history (wishlist_id, price, note) VALUES (?, ?, ?)",
               wish_id, new_price, note)
    flash("Price updated")
    return redirect("/wishlist")


@app.route("/wishlist/<int:wish_id>/history")
@login_required
def price_history(wish_id):
    row = db.execute("SELECT * FROM wishlist WHERE id = ? AND user_id = ?", wish_id, session["user_id"])
    if not row:
        return apology("Not found", 404)
    history = db.execute("SELECT * FROM price_history WHERE wishlist_id = ? ORDER BY created_at DESC", wish_id)
    return render_template("price_history.html", item=dict(row[0]), history=history)


# ============ PHOTO EDITOR ============
@app.route("/photo-editor")
@login_required
def photo_editor():
    items = db.execute("SELECT * FROM items WHERE user_id = ? AND image_path != '' ORDER BY created_at DESC", session["user_id"])
    return render_template("photo_editor.html", items=items)


@app.route("/photo-editor/save/<int:item_id>", methods=["POST"])
@login_required
def save_edited_photo(item_id):
    import base64
    row = db.execute("SELECT * FROM items WHERE id = ? AND user_id = ?", item_id, session["user_id"])
    if not row:
        return jsonify({"ok": False, "error": "Not found"})
    data = request.get_json()
    image_data = data.get("image", "")
    if not image_data or not image_data.startswith("data:image"):
        return jsonify({"ok": False, "error": "Invalid image"})
    header, encoded = image_data.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    fname = "edited_" + str(uuid.uuid4())[:8] + ".jpg"
    path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
    with open(path, "wb") as f:
        f.write(img_bytes)
    db.execute("UPDATE items SET image_path = ? WHERE id = ?", "uploads/" + fname, item_id)
    return jsonify({"ok": True})


# ============ KOREAN BRANDS ============
@app.route("/korean-brands")
@login_required
def korean_brands():
    brands = [
        {"name": "Musinsa", "type": "Marketplace", "desc": "Korea's largest online fashion platform", "url": "https://www.musinsa.com", "tier": "Mid"},
        {"name": "W Concept", "type": "Designer", "desc": "Curated Korean designer fashion", "url": "https://www.wconcept.co.kr", "tier": "Premium"},
        {"name": "Zigzag", "type": "Marketplace", "desc": "Women's fashion marketplace", "url": "https://zigzag.kr", "tier": "Mid"},
        {"name": "29CM", "type": "Lifestyle", "desc": "Curated lifestyle and fashion", "url": "https://www.29cm.co.kr", "tier": "Premium"},
        {"name": "Stylenanda", "type": "Fast Fashion", "desc": "Trendy Korean fast fashion", "url": "https://www.stylenanda.com", "tier": "Budget"},
        {"name": "Chuu", "type": "Fast Fashion", "desc": "Cute and trendy Korean brand", "url": "https://www.chuu.co.kr", "tier": "Budget"},
        {"name": "ADER Error", "type": "Designer", "desc": "Minimalist Seoul streetwear", "url": "https://adererror.com", "tier": "Premium"},
        {"name": "Nerdy", "type": "Streetwear", "desc": "Colorful streetwear brand", "url": "https://nerdy.co.kr", "tier": "Mid"},
        {"name": "Kirsh", "type": "Casual", "desc": "Cherry-logo casual wear", "url": "https://kirsh.co.kr", "tier": "Mid"},
        {"name": "Mixxmix", "type": "Fast Fashion", "desc": "Everyday Korean fashion", "url": "https://mixxmix.com", "tier": "Budget"},
        {"name": "Gentle Monster", "type": "Eyewear", "desc": "Iconic Korean sunglasses", "url": "https://www.gentlemonster.com", "tier": "Luxury"},
        {"name": "Kangol Korea", "type": "Accessories", "desc": "Hats and headwear", "url": "https://kangol.co.kr", "tier": "Mid"},
        {"name": "LMC", "type": "Streetwear", "desc": "Seoul-based streetwear", "url": "https://lmc.co.kr", "tier": "Mid"},
        {"name": "Thisisneverthat", "type": "Streetwear", "desc": "Skate-inspired streetwear", "url": "https://thisisneverthat.com", "tier": "Premium"},
        {"name": "Andersson Bell", "type": "Designer", "desc": "Contemporary Seoul designer", "url": "https://anderssonbell.com", "tier": "Luxury"},
        {"name": "Low Classic", "type": "Designer", "desc": "Minimalist womenswear", "url": "https://lowclassic.com", "tier": "Premium"},
    ]
    return render_template("korean_brands.html", brands=brands)


# ============ OCR (Tesseract.js) ============
@app.route("/ocr")
@login_required
def ocr_page():
    return render_template("ocr.html")


# ============ BARCODE (QuaggaJS) ============
@app.route("/barcode")
@login_required
def barcode_page():
    return render_template("barcode.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


# ============ PUBLIC PROFILE ============
@app.route("/u/<username>")
def public_profile(username):
    user_rows = db.execute("SELECT id, username, city, country, avatar_path, avatar_emoji, avatar_type, streak, created_at FROM users WHERE username = ?", username)
    if not user_rows:
        return apology("User not found", 404)
    profile_user = dict(user_rows[0])
    uid = profile_user["id"]
    current_uid = session.get("user_id")

    # Stats
    stats = {
        "items": db.execute("SELECT COUNT(*) AS c FROM items WHERE user_id = ?", uid)[0]["c"],
        "outfits": db.execute("SELECT COUNT(*) AS c FROM outfits WHERE user_id = ?", uid)[0]["c"],
        "followers": db.execute("SELECT COUNT(*) AS c FROM follows WHERE following_id = ?", uid)[0]["c"],
        "following": db.execute("SELECT COUNT(*) AS c FROM follows WHERE follower_id = ?", uid)[0]["c"],
    }

    # Is following?
    is_following = False
    if current_uid and current_uid != uid:
        r = db.execute("SELECT id FROM follows WHERE follower_id = ? AND following_id = ?", current_uid, uid)
        is_following = len(r) > 0

    # Public outfits with likes/comments count
    outfits = db.execute("SELECT * FROM outfits WHERE user_id = ? ORDER BY created_at DESC LIMIT 12", uid)
    outfit_list = []
    for o in outfits:
        o = dict(o)
        o["likes"] = db.execute("SELECT COUNT(*) AS c FROM likes WHERE outfit_id = ?", o["id"])[0]["c"]
        o["comments"] = db.execute("SELECT COUNT(*) AS c FROM comments WHERE outfit_id = ?", o["id"])[0]["c"]
        outfit_list.append(o)

    return render_template("public_profile.html",
        profile_user=profile_user, stats=stats,
        is_following=is_following, outfits=outfit_list,
        current_uid=current_uid)


# ============ FOLLOW ============
@app.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def follow_user(user_id):
    uid = session["user_id"]
    if uid == user_id:
        flash("Cannot follow yourself")
        return redirect(request.referrer or "/")
    try:
        db.execute("INSERT INTO follows (follower_id, following_id) VALUES (?, ?)", uid, user_id)
        flash("Now following")
    except Exception:
        pass
    return redirect(request.referrer or "/")


@app.route("/unfollow/<int:user_id>", methods=["POST"])
@login_required
def unfollow_user(user_id):
    uid = session["user_id"]
    db.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", uid, user_id)
    flash("Unfollowed")
    return redirect(request.referrer or "/")


# ============ LIKE OUTFIT ============
@app.route("/like/<int:outfit_id>", methods=["POST"])
@login_required
def like_outfit(outfit_id):
    uid = session["user_id"]
    existing = db.execute("SELECT id FROM likes WHERE user_id = ? AND outfit_id = ?", uid, outfit_id)
    if existing:
        db.execute("DELETE FROM likes WHERE user_id = ? AND outfit_id = ?", uid, outfit_id)
        return jsonify({"ok": True, "action": "unliked"})
    else:
        db.execute("INSERT INTO likes (user_id, outfit_id) VALUES (?, ?)", uid, outfit_id)
        return jsonify({"ok": True, "action": "liked"})


# ============ OUTFIT DETAIL (Public) ============
@app.route("/o/<int:outfit_id>")
def outfit_detail(outfit_id):
    row = db.execute("SELECT * FROM outfits WHERE id = ?", outfit_id)
    if not row:
        return apology("Outfit not found", 404)
    o = dict(row[0])
    ids = [i for i in (o.get("item_ids") or "").split(",") if i.strip().isdigit()]
    items = []
    for iid in ids[:10]:
        item = db.execute("SELECT * FROM items WHERE id = ?", int(iid))
        if item:
            items.append(dict(item[0]))
    u = db.execute("SELECT id, username, avatar_path, avatar_emoji, avatar_type FROM users WHERE id = ?", o["user_id"])
    o["author"] = dict(u[0]) if u else {"username": "Someone", "id": 0}
    o["items"] = items
    o["likes"] = db.execute("SELECT COUNT(*) AS c FROM likes WHERE outfit_id = ?", outfit_id)[0]["c"]

    current_uid = session.get("user_id")
    o["is_liked"] = False
    if current_uid:
        r = db.execute("SELECT id FROM likes WHERE user_id = ? AND outfit_id = ?", current_uid, outfit_id)
        o["is_liked"] = len(r) > 0

    comments = db.execute("""
        SELECT c.*, u.username FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.outfit_id = ? ORDER BY c.created_at DESC
    """, outfit_id)

    return render_template("outfit_detail.html", outfit=o, comments=comments)


# ============ ADD COMMENT ============
@app.route("/comment/<int:outfit_id>", methods=["POST"])
@login_required
def add_comment(outfit_id):
    text = request.form.get("text", "").strip()
    if not text:
        flash("Comment cannot be empty")
        return redirect(request.referrer or "/")
    db.execute("INSERT INTO comments (user_id, outfit_id, text) VALUES (?, ?, ?)",
               session["user_id"], outfit_id, text[:500])
    flash("Comment added")
    return redirect(request.referrer or "/")


@app.route("/comment/delete/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    row = db.execute("SELECT * FROM comments WHERE id = ?", comment_id)
    if row and row[0]["user_id"] == session["user_id"]:
        db.execute("DELETE FROM comments WHERE id = ?", comment_id)
        flash("Comment deleted")
    return redirect(request.referrer or "/")


# ============ COMMUNITY WALL ============
@app.route("/community")
@login_required
def community():
    uid = session["user_id"]

    # Get all public outfits with stats
    outfits = db.execute("""
        SELECT o.*, u.username FROM outfits o
        JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC LIMIT 50
    """)

    outfit_list = []
    for o in outfits:
        o = dict(o)
        o["likes"] = db.execute("SELECT COUNT(*) AS c FROM likes WHERE outfit_id = ?", o["id"])[0]["c"]
        o["comments"] = db.execute("SELECT COUNT(*) AS c FROM comments WHERE outfit_id = ?", o["id"])[0]["c"]
        outfit_list.append(o)

    # Sort by likes
    outfit_list.sort(key=lambda x: x["likes"], reverse=True)

    # Suggested users to follow
    suggested = db.execute("""
        SELECT id, username, avatar_path, avatar_emoji, avatar_type FROM users
        WHERE id != ? AND id NOT IN (SELECT following_id FROM follows WHERE follower_id = ?)
        ORDER BY RANDOM() LIMIT 6
    """, uid, uid)

    return render_template("community.html", outfits=outfit_list, suggested=suggested)


# ============ K-POP IDOL MATCH (Rule-based) ============
K_IDOLS = [
    {"name": "Jennie", "group": "BLACKPINK", "style": "Old Money meets Street", "colors": ["black", "white", "pink"], "keywords": ["chanel", "crop", "tweed"], "emoji": "🖤"},
    {"name": "Jungkook", "group": "BTS", "style": "Streetwear Casual", "colors": ["black", "white", "grey"], "keywords": ["hoodie", "cargo", "sneakers"], "emoji": "💜"},
    {"name": "Lisa", "group": "BLACKPINK", "style": "Bold Streetwear", "colors": ["black", "red", "yellow"], "keywords": ["crop", "cargo", "platform"], "emoji": "🔥"},
    {"name": "Jimin", "group": "BTS", "style": "Soft Elegant", "colors": ["white", "beige", "black"], "keywords": ["shirt", "blazer", "minimal"], "emoji": "✨"},
    {"name": "Rosé", "group": "BLACKPINK", "style": "Y2K Minimal", "colors": ["pink", "white", "black"], "keywords": ["skirt", "tee", "sneakers"], "emoji": "🌸"},
    {"name": "V", "group": "BTS", "style": "Old Money", "colors": ["brown", "beige", "white"], "keywords": ["coat", "suit", "classic"], "emoji": "🤎"},
    {"name": "IU", "group": "Solo", "style": "Soft Casual", "colors": ["pink", "white", "beige"], "keywords": ["knit", "skirt", "soft"], "emoji": "💫"},
    {"name": "Hanni", "group": "NewJeans", "style": "Y2K Fresh", "colors": ["pink", "blue", "white"], "keywords": ["tee", "skirt", "sneakers"], "emoji": "💙"},
    {"name": "Karina", "group": "aespa", "style": "Futuristic Y2K", "colors": ["silver", "black", "white"], "keywords": ["crop", "leather", "futuristic"], "emoji": "⚡"},
    {"name": "Taehyung", "group": "BTS", "style": "Vintage Classic", "colors": ["brown", "navy", "white"], "keywords": ["coat", "turtleneck", "classic"], "emoji": "🍂"},
]


@app.route("/idol-match")
@login_required
def idol_match():
    from helpers import _classify_item, _detect_style, _detect_color_group
    uid = session["user_id"]
    items = db.execute("SELECT * FROM items WHERE user_id = ?", uid)

    if len(items) < 3:
        return render_template("idol_match.html", matches=[], message="Add at least 3 items to your wardrobe first!")

    # Analyze user's style
    user_colors = {}
    user_keywords = set()
    user_styles = set()

    for item in items:
        color = (item.get("color") or "").lower()
        if color:
            user_colors[color] = user_colors.get(color, 0) + 1
        name = (item.get("name") or "").lower()
        for kw in ["crop", "cargo", "hoodie", "shirt", "blazer", "skirt", "tee", "coat", "turtleneck", "leather", "sneakers", "platform", "knit", "suit"]:
            if kw in name:
                user_keywords.add(kw)
        style = (item.get("style") or "").lower()
        if style:
            user_styles.add(style)

    # Score each idol
    matches = []
    for idol in K_IDOLS:
        score = 0
        reasons = []

        # Color match
        color_hits = sum(1 for c in idol["colors"] if c in user_colors)
        score += color_hits * 15
        if color_hits:
            reasons.append(f"{color_hits} matching colors")

        # Keyword match
        kw_hits = sum(1 for kw in idol["keywords"] if kw in user_keywords)
        score += kw_hits * 20
        if kw_hits:
            reasons.append(f"{kw_hits} similar items")

        # Style match
        style_lower = idol["style"].lower()
        for us in user_styles:
            if us in style_lower or any(w in style_lower for w in us.split()):
                score += 25
                reasons.append(f"style vibe: {us}")
                break

        matches.append({
            "idol": idol,
            "score": min(score, 95),
            "reasons": reasons[:3],
        })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return render_template("idol_match.html", matches=matches[:5], message=None)


# ============ FASHION WEEKS (RSS) ============
@app.route("/fashion-weeks")
@login_required
def fashion_weeks():
    from helpers import fetch_trends_from_rss
    items = fetch_trends_from_rss("all")
    # Filter for runway-related
    runway = [it for it in items if any(k in it["title"].lower() for k in ["runway", "fashion week", "seoul", "paris", "milan", "new york fashion"])]
    if not runway:
        runway = items[:10]

    weeks = [
        {"name": "Seoul Fashion Week", "when": "March & September", "emoji": "🇰🇷", "site": "https://www.seoulfashionweek.org"},
        {"name": "Paris Fashion Week", "when": "Feb/March & Sept/Oct", "emoji": "🇫🇷", "site": "https://www.fhcm.paris"},
        {"name": "Milan Fashion Week", "when": "Feb/March & Sept/Oct", "emoji": "🇮🇹", "site": "https://www.cameramoda.it"},
        {"name": "New York Fashion Week", "when": "February & September", "emoji": "🇺🇸", "site": "https://nyfw.com"},
        {"name": "London Fashion Week", "when": "February & September", "emoji": "🇬🇧", "site": "https://www.londonfashionweek.co.uk"},
    ]
    return render_template("fashion_weeks.html", weeks=weeks, runway=runway)


# ============ AI FROM PHOTOS (Canvas color analysis) ============
@app.route("/photo-style")
@login_required
def photo_style():
    return render_template("photo_style.html")


@app.route("/photo-style/analyze", methods=["POST"])
@login_required
def photo_style_analyze():
    import base64
    data = request.get_json()
    image_data = data.get("image", "")
    if not image_data or not image_data.startswith("data:image"):
        return jsonify({"ok": False, "error": "Invalid image"})

    # Client sends dominant colors as list
    colors = data.get("colors", [])
    if not colors:
        return jsonify({"ok": False, "error": "No colors detected"})

    # Suggest outfit from wardrobe based on colors
    uid = session["user_id"]
    items = db.execute("SELECT * FROM items WHERE user_id = ?", uid)

    from helpers import _detect_color_group
    # Find items matching the color groups
    target_groups = set()
    for c in colors:
        g = _detect_color_group(c)
        if g:
            target_groups.add(g)

    if not target_groups:
        target_groups = {"neutral"}

    matches = []
    for item in items:
        item_group = _detect_color_group(item.get("color", ""))
        if item_group in target_groups:
            matches.append(dict(item))

    tip = "Style with these colors - " + ", ".join(target_groups)

    return jsonify({
        "ok": True,
        "suggested": [{"id": m["id"], "name": m["name"], "color": m.get("color", ""), "image": m.get("image_path", "")} for m in matches[:8]],
        "tip": tip,
        "colors": colors,
    })


# ============ AI LEARNS (Preference tracking) ============
@app.route("/preferences")
@login_required
def preferences_view():
    uid = session["user_id"]
    # Get user's top liked colors/styles
    actions = db.execute("SELECT action, item_id FROM preferences WHERE user_id = ?", uid)
    color_count = {}
    style_count = {}
    for a in actions:
        if a["item_id"]:
            item = db.execute("SELECT color, style, occasion FROM items WHERE id = ?", a["item_id"])
            if item:
                it = item[0]
                if it["color"]:
                    color_count[it["color"]] = color_count.get(it["color"], 0) + 1
                if it["style"]:
                    style_count[it["style"]] = style_count.get(it["style"], 0) + 1

    top_colors = sorted(color_count.items(), key=lambda x: x[1], reverse=True)[:5]
    top_styles = sorted(style_count.items(), key=lambda x: x[1], reverse=True)[:5]

    return render_template("preferences.html",
        top_colors=top_colors, top_styles=top_styles,
        total_actions=len(actions))


@app.route("/track/<int:item_id>/<action>", methods=["POST"])
@login_required
def track_preference(item_id, action):
    if action not in ["like", "dislike", "select"]:
        return jsonify({"ok": False})
    db.execute("INSERT INTO preferences (user_id, item_id, action) VALUES (?, ?, ?)",
               session["user_id"], item_id, action)
    return jsonify({"ok": True})
