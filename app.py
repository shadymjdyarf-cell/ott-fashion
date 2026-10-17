from datetime import datetime, timedelta
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


def create_notification(user_id, actor_id, ntype, target_id, message):
    if user_id == actor_id:
        return
    try:
        db.execute(
            "INSERT INTO notifications (user_id, actor_id, type, target_id, message) VALUES (?, ?, ?, ?, ?)",
            user_id, actor_id, ntype, target_id, message
        )
    except Exception as e:
        print("Notif:", e)


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

    try:
        recent_outfits = db.execute(
            "SELECT id, title, occasion, is_public FROM outfits WHERE user_id = ? ORDER BY created_at DESC LIMIT 3",
            uid
        )
    except Exception:
        recent_outfits = []

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

        # auto-save disabled

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
    uid = session["user_id"]
    user = db.execute("SELECT * FROM users WHERE id = ?", uid)[0]

    counts = {
        "item_count": db.execute("SELECT COUNT(*) AS c FROM items WHERE user_id = ?", uid)[0]["c"],
        "wishlist": db.execute("SELECT COUNT(*) AS c FROM wishlist WHERE user_id = ?", uid)[0]["c"],
        "outfits": db.execute("SELECT COUNT(*) AS c FROM outfits WHERE user_id = ?", uid)[0]["c"],
    }

    recent_items = db.execute(
        "SELECT * FROM items WHERE user_id = ? ORDER BY created_at DESC LIMIT 9",
        uid
    )

    try:
        user_posts = db.execute(
            "SELECT * FROM posts WHERE user_id = ? AND (is_story = 0 OR is_story IS NULL) ORDER BY created_at DESC LIMIT 20",
            uid
        )
    except Exception:
        user_posts = []

    try:
        recent_outfits = db.execute(
            "SELECT id, title, occasion, is_public FROM outfits WHERE user_id = ? ORDER BY created_at DESC LIMIT 9",
            uid
        )
    except Exception:
        recent_outfits = []

    # Fetch reposts
    try:
        my_reposts = db.execute("""
            SELECT p.*, u.username AS original_author
            FROM reposts r
            JOIN posts p ON r.post_id = p.id
            JOIN users u ON p.user_id = u.id
            WHERE r.user_id = ?
            ORDER BY r.created_at DESC LIMIT 20
        """, uid)
    except Exception:
        my_reposts = []

    # Followers count
    try:
        followers_count = db.execute(
            "SELECT COUNT(*) AS c FROM follows WHERE following_id = ?", uid
        )[0]["c"]
    except Exception:
        followers_count = 0

    # Following count
    try:
        following_count = db.execute(
            "SELECT COUNT(*) AS c FROM follows WHERE follower_id = ?", uid
        )[0]["c"]
    except Exception:
        following_count = 0

    # Check if user has active story
    try:
        active_stories = db.execute("""
            SELECT id FROM posts
            WHERE user_id = ? AND is_story = 1
              AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, uid)
        has_active_story = len(active_stories) > 0
        active_story_id = active_stories[0]["id"] if active_stories else None
    except Exception:
        has_active_story = False
        active_story_id = None

    return render_template(
        "profile.html",
        user=user,
        counts=counts,
        recent_items=recent_items,
        user_posts=user_posts,
        my_reposts=my_reposts,
        recent_outfits=recent_outfits,
        has_active_story=has_active_story,
        active_story_id=active_story_id,
        followers_count=followers_count,
        following_count=following_count,
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




@app.route("/story/new", methods=["GET", "POST"])
@login_required
def new_story():
    if request.method == "POST":
        note = request.form.get("note", "").strip()[:200]
        file = request.files.get("media")
        if not file or not file.filename:
            flash("Please select an image or video")
            return redirect("/story/new")
        
        ext = file.filename.rsplit(".", 1)[-1].lower()
        media_type = "image" if ext in ["png","jpg","jpeg","gif","webp"] else "video" if ext in ["mp4","mov","webm"] else None
        if not media_type:
            flash("Invalid file type")
            return redirect("/story/new")
        
        fname = "story_" + str(uuid.uuid4())[:8] + "." + ext
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
        media_path = "uploads/" + fname
        
        try:
            duration = int(request.form.get("duration", 24))
        except ValueError:
            duration = 24
        if duration not in [1, 6, 12, 24, 48, 168]:
            duration = 24
        
        expires_at = (datetime.now() + timedelta(hours=duration)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO posts (user_id, media_path, media_type, note, is_public, is_story, expires_at, duration_hours) VALUES (?, ?, ?, ?, 1, 1, ?, ?)",
            session["user_id"], media_path, media_type, note, expires_at, duration
        )
        flash("Story posted! It will expire in 24 hours.")
        return redirect("/community")
    
    return render_template("new_story.html")




@app.route("/u/<username>")
def public_profile(username):
    user_rows = db.execute("SELECT id, username, city, country, avatar_path, avatar_emoji, avatar_type, streak, created_at FROM users WHERE username = ?", username)
    if not user_rows:
        return apology("User not found", 404)
    profile_user = dict(user_rows[0])
    uid = profile_user["id"]
    current_uid = session.get("user_id")

    # Check if blocked
    if current_uid:
        blocked = db.execute("SELECT id FROM blocks WHERE (blocker_id = ? AND blocked_id = ?) OR (blocker_id = ? AND blocked_id = ?)",
                             current_uid, uid, uid, current_uid)
        if blocked:
            return apology("This user is not available", 403)

    is_own_profile = (current_uid == uid)

    # Stats
    stats = {
        "followers": db.execute("SELECT COUNT(*) AS c FROM follows WHERE following_id = ?", uid)[0]["c"],
        "following": db.execute("SELECT COUNT(*) AS c FROM follows WHERE follower_id = ?", uid)[0]["c"],
    }

    # Is following?
    is_following = False
    if current_uid and current_uid != uid:
        r = db.execute("SELECT id FROM follows WHERE follower_id = ? AND following_id = ?", current_uid, uid)
        is_following = len(r) > 0

    # Check if private
    is_private = profile_user.get("is_private", 0) == 1 if "is_private" in profile_user else False
    is_following = False
    if current_uid and current_uid != uid:
        r = db.execute("SELECT id FROM follows WHERE follower_id = ? AND following_id = ?", current_uid, uid)
        is_following = len(r) > 0
    
    # Show posts only if: not private OR own profile OR following
    can_view_content = (not is_private) or is_own_profile or is_following
    
    if can_view_content:
        posts = db.execute("""
            SELECT p.* FROM posts p
            WHERE p.user_id = ? AND p.is_public = 1
            ORDER BY p.created_at DESC LIMIT 30
        """, uid)
        reposts = []
        try:
            reposts = db.execute("""
                SELECT p.*, u.username AS original_author, r.created_at AS reposted_at
                FROM reposts r
                JOIN posts p ON r.post_id = p.id
                JOIN users u ON p.user_id = u.id
                WHERE r.user_id = ?
                ORDER BY r.created_at DESC LIMIT 20
            """, uid)
        except Exception:
            pass
    else:
        posts = []
        reposts = []

    # Reposts
    reposts = []
    try:
        reposts = db.execute("""
            SELECT p.*, u.username AS original_author, r.created_at AS reposted_at
            FROM reposts r
            JOIN posts p ON r.post_id = p.id
            JOIN users u ON p.user_id = u.id
            WHERE r.user_id = ?
            ORDER BY r.created_at DESC LIMIT 20
        """, uid)
    except Exception:
        pass

    # Has active story
    try:
        active_stories = db.execute("""
            SELECT id FROM posts
            WHERE user_id = ? AND is_story = 1
              AND (expires_at IS NULL OR expires_at > datetime('now'))
            ORDER BY created_at DESC LIMIT 1
        """, uid)
        has_active_story = len(active_stories) > 0
        active_story_id = active_stories[0]["id"] if active_stories else None
    except Exception:
        has_active_story = False
        active_story_id = None

    return render_template("public_profile.html",
        profile_user=profile_user,
        stats=stats,
        is_following=is_following,
        posts=posts,
        reposts=reposts,
        current_uid=current_uid,
        is_own_profile=is_own_profile,
        has_active_story=has_active_story,
        active_story_id=active_story_id,
        is_private=is_private,
        can_view_content=can_view_content,
    )



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
        # Create notification for outfit owner
        outfit = db.execute("SELECT user_id, title FROM outfits WHERE id = ?", outfit_id)
        if outfit:
            owner_id = outfit[0]["user_id"]
            create_notification(owner_id, uid, "like", outfit_id, "liked your outfit")
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
    # Create notification for outfit owner
    outfit = db.execute("SELECT user_id, title FROM outfits WHERE id = ?", outfit_id)
    if outfit:
        owner_id = outfit[0]["user_id"]
        create_notification(owner_id, session["user_id"], "comment", outfit_id, "commented on your outfit")
    flash("Comment added")
    return redirect(request.referrer or "/")


@app.route("/community")
@login_required
def community():
    uid = session["user_id"]
    
    try:
        posts = db.execute("SELECT p.*, u.username, u.avatar_path, u.avatar_emoji FROM posts p JOIN users u ON p.user_id = u.id WHERE p.is_public = 1 AND (p.is_story = 0 OR p.is_story IS NULL) ORDER BY p.created_at DESC LIMIT 30")
    except Exception:
        posts = []
    
    try:
        stories = db.execute("SELECT p.*, u.username, u.avatar_path, u.avatar_emoji FROM posts p JOIN users u ON p.user_id = u.id WHERE p.is_story = 1 AND (p.expires_at IS NULL OR p.expires_at > datetime('now')) ORDER BY p.created_at DESC")
    except Exception:
        stories = []
    
    story_users = {}
    for s in stories:
        s = dict(s)
        if s["user_id"] not in story_users:
            story_users[s["user_id"]] = {
                "user_id": s["user_id"],
                "username": s["username"],
                "avatar_path": s["avatar_path"],
                "avatar_emoji": s["avatar_emoji"],
                "stories": []
            }
        story_users[s["user_id"]]["stories"].append(s)
    
    try:
        suggested = db.execute("SELECT id, username, avatar_path, avatar_emoji FROM users WHERE id != ? ORDER BY RANDOM() LIMIT 8", uid)
    except Exception:
        suggested = []
    
    return render_template("community.html",
        posts=posts,
        story_users=list(story_users.values()),
        suggested=suggested)




# ============================================
# RESTORED ROUTES
# ============================================















@app.route("/outfits")
@login_required
def outfit_history():
    uid = session["user_id"]
    try:
        rows = db.execute("SELECT id, title, occasion, created_at FROM outfits WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", uid)
    except Exception:
        rows = []
    return render_template("outfit_history.html", outfits=rows, total=len(rows))


@app.route("/notifications")
@login_required
def notifications():
    uid = session["user_id"]
    rows = db.execute("SELECT n.*, u.username AS actor_name, u.avatar_path AS actor_avatar, u.avatar_emoji AS actor_emoji FROM notifications n LEFT JOIN users u ON n.actor_id = u.id WHERE n.user_id = ? ORDER BY n.created_at DESC LIMIT 50", uid)
    notifs = []
    for n in rows:
        n = dict(n)
        ntype = n.get("type", "")
        target = n.get("target_id")
        if ntype in ["like", "reaction", "comment", "reply"] and target:
            n["link"] = "/p/" + str(target)
        elif ntype == "follow":
            n["link"] = "/u/" + (n.get("actor_name") or "")
        else:
            n["link"] = "/community"
        notifs.append(n)
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", uid)
    return render_template("notifications.html", notifications=notifs)


@app.route("/notifications/count")
@login_required
def notifications_count():
    uid = session["user_id"]
    row = db.execute("SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0", uid)
    return jsonify({"count": row[0]["c"] if row else 0})


@app.route("/notifications/clear", methods=["POST"])
@login_required
def clear_notifications():
    db.execute("DELETE FROM notifications WHERE user_id = ?", session["user_id"])
    flash("Notifications cleared")
    return redirect("/notifications")


@app.route("/unfollow/<int:user_id>", methods=["POST"])
@login_required
def unfollow_user(user_id):
    db.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", session["user_id"], user_id)
    flash("Unfollowed")
    return redirect(request.referrer or "/following")


@app.route("/block/<int:user_id>", methods=["POST"])
@login_required
def block_user(user_id):
    uid = session["user_id"]
    if uid == user_id:
        flash("Cannot block yourself")
        return redirect(request.referrer or "/")
    try:
        db.execute("INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?, ?)", uid, user_id)
        db.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", uid, user_id)
        db.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", user_id, uid)
        flash("User blocked")
    except Exception as e:
        print("Block error:", e)
    return redirect(request.referrer or "/")


@app.route("/unblock/<int:user_id>", methods=["POST"])
@login_required
def unblock_user(user_id):
    db.execute("DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?", session["user_id"], user_id)
    flash("User unblocked")
    return redirect("/blocked")


@app.route("/blocked")
@login_required
def blocked_list():
    uid = session["user_id"]
    rows = db.execute("SELECT u.id, u.username, u.avatar_path, u.avatar_emoji FROM blocks b JOIN users u ON b.blocked_id = u.id WHERE b.blocker_id = ? ORDER BY b.created_at DESC", uid)
    return render_template("blocked.html", users=rows)


@app.route("/followers")
@login_required
def my_followers():
    uid = session["user_id"]
    rows = db.execute("SELECT u.id, u.username, u.avatar_path, u.avatar_emoji FROM follows f JOIN users u ON f.follower_id = u.id WHERE f.following_id = ? ORDER BY f.created_at DESC", uid)
    followers = []
    for r in rows:
        r = dict(r)
        back = db.execute("SELECT id FROM follows WHERE follower_id = ? AND following_id = ?", uid, r["id"])
        r["follows_back"] = len(back) > 0
        followers.append(r)
    return render_template("followers.html", users=followers, title="My Followers")


@app.route("/following")
@login_required
def my_following():
    uid = session["user_id"]
    rows = db.execute("SELECT u.id, u.username, u.avatar_path, u.avatar_emoji FROM follows f JOIN users u ON f.following_id = u.id WHERE f.follower_id = ? ORDER BY f.created_at DESC", uid)
    return render_template("followers.html", users=rows, title="Following")


@app.route("/search_users")
@login_required
def search_users():
    uid = session["user_id"]
    q = request.args.get("q", "").strip()
    if q:
        users = db.execute("SELECT id, username, avatar_path, avatar_emoji, city, country FROM users WHERE username LIKE ? AND id != ? ORDER BY username LIMIT 30", "%" + q + "%", uid)
    else:
        users = db.execute("SELECT id, username, avatar_path, avatar_emoji, city, country FROM users WHERE id != ? ORDER BY RANDOM() LIMIT 30", uid)
    result = []
    for u in users:
        u = dict(u)
        r = db.execute("SELECT id FROM follows WHERE follower_id = ? AND following_id = ?", uid, u["id"])
        u["is_following"] = len(r) > 0
        result.append(u)
    return render_template("search_users.html", users=result, q=q)


@app.route("/toggle_privacy", methods=["POST"])
@login_required
def toggle_privacy():
    uid = session["user_id"]
    user = db.execute("SELECT is_private FROM users WHERE id = ?", uid)
    current = user[0]["is_private"] if user else 0
    new_val = 0 if current == 1 else 1
    db.execute("UPDATE users SET is_private = ? WHERE id = ?", new_val, uid)
    flash("Profile is now " + ("private" if new_val else "public"))
    return redirect("/profile")


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    uid = session["user_id"]
    if request.method == "POST":
        note = request.form.get("note", "").strip()[:500]
        file = request.files.get("media")
        media_path = None
        media_type = "image"
        if file and file.filename:
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
                media_type = "image"
            elif ext in ["mp4", "mov", "webm"]:
                media_type = "video"
            else:
                flash("Only images or videos")
                return redirect("/post/new")
            fname = "post_" + str(uuid.uuid4())[:8] + "." + ext
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
            media_path = "uploads/" + fname
        if not media_path:
            flash("Select a file")
            return redirect("/post/new")
        db.execute("INSERT INTO posts (user_id, media_path, media_type, note, is_public) VALUES (?, ?, ?, ?, 1)", uid, media_path, media_type, note)
        flash("Post published!")
        return redirect("/profile")
    return render_template("new_post.html")


@app.route("/p/<int:post_id>")
def view_post(post_id):
    row = db.execute("SELECT * FROM posts WHERE id = ?", post_id)
    if not row:
        return apology("Not found", 404)
    p = dict(row[0])
    u = db.execute("SELECT id, username, avatar_path, avatar_emoji FROM users WHERE id = ?", p["user_id"])
    p["author"] = dict(u[0]) if u else {"username": "Someone", "id": 0}
    if request.args.get("json") == "1":
        return jsonify({"id": p["id"], "media_url": "/static/" + p["media_path"], "media_type": p["media_type"], "note": p.get("note") or "", "user_id": p["user_id"]})
    try:
        p["likes"] = db.execute("SELECT COUNT(*) AS c FROM post_reactions WHERE post_id = ?", post_id)[0]["c"]
        p["comments_count"] = db.execute("SELECT COUNT(*) AS c FROM post_comments WHERE post_id = ?", post_id)[0]["c"]
        p["is_liked"] = False
        if session.get("user_id"):
            r = db.execute("SELECT id FROM post_reactions WHERE user_id = ? AND post_id = ?", session["user_id"], post_id)
            p["is_liked"] = len(r) > 0
        comments = db.execute("SELECT c.*, u.username, u.avatar_path, u.avatar_emoji FROM post_comments c JOIN users u ON c.user_id = u.id WHERE c.post_id = ? ORDER BY c.created_at ASC", post_id)
    except Exception:
        p["likes"] = 0
        p["comments_count"] = 0
        p["is_liked"] = False
        comments = []
    return render_template("view_post.html", post=p, comments=comments)


@app.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def follow_user(user_id):
    uid = session["user_id"]
    if uid == user_id:
        flash("Cannot follow yourself")
        return redirect(request.referrer or "/")
    try:
        db.execute("INSERT INTO follows (follower_id, following_id) VALUES (?, ?)", uid, user_id)
        create_notification(user_id, uid, "follow", uid, "started following you")
        flash("Now following")
    except Exception:
        pass
    return redirect(request.referrer or "/")


# ============================================
# POST COMMENTS API
# ============================================
@app.route("/post/<int:post_id>/comments")
@login_required
def get_post_comments(post_id):
    try:
        comments = db.execute("""
            SELECT c.*, u.username, u.avatar_path, u.avatar_emoji
            FROM post_comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ?
            ORDER BY c.created_at ASC
        """, post_id)
        result = []
        for c in comments:
            c = dict(c)
            reactions = db.execute(
                "SELECT emoji, COUNT(*) AS c FROM comment_reactions WHERE comment_id = ? GROUP BY emoji",
                c["id"]
            )
            c["reactions"] = {r["emoji"]: r["c"] for r in reactions}
            result.append(c)
        return jsonify({"ok": True, "comments": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ============================================
# POST REACTIONS API
# ============================================
@app.route("/post/<int:post_id>/reactions")
@login_required
def get_post_reactions(post_id):
    try:
        rows = db.execute(
            "SELECT emoji, COUNT(*) AS c FROM post_reactions WHERE post_id = ? GROUP BY emoji",
            post_id
        )
        counts = {r["emoji"]: r["c"] for r in rows}
        my = None
        r = db.execute(
            "SELECT emoji FROM post_reactions WHERE user_id = ? AND post_id = ?",
            session["user_id"], post_id
        )
        if r:
            my = r[0]["emoji"]
        return jsonify({"ok": True, "counts": counts, "my_reaction": my, "total": sum(counts.values())})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ============================================
# POST REACT
# ============================================
@app.route("/post/<int:post_id>/react", methods=["POST"])
@login_required
def react_to_post(post_id):
    emoji = request.form.get("emoji", "❤️")
    valid = ["❤️", "😂", "😮", "😢", "🔥"]
    if emoji not in valid:
        emoji = "❤️"
    uid = session["user_id"]
    existing = db.execute("SELECT emoji FROM post_reactions WHERE user_id = ? AND post_id = ?", uid, post_id)
    if existing:
        if existing[0]["emoji"] == emoji:
            db.execute("DELETE FROM post_reactions WHERE user_id = ? AND post_id = ?", uid, post_id)
        else:
            db.execute("UPDATE post_reactions SET emoji = ? WHERE user_id = ? AND post_id = ?", emoji, uid, post_id)
    else:
        db.execute("INSERT INTO post_reactions (user_id, post_id, emoji) VALUES (?, ?, ?)", uid, post_id, emoji)
        post = db.execute("SELECT user_id FROM posts WHERE id = ?", post_id)
        if post and post[0]["user_id"] != uid:
            create_notification(post[0]["user_id"], uid, "reaction", post_id, "reacted " + emoji)
    counts = db.execute("SELECT emoji, COUNT(*) AS c FROM post_reactions WHERE post_id = ? GROUP BY emoji", post_id)
    my = db.execute("SELECT emoji FROM post_reactions WHERE user_id = ? AND post_id = ?", uid, post_id)
    return jsonify({"ok": True, "counts": {c["emoji"]: c["c"] for c in counts}, "my_reaction": my[0]["emoji"] if my else None})


# ============================================
# COMMENT REACT
# ============================================
@app.route("/comment/<int:comment_id>/react", methods=["POST"])
@login_required
def react_to_comment(comment_id):
    emoji = request.form.get("emoji", "❤️")
    valid = ["❤️", "😂", "😮", "😢", "🔥"]
    if emoji not in valid:
        emoji = "❤️"
    uid = session["user_id"]
    existing = db.execute("SELECT emoji FROM comment_reactions WHERE user_id = ? AND comment_id = ?", uid, comment_id)
    if existing:
        if existing[0]["emoji"] == emoji:
            db.execute("DELETE FROM comment_reactions WHERE user_id = ? AND comment_id = ?", uid, comment_id)
        else:
            db.execute("UPDATE comment_reactions SET emoji = ? WHERE user_id = ? AND comment_id = ?", emoji, uid, comment_id)
    else:
        db.execute("INSERT INTO comment_reactions (user_id, comment_id, emoji) VALUES (?, ?, ?)", uid, comment_id, emoji)
    counts = db.execute("SELECT emoji, COUNT(*) AS c FROM comment_reactions WHERE comment_id = ? GROUP BY emoji", comment_id)
    my = db.execute("SELECT emoji FROM comment_reactions WHERE user_id = ? AND comment_id = ?", uid, comment_id)
    return jsonify({"ok": True, "counts": {c["emoji"]: c["c"] for c in counts}, "my_reaction": my[0]["emoji"] if my else None})


# ============================================
# STORY REACT
# ============================================
@app.route("/story/<int:story_id>/react", methods=["POST"])
@login_required
def react_to_story(story_id):
    emoji = request.form.get("emoji", "❤️")
    valid = ["❤️", "😂", "😮", "😢", "🔥"]
    if emoji not in valid:
        emoji = "❤️"
    uid = session["user_id"]
    existing = db.execute("SELECT emoji FROM story_reactions WHERE user_id = ? AND story_id = ?", uid, story_id)
    if existing:
        if existing[0]["emoji"] == emoji:
            db.execute("DELETE FROM story_reactions WHERE user_id = ? AND story_id = ?", uid, story_id)
        else:
            db.execute("UPDATE story_reactions SET emoji = ? WHERE user_id = ? AND story_id = ?", emoji, uid, story_id)
    else:
        db.execute("INSERT INTO story_reactions (user_id, story_id, emoji) VALUES (?, ?, ?)", uid, story_id, emoji)
        post = db.execute("SELECT user_id FROM posts WHERE id = ?", story_id)
        if post and post[0]["user_id"] != uid:
            create_notification(post[0]["user_id"], uid, "story_reaction", story_id, "reacted " + emoji)
    counts = db.execute("SELECT emoji, COUNT(*) AS c FROM story_reactions WHERE story_id = ? GROUP BY emoji", story_id)
    my = db.execute("SELECT emoji FROM story_reactions WHERE user_id = ? AND story_id = ?", uid, story_id)
    return jsonify({"ok": True, "counts": {c["emoji"]: c["c"] for c in counts}, "my_reaction": my[0]["emoji"] if my else None})


# ============================================
# DELETE POST
# ============================================
@app.route("/post/delete/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    row = db.execute("SELECT * FROM posts WHERE id = ? AND user_id = ?", post_id, session["user_id"])
    if row:
        db.execute("DELETE FROM post_reactions WHERE post_id = ?", post_id)
        db.execute("DELETE FROM post_comments WHERE post_id = ?", post_id)
        db.execute("DELETE FROM reposts WHERE post_id = ?", post_id)
        db.execute("DELETE FROM story_reactions WHERE story_id = ?", post_id)
        db.execute("DELETE FROM posts WHERE id = ?", post_id)
        flash("Post deleted")
    return redirect(request.referrer or "/profile")


# ============================================
# REMOVE REPOST
# ============================================
@app.route("/repost/<int:post_id>/remove", methods=["POST"])
@login_required
def remove_repost(post_id):
    db.execute("DELETE FROM reposts WHERE user_id = ? AND post_id = ?", session["user_id"], post_id)
    flash("Repost removed")
    return redirect(request.referrer or "/profile")


# ============================================
# POST COMMENT
# ============================================
@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def comment_post(post_id):
    text = (request.form.get("text") or "").strip()
    if not text:
        flash("Empty comment")
        return redirect(request.referrer or "/community")
    db.execute("INSERT INTO post_comments (user_id, post_id, text) VALUES (?, ?, ?)",
               session["user_id"], post_id, text[:500])
    post = db.execute("SELECT user_id FROM posts WHERE id = ?", post_id)
    if post and post[0]["user_id"] != session["user_id"]:
        create_notification(post[0]["user_id"], session["user_id"], "comment", post_id, "commented")
    flash("Comment added")
    return redirect(request.referrer or "/community")


# ============================================
# COMMENT EDIT
# ============================================
@app.route("/comment/<int:comment_id>/edit", methods=["POST"])
@login_required
def edit_comment(comment_id):
    text = (request.form.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Empty"})
    row = db.execute("SELECT * FROM post_comments WHERE id = ? AND user_id = ?", comment_id, session["user_id"])
    if not row:
        return jsonify({"ok": False, "error": "Not authorized"})
    db.execute("UPDATE post_comments SET text = ? WHERE id = ?", text[:500], comment_id)
    return jsonify({"ok": True, "text": text[:500]})


# ============================================
# COMMENT DELETE
# ============================================
@app.route("/comment/<int:comment_id>/reply", methods=["POST"])
@login_required
def reply_to_comment(comment_id):
    text = (request.form.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Empty"})
    parent = db.execute("SELECT post_id, user_id FROM post_comments WHERE id = ?", comment_id)
    if not parent:
        return jsonify({"ok": False, "error": "Not found"})
    post_id = parent[0]["post_id"]
    db.execute("INSERT INTO post_comments (user_id, post_id, text, parent_id) VALUES (?, ?, ?, ?)",
               session["user_id"], post_id, text[:500], comment_id)
    if parent[0]["user_id"] != session["user_id"]:
        create_notification(parent[0]["user_id"], session["user_id"], "reply", post_id, "replied")
    return jsonify({"ok": True})


@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def ott_delete_comment(comment_id):
    row = db.execute("SELECT * FROM post_comments WHERE id = ? AND user_id = ?", comment_id, session["user_id"])
    if not row:
        return jsonify({"ok": False, "error": "Not authorized"})
    db.execute("DELETE FROM comment_reactions WHERE comment_id = ?", comment_id)
    db.execute("DELETE FROM post_comments WHERE parent_id = ?", comment_id)
    db.execute("DELETE FROM post_comments WHERE id = ?", comment_id)
    return jsonify({"ok": True})


@app.route("/post/<int:post_id>/repost", methods=["POST"])
@login_required
def repost_post(post_id):
    uid = session["user_id"]
    existing = db.execute("SELECT id FROM reposts WHERE user_id = ? AND post_id = ?", uid, post_id)
    if existing:
        db.execute("DELETE FROM reposts WHERE user_id = ? AND post_id = ?", uid, post_id)
        return jsonify({"ok": True, "action": "unreposted"})
    
    db.execute("INSERT INTO reposts (user_id, post_id) VALUES (?, ?)", uid, post_id)
    post = db.execute("SELECT user_id FROM posts WHERE id = ?", post_id)
    if post and post[0]["user_id"] != uid:
        create_notification(post[0]["user_id"], uid, "repost", post_id, "reposted your post")
    return jsonify({"ok": True, "action": "reposted"})


@app.route("/react/<string:type>/<int:item_id>", methods=["POST"])
@login_required
def react(type, item_id):
    emoji = request.form.get("emoji", "❤️")
    valid = ["❤️", "😂", "😮", "😢", "🔥"]
    if emoji not in valid: emoji = "❤️"
    uid = session["user_id"]
    
    if type == "post":
        existing = db.execute("SELECT emoji FROM post_reactions WHERE user_id = ? AND post_id = ?", uid, item_id)
        if existing:
            if existing[0]["emoji"] == emoji:
                db.execute("DELETE FROM post_reactions WHERE user_id = ? AND post_id = ?", uid, item_id)
            else:
                db.execute("UPDATE post_reactions SET emoji = ? WHERE user_id = ? AND post_id = ?", emoji, uid, item_id)
        else:
            db.execute("INSERT INTO post_reactions (user_id, post_id, emoji) VALUES (?, ?, ?)", uid, item_id, emoji)
            post = db.execute("SELECT user_id FROM posts WHERE id = ?", item_id)
            if post and post[0]["user_id"] != uid:
                create_notification(post[0]["user_id"], uid, "reaction", item_id, "reacted " + emoji)
        
        counts = db.execute("SELECT emoji, COUNT(*) AS c FROM post_reactions WHERE post_id = ? GROUP BY emoji", item_id)
        my = db.execute("SELECT emoji FROM post_reactions WHERE user_id = ? AND post_id = ?", uid, item_id)
        
    elif type == "comment":
        existing = db.execute("SELECT emoji FROM comment_reactions WHERE user_id = ? AND comment_id = ?", uid, item_id)
        if existing:
            if existing[0]["emoji"] == emoji:
                db.execute("DELETE FROM comment_reactions WHERE user_id = ? AND comment_id = ?", uid, item_id)
            else:
                db.execute("UPDATE comment_reactions SET emoji = ? WHERE user_id = ? AND comment_id = ?", emoji, uid, item_id)
        else:
            db.execute("INSERT INTO comment_reactions (user_id, comment_id, emoji) VALUES (?, ?, ?)", uid, item_id, emoji)
            
        counts = db.execute("SELECT emoji, COUNT(*) AS c FROM comment_reactions WHERE comment_id = ? GROUP BY emoji", item_id)
        my = db.execute("SELECT emoji FROM comment_reactions WHERE user_id = ? AND comment_id = ?", uid, item_id)

    return jsonify({
        "ok": True, 
        "counts": {c["emoji"]: c["c"] for c in counts}, 
        "my_reaction": my[0]["emoji"] if my else None
    })

