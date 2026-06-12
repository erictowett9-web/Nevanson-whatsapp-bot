import os
import json
import logging
from flask import Flask, request, jsonify, session, render_template_string
from groq import Groq
from fuzzywuzzy import fuzz
from twilio.twiml.messaging_response import MessagingResponse
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nevanson-secret-2026")

GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "nevanson2026")
groq_client    = Groq(api_key=GROQ_API_KEY)

# ── Shop constants ─────────────────────────────────────────────────────────────
SHOP_NAME     = "NEVANSON ELECTRICALS & ELECTRONICS"
SHOP_PHONE    = "0741311041 / 0720799896"
SHOP_LOCATION = "Mogogosiek Town – Opposite Stabex Petrol Station"
PAYBILL       = "522533"
PAYBILL_ACC   = "8093799"

CATEGORY_ICONS = {
    "Accessories": "🔧", "Bulbs": "💡", "Cables": "🔌",
    "Conduit & Trunking": "📦", "Floodlights": "🔦",
    "Fluorescent Lighting": "🕯️", "MCBs & Consumer Units": "⚡",
    "Shower Fittings": "🚿", "Sockets": "🔌", "Switches": "🔘",
}

FAQ_KEYWORDS = ["cable","bulb","switch","socket","mcb","price","location",
                "payment","mpesa","delivery","brand","tronic","warrant","order"]

# ── Default products (used for seeding only) ───────────────────────────────────
DEFAULT_PRODUCTS = {
    "5W AC Bulb (Yomy)":              {"price": 40,   "category": "Bulbs"},
    "7W AC Bulb (Yomy)":              {"price": 45,   "category": "Bulbs"},
    "9W AC Bulb (Yomy)":              {"price": 35,   "category": "Bulbs"},
    "5W AC Bulb (Hommie)":            {"price": 40,   "category": "Bulbs"},
    "7W AC Bulb (Hommie)":            {"price": 45,   "category": "Bulbs"},
    "9W AC Bulb (Hommie)":            {"price": 50,   "category": "Bulbs"},
    "12W AC Bulb (Hommie)":           {"price": 750,  "category": "Bulbs"},
    "50W AC Floodlight":              {"price": 1200, "category": "Floodlights"},
    "100W LED Floodlight (Atta)":     {"price": 230,  "category": "Floodlights"},
    "18W Bulkhead (Atta)":            {"price": 280,  "category": "Floodlights"},
    "24W Bulkhead (Atta)":            {"price": 280,  "category": "Floodlights"},
    "19.2W Switch":                   {"price": 60,   "category": "Switches"},
    "29.2W Switch":                   {"price": 75,   "category": "Switches"},
    "39.2W Switch":                   {"price": 100,  "category": "Switches"},
    "DP Switch 45A":                  {"price": 300,  "category": "Switches"},
    "4G 2W Switch (Casher)":          {"price": 200,  "category": "Switches"},
    "Socket Single":                  {"price": 80,   "category": "Sockets"},
    "Socket Double":                  {"price": 160,  "category": "Sockets"},
    "Socket Double 13A Tronic":       {"price": 300,  "category": "Sockets"},
    "Socket Single Double":           {"price": 3300, "category": "Sockets"},
    "Extension Socket Plk Sw":        {"price": 230,  "category": "Sockets"},
    "Pipe 20mm HLG":                  {"price": 75,   "category": "Conduit & Trunking"},
    "Throughbox 4-Way":               {"price": 15,   "category": "Conduit & Trunking"},
    "Throughbox 3-Way":               {"price": 15,   "category": "Conduit & Trunking"},
    "Saddle Clips 25mm":              {"price": 3,    "category": "Conduit & Trunking"},
    "MK Single":                      {"price": 15,   "category": "Conduit & Trunking"},
    "MK Double":                      {"price": 25,   "category": "Conduit & Trunking"},
    "Pattress Double":                {"price": 30,   "category": "Conduit & Trunking"},
    "Pattress Single":                {"price": 20,   "category": "Conduit & Trunking"},
    "1x1 Trunking":                   {"price": 70,   "category": "Conduit & Trunking"},
    "1.5 Singles R7B (roll)":         {"price": 1700, "category": "Conduit & Trunking"},
    "Plain Coupler 20mm":             {"price": 10,   "category": "Conduit & Trunking"},
    "Normal Bend 20mm":               {"price": 10,   "category": "Conduit & Trunking"},
    "Cable Single Tronic 1.5 (R7B)":  {"price": 5400, "category": "Cables"},
    "Cable Single Tronic 2.5 (R7B)":  {"price": 3,    "category": "Cables"},
    "MCB 6A Andeli":                  {"price": 110,  "category": "MCBs & Consumer Units"},
    "MCB 32A Andeli":                 {"price": 110,  "category": "MCBs & Consumer Units"},
    "MCB 2P 63A Andeli":              {"price": 220,  "category": "MCBs & Consumer Units"},
    "MCB 2P Cloak Andeli":            {"price": 220,  "category": "MCBs & Consumer Units"},
    "MCB 16A Andeli":                 {"price": 110,  "category": "MCBs & Consumer Units"},
    "MCB 20A Andeli":                 {"price": 110,  "category": "MCBs & Consumer Units"},
    "Consumer Unit Z-Y 2-4":          {"price": 200,  "category": "MCBs & Consumer Units"},
    "Consumer Unit Z-Y 4-6":          {"price": 300,  "category": "MCBs & Consumer Units"},
    "Consumer Unit Z-Y 6-8":          {"price": 850,  "category": "MCBs & Consumer Units"},
    "Element 4T":                     {"price": 350,  "category": "MCBs & Consumer Units"},
    "Fluorescent DLP 2ft":            {"price": 200,  "category": "Fluorescent Lighting"},
    "Fluorescent DLP 4ft":            {"price": 300,  "category": "Fluorescent Lighting"},
    "Shower Head Horizon":            {"price": 850,  "category": "Shower Fittings"},
    "Junction Box Big":               {"price": 70,   "category": "Accessories"},
    "Wood Screws (5pkts)":            {"price": 190,  "category": "Accessories"},
    "Top Plug Topnexas":              {"price": 30,   "category": "Accessories"},
    "Top Plug HLG":                   {"price": 75,   "category": "Accessories"},
    "Holder Angle HLG":               {"price": 65,   "category": "Accessories"},
    "Holder Straight HLG":            {"price": 65,   "category": "Accessories"},
    "DP Angle Holder":                {"price": 35,   "category": "Accessories"},
    "Small Straight Holder":          {"price": 30,   "category": "Accessories"},
    "TV Mast":                        {"price": 300,  "category": "Accessories"},
    "TV Guard Itol":                  {"price": 300,  "category": "Accessories"},
    "Fridge Guard Itol":              {"price": 35,   "category": "Accessories"},
    "PCB 2Y1":                        {"price": 16,   "category": "Accessories"},
    "Female Connector":               {"price": 10,   "category": "Accessories"},
    "Male Connector":                 {"price": 10,   "category": "Accessories"},
    "Plastic Jackpin":                {"price": 15,   "category": "Accessories"},
    "Meter Box Heavy Gauge":          {"price": 260,  "category": "Accessories"},
    "Earth Rod Small":                {"price": 100,  "category": "Accessories"},
    "DB Enclosure":                   {"price": 80,   "category": "Accessories"},
}

# ── Init DB & seed products ────────────────────────────────────────────────────
db.init_db()
db.seed_products(DEFAULT_PRODUCTS)

# ── Helpers ────────────────────────────────────────────────────────────────────
def get_products():
    p = db.load_products()
    return p if p else DEFAULT_PRODUCTS

def get_categories():
    return sorted(set(v["category"] for v in get_products().values()))

def search_products(query, threshold=60):
    results = []
    for name, info in get_products().items():
        score = fuzz.partial_ratio(query.lower(), name.lower())
        if score >= threshold:
            results.append((name, info, score))
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:8]

def get_by_category(category_query):
    return [(n, i) for n, i in get_products().items()
            if category_query.lower() in i["category"].lower()]

def build_product_context(user_message):
    context = ""
    for cat in get_categories():
        if cat.lower() in user_message.lower():
            items = get_by_category(cat)
            if items:
                icon = CATEGORY_ICONS.get(cat, "🔹")
                lines = [f"  • {n}: Ksh {i['price']:,}" for n, i in items]
                context += f"\n{icon} {cat}:\n" + "\n".join(lines)
    results = search_products(user_message)
    if results and not context:
        lines = [f"  • {n}: Ksh {i['price']:,}" for n, i, _ in results]
        context += "\n🔍 Matching products:\n" + "\n".join(lines)
    for word in user_message.upper().split():
        if word.startswith("NEV") and len(word) >= 7:
            order = db.get_order(word)
            if order:
                context += (f"\n📋 Order {word}:\n  Status: {order['status']}\n"
                            f"  Items: {order['items']}\n  Total: Ksh {order['total']:,}")
    return context

def track_faqs(message):
    for kw in FAQ_KEYWORDS:
        if kw in message.lower():
            db.increment_faq(kw)

def parse_order(phone, message):
    try:
        parts = message.replace("ORDER", "").strip().split("|")
        if len(parts) < 2: return None
        customer_name = parts[0].strip()
        items_text = ", ".join(p.strip() for p in parts[1:])
        total = 0
        for part in parts[1:]:
            for name, info in get_products().items():
                if fuzz.partial_ratio(part.lower(), name.lower()) > 70:
                    qty = 1
                    for word in part.split():
                        if word.isdigit(): qty = int(word)
                    total += info["price"] * qty
                    break
        order_id = db.get_next_order_id()
        db.save_order(order_id, phone, customer_name, items_text, total)
        return order_id, customer_name, items_text, total
    except Exception as e:
        logger.error(f"parse_order: {e}"); return None

def generate_ai_response(phone, user_message):
    history = db.get_conversation(phone)
    product_context = build_product_context(user_message)
    enhanced = user_message
    if product_context:
        enhanced = f"{user_message}\n\n[PRODUCT DATA:{product_context}]"
    history.append({"role": "user", "content": enhanced})
    recent = history[-10:]
    cats = ", ".join(get_categories())
    system = f"""You are a professional WhatsApp sales assistant for {SHOP_NAME} in {SHOP_LOCATION}.
Contacts: {SHOP_PHONE} | M-Pesa Paybill: {PAYBILL}, Account: {PAYBILL_ACC}.
Personality: warm, knowledgeable, professional.
- Help customers find products and prices in Ksh
- Take orders: ask name, confirm items/qty, then say reply with: ORDER Name | Item x Qty
- Track orders by Order ID (e.g. NEV1001)
- Cable brands: Tronic, ASL, Evin East Africa. Sizes: 1.0-6.0mm singles & twin earth
- Use *bold* for names/prices. Show prices as: Ksh X,XXX
- Product listings: • *Product Name* — Ksh X,XXX
- Categories: {cats}"""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system}] + recent,
            max_tokens=700, temperature=0.5,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq error: {e}")
        reply = f"⚠️ Technical issue. Call us: 📞 *{SHOP_PHONE}*"
    history.append({"role": "assistant", "content": reply})
    db.save_conversation(phone, history[-20:])
    return reply

# ── Message templates ──────────────────────────────────────────────────────────
def welcome_message():
    cats = get_categories()
    lines = [
        "╔══════════════════════════╗",
        "⚡  *NEVANSON ELECTRICALS*  ⚡",
        "     *& ELECTRONICS*",
        "╚══════════════════════════╝",
        "", "👋 *Welcome! How can we help you today?*", "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🛍️  *What would you like to do?*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━", "",
        "1️⃣  Browse products by category",
        "2️⃣  Search for a specific item",
        "3️⃣  Place an order",
        "4️⃣  Track my order",
        "5️⃣  Payment information",
        "6️⃣  Contact & location", "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📂 *Our Product Categories:*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━", "",
    ]
    for cat in cats:
        icon = CATEGORY_ICONS.get(cat, "🔹")
        lines.append(f"{icon}  {cat}")
    lines += ["", "━━━━━━━━━━━━━━━━━━━━━━━━━━",
              "💬 *Type a category name or describe what you need!*"]
    return "\n".join(lines)

def payment_message():
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n💳 *PAYMENT INFORMATION*\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ *M-Pesa Paybill*\n   📟 Paybill No: *{PAYBILL}*\n   🔢 Account No: *{PAYBILL_ACC}*\n\n"
        "📝 *How to pay:*\n   1. Go to M-Pesa\n   2. Select *Lipa na M-Pesa*\n"
        f"   3. Select *Pay Bill*\n   4. Business No: *{PAYBILL}*\n   5. Account No: *{PAYBILL_ACC}*\n"
        f"   6. Enter amount & confirm\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n📞 For help: *{SHOP_PHONE}*"
    )

def contact_message():
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n📍 *FIND US*\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏪 *{SHOP_NAME}*\n\n📌 *Location:*\n   {SHOP_LOCATION}\n\n"
        f"📞 *Call us:*\n   {SHOP_PHONE}\n\n"
        "🕒 *Business Hours:*\n   Mon – Sat: 8:00 AM – 6:00 PM\n   Sun: 9:00 AM – 2:00 PM\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n💬 We're always happy to help!"
    )

def order_confirm_message(order_id, items, total):
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ *ORDER CONFIRMED!*\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 *Order ID:* `{order_id}`\n🛒 *Items:* {items}\n💰 *Total: Ksh {total:,}*\n\n"
        f"💳 *Pay via M-Pesa:*\n   Paybill: *{PAYBILL}*\n   Account: *{PAYBILL_ACC}*\n"
        f"   Amount: *Ksh {total:,}*\n   Reference: *{order_id}*\n\n"
        f"📱 After payment, send: *PAID {order_id}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n📞 Need help? Call: *{SHOP_PHONE}*\nThank you for shopping with us! 🙏"
    )

# ══════════════════════════════════════════════════════════════════════════════
# WHATSAPP WEBHOOK
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
def home():
    return f"✅ {SHOP_NAME} Bot is running! Admin: /admin"

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming = request.form.get("Body", "").strip()
    phone    = request.form.get("From", "")
    logger.info(f"[{phone}] {incoming}")

    db.log_message(phone, incoming, "inbound")
    db.update_last_seen(phone)
    track_faqs(incoming)

    text_lower = incoming.lower().strip()

    # Admin takeover — bot stays silent
    if db.is_admin_takeover(phone):
        return str(MessagingResponse())

    # Payment confirmation
    if text_lower.startswith("paid "):
        order_id = text_lower.replace("paid ", "").strip().upper()
        order = db.get_order(order_id)
        if order:
            db.update_order_status(order_id, "Payment Received – Processing")
            reply = (f"✅ *Payment received for {order_id}!*\n\n"
                     f"Your order is being processed. We'll notify you when ready.\n"
                     f"📞 Questions? Call: *{SHOP_PHONE}*")
        else:
            reply = f"⚠️ Order ID *{order_id}* not found. Please check and try again."

    # Order command
    elif text_lower.startswith("order ") and "|" in incoming:
        result = parse_order(phone, incoming)
        if result:
            order_id, name, items, total = result
            reply = order_confirm_message(order_id, items, total)
        else:
            reply = ("⚠️ Order format not recognized. Use:\n\n"
                     "*ORDER Your Name | Item1 x Qty | Item2 x Qty*\n\n"
                     "Example:\n_ORDER John Doe | Socket Double x2 | 9W Bulb x4_")

    elif text_lower in ["hi","hello","hujambo","habari","hey","start","menu","0"]:
        reply = welcome_message()
    elif text_lower in ["payment","pay","mpesa","paybill","lipa","5"]:
        reply = payment_message()
    elif text_lower in ["contact","location","address","where","directions","6"]:
        reply = contact_message()
    else:
        reply = generate_ai_response(phone, incoming)

    db.log_message(phone, reply, "outbound")
    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN API
# ══════════════════════════════════════════════════════════════════════════════
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    if data.get("password") == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return jsonify({"success": True})
    return jsonify({"error": "Invalid password"}), 401

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/admin/metrics", methods=["GET"])
@admin_required
def get_metrics():
    return jsonify(db.get_metrics())

@app.route("/admin/orders", methods=["GET"])
@admin_required
def get_orders():
    return jsonify(db.get_all_orders())

@app.route("/admin/orders/<order_id>/status", methods=["PUT"])
@admin_required
def update_order(order_id):
    data = request.get_json()
    db.update_order_status(order_id, data.get("status"))
    return jsonify({"success": True})

@app.route("/admin/conversations", methods=["GET"])
@admin_required
def get_conversations():
    return jsonify(db.get_all_conversations())

@app.route("/admin/conversations/<path:phone>/takeover", methods=["POST"])
@admin_required
def takeover(phone):
    db.set_admin_takeover(phone, True)
    return jsonify({"success": True})

@app.route("/admin/conversations/<path:phone>/release", methods=["POST"])
@admin_required
def release(phone):
    db.set_admin_takeover(phone, False)
    return jsonify({"success": True})

@app.route("/admin/conversations/<path:phone>/send", methods=["POST"])
@admin_required
def admin_send(phone):
    data = request.get_json()
    message = data.get("message", "")
    db.log_message(phone, f"[ADMIN] {message}", "outbound")
    history = db.get_conversation(phone)
    history.append({"role": "assistant", "content": message})
    db.save_conversation(phone, history[-20:])
    return jsonify({"success": True})

@app.route("/admin/messages", methods=["GET"])
@admin_required
def get_messages():
    limit = int(request.args.get("limit", 200))
    return jsonify(db.get_messages(limit))

@app.route("/admin/products", methods=["GET"])
@admin_required
def get_products_api():
    return jsonify(get_products())

@app.route("/admin/products", methods=["POST"])
@admin_required
def add_product():
    data = request.get_json()
    name = data.get("name","").strip()
    if not name: return jsonify({"error": "Name required"}), 400
    db.add_product(name, int(data.get("price", 0)), data.get("category","Accessories"))
    return jsonify({"success": True})

@app.route("/admin/products/<path:name>/price", methods=["PUT"])
@admin_required
def update_price(name):
    data = request.get_json()
    db.update_product_price(name, int(data.get("price", 0)))
    return jsonify({"success": True})

@app.route("/admin/products/<path:name>/rename", methods=["PUT"])
@admin_required
def rename_product(name):
    data = request.get_json()
    new_name = data.get("new_name","").strip()
    if not new_name: return jsonify({"error": "New name required"}), 400
    products = get_products()
    if new_name in products: return jsonify({"error": "Name already exists"}), 400
    db.rename_product(name, new_name)
    return jsonify({"success": True})

@app.route("/admin/products/<path:name>", methods=["DELETE"])
@admin_required
def del_product(name):
    db.delete_product(name)
    return jsonify({"success": True})

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD HTML
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/admin")
@app.route("/admin/")
def admin_dashboard():
    return render_template_string(DASHBOARD_HTML)

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Nevanson Admin</title>
<style>
:root{--bg:#0a0e1a;--surface:#111827;--surface2:#1a2235;--border:#1e2d45;--accent:#f59e0b;--green:#10b981;--red:#ef4444;--blue:#60a5fa;--text:#e2e8f0;--muted:#64748b}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}
#login-screen{display:flex;align-items:center;justify-content:center;min-height:100vh}
.login-card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:48px;width:380px;text-align:center}
.login-logo{font-size:48px;margin-bottom:16px}
.login-title{font-size:22px;font-weight:700;color:var(--accent);margin-bottom:6px}
.login-sub{color:var(--muted);font-size:13px;margin-bottom:32px}
.login-input{width:100%;padding:12px 16px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:15px;margin-bottom:16px;outline:none}
.login-input:focus{border-color:var(--accent)}
.login-btn{width:100%;padding:13px;background:var(--accent);color:#000;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer}
.login-btn:hover{opacity:.85}
.login-error{color:var(--red);font-size:13px;margin-top:10px}
#app{display:none;flex-direction:column;min-height:100vh}
.topbar{background:var(--surface);border-bottom:1px solid var(--border);padding:0 24px;height:60px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.topbar-brand{display:flex;align-items:center;gap:10px}
.topbar-name{font-weight:700;color:var(--accent);font-size:15px}
.topbar-sub{color:var(--muted);font-size:11px}
.live-dot{width:8px;height:8px;background:var(--green);border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.logout-btn{padding:7px 16px;background:transparent;border:1px solid var(--border);color:var(--muted);border-radius:6px;cursor:pointer;font-size:13px}
.logout-btn:hover{border-color:var(--red);color:var(--red)}
.main-layout{display:flex;flex:1}
.sidebar{width:220px;background:var(--surface);border-right:1px solid var(--border);padding:20px 0;position:sticky;top:60px;height:calc(100vh - 60px);overflow-y:auto}
.nav-label{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);padding:8px 24px 4px}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 24px;cursor:pointer;color:var(--muted);font-size:14px;transition:all .15s;margin-bottom:2px}
.nav-item:hover{background:var(--surface2);color:var(--text)}
.nav-item.active{background:rgba(245,158,11,.15);color:var(--accent);border-right:3px solid var(--accent)}
.content{flex:1;padding:28px;overflow-y:auto}
.page{display:none}.page.active{display:block}
.page-title{font-size:22px;font-weight:700;margin-bottom:4px}
.page-sub{color:var(--muted);font-size:13px;margin-bottom:28px}
.metrics-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:16px;margin-bottom:28px}
.metric-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px}
.metric-icon{font-size:24px;margin-bottom:10px}
.metric-value{font-size:30px;font-weight:800;color:var(--accent)}
.metric-label{font-size:12px;color:var(--muted);margin-top:4px}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px}
.card-title{font-size:14px;font-weight:700;margin-bottom:16px;color:var(--accent)}
.faq-item{margin-bottom:10px}
.faq-row{display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px}
.faq-bar{height:6px;background:var(--border);border-radius:3px;overflow:hidden}
.faq-fill{height:100%;background:var(--accent);border-radius:3px;transition:width .5s}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 14px;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)}
td{padding:12px 14px;border-bottom:1px solid var(--border);vertical-align:middle}
tr:hover td{background:var(--surface2)}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.badge-yellow{background:rgba(245,158,11,.15);color:var(--accent)}
.badge-green{background:rgba(16,185,129,.15);color:var(--green)}
.badge-red{background:rgba(239,68,68,.15);color:var(--red)}
.badge-blue{background:rgba(96,165,250,.15);color:var(--blue)}
.btn{padding:7px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;border:none;transition:opacity .2s}
.btn:hover{opacity:.8}
.btn-primary{background:var(--accent);color:#000}
.btn-danger{background:var(--red);color:#fff}
.btn-ghost{background:var(--surface2);color:var(--text);border:1px solid var(--border)}
.btn-green{background:var(--green);color:#fff}
.btn-blue{background:var(--blue);color:#000}
.conv-list{display:grid;grid-template-columns:280px 1fr;height:72vh;border:1px solid var(--border);border-radius:12px;overflow:hidden}
.conv-sidebar{background:var(--surface);border-right:1px solid var(--border);overflow-y:auto;display:flex;flex-direction:column}
.conv-search{padding:12px;border-bottom:1px solid var(--border)}
.conv-search input{width:100%;padding:8px 12px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;outline:none}
.conv-item{padding:14px 16px;border-bottom:1px solid var(--border);cursor:pointer;transition:background .15s}
.conv-item:hover{background:var(--surface2)}
.conv-item.active{background:rgba(245,158,11,.1);border-left:3px solid var(--accent)}
.conv-phone{font-size:13px;font-weight:600}
.conv-preview{font-size:11px;color:var(--muted);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.conv-meta{display:flex;justify-content:space-between;align-items:center}
.conv-time{font-size:10px;color:var(--muted)}
.takeover-badge{font-size:9px;background:var(--red);color:#fff;padding:2px 6px;border-radius:4px}
.chat-panel{display:flex;flex-direction:column;background:var(--bg)}
.chat-header{padding:16px 20px;background:var(--surface);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.chat-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px}
.msg{max-width:72%;padding:10px 14px;border-radius:12px;font-size:13px;line-height:1.5;word-break:break-word}
.msg-in{background:var(--surface2);align-self:flex-start;border-bottom-left-radius:4px}
.msg-out{background:rgba(245,158,11,.12);align-self:flex-end;border-bottom-right-radius:4px}
.msg-admin{background:rgba(239,68,68,.15);align-self:flex-end;border-bottom-right-radius:4px}
.chat-input-area{padding:12px 16px;background:var(--surface);border-top:1px solid var(--border);display:flex;gap:10px}
.chat-input{flex:1;padding:10px 14px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;outline:none}
.chat-input:focus{border-color:var(--accent)}
.no-conv-msg{display:flex;align-items:center;justify-content:center;flex:1;color:var(--muted);font-size:14px}
.products-toolbar{display:flex;gap:12px;margin-bottom:20px;align-items:center;flex-wrap:wrap}
.search-input{flex:1;min-width:200px;padding:10px 14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;outline:none}
.search-input:focus{border-color:var(--accent)}
.price-input{width:90px;padding:6px 10px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;outline:none;text-align:right}
.price-input:focus{border-color:var(--accent)}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:28px;width:440px;max-width:95vw}
.modal-title{font-size:17px;font-weight:700;margin-bottom:20px}
.form-group{margin-bottom:16px}
.form-label{font-size:12px;color:var(--muted);margin-bottom:6px;display:block}
.form-input,.form-select{width:100%;padding:10px 14px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;outline:none}
.form-input:focus,.form-select:focus{border-color:var(--accent)}
.modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}
.toast{position:fixed;bottom:24px;right:24px;background:var(--surface);border:1px solid var(--green);border-radius:8px;padding:12px 20px;font-size:13px;color:var(--green);z-index:9999;transform:translateY(80px);opacity:0;transition:all .3s}
.toast.show{transform:translateY(0);opacity:1}
.empty-state{text-align:center;padding:48px;color:var(--muted)}
.empty-icon{font-size:40px;margin-bottom:12px}
</style>
</head>
<body>

<div id="login-screen">
  <div class="login-card">
    <div class="login-logo">⚡</div>
    <div class="login-title">Nevanson Admin</div>
    <div class="login-sub">Sign in to access the dashboard</div>
    <input type="password" class="login-input" id="pw-input" placeholder="Enter password" onkeydown="if(event.key==='Enter')doLogin()">
    <button class="login-btn" onclick="doLogin()">Sign In</button>
    <div class="login-error" id="login-error"></div>
  </div>
</div>

<div id="app">
  <div class="topbar">
    <div class="topbar-brand">
      <span style="font-size:22px">⚡</span>
      <div><div class="topbar-name">Nevanson Electricals</div><div class="topbar-sub">Admin Dashboard</div></div>
    </div>
    <div style="display:flex;align-items:center;gap:12px">
      <div class="live-dot"></div>
      <span style="font-size:12px;color:var(--muted)">Live</span>
      <button class="logout-btn" onclick="doLogout()">Sign out</button>
    </div>
  </div>
  <div class="main-layout">
    <div class="sidebar">
      <div class="nav-label">Overview</div>
      <div class="nav-item active" onclick="showPage('metrics',this)">📊 Dashboard</div>
      <div class="nav-item" onclick="showPage('orders',this)">🛒 Orders</div>
      <div class="nav-label">Communication</div>
      <div class="nav-item" onclick="showPage('conversations',this)">💬 Conversations</div>
      <div class="nav-item" onclick="showPage('messages',this)">📨 Message Log</div>
      <div class="nav-label">Catalogue</div>
      <div class="nav-item" onclick="showPage('products',this)">📦 Products & Prices</div>
    </div>
    <div class="content">

      <!-- METRICS -->
      <div class="page active" id="page-metrics">
        <div class="page-title">Dashboard</div>
        <div class="page-sub">Real-time overview of your WhatsApp bot</div>
        <div class="metrics-grid">
          <div class="metric-card"><div class="metric-icon">👥</div><div class="metric-value" id="m-users">—</div><div class="metric-label">Total Users</div></div>
          <div class="metric-card"><div class="metric-icon">🟢</div><div class="metric-value" id="m-1h">—</div><div class="metric-label">Active (Last Hour)</div></div>
          <div class="metric-card"><div class="metric-icon">📅</div><div class="metric-value" id="m-24h">—</div><div class="metric-label">Active (Last 24h)</div></div>
          <div class="metric-card"><div class="metric-icon">💬</div><div class="metric-value" id="m-msgs">—</div><div class="metric-label">Total Messages</div></div>
          <div class="metric-card"><div class="metric-icon">🛒</div><div class="metric-value" id="m-orders">—</div><div class="metric-label">Total Orders</div></div>
          <div class="metric-card"><div class="metric-icon">⏳</div><div class="metric-value" id="m-pending">—</div><div class="metric-label">Pending Orders</div></div>
          <div class="metric-card"><div class="metric-icon">✅</div><div class="metric-value" id="m-paid">—</div><div class="metric-label">Paid Orders</div></div>
          <div class="metric-card"><div class="metric-icon">💰</div><div class="metric-value" id="m-revenue">—</div><div class="metric-label">Revenue (Ksh)</div></div>
        </div>
        <div class="two-col">
          <div class="card"><div class="card-title">🔥 Top Questions Asked</div><div id="faq-list"><div class="empty-state"><div class="empty-icon">💬</div>No data yet</div></div></div>
          <div class="card"><div class="card-title">🛒 Recent Orders</div><div id="recent-orders"></div></div>
        </div>
      </div>

      <!-- ORDERS -->
      <div class="page" id="page-orders">
        <div class="page-title">Orders</div>
        <div class="page-sub">Manage and update customer orders</div>
        <div class="card"><div class="table-wrap">
          <table><thead><tr><th>Order ID</th><th>Customer</th><th>Items</th><th>Total</th><th>Status</th><th>Time</th><th>Update</th></tr></thead>
          <tbody id="orders-tbody"><tr><td colspan="7" style="text-align:center;color:var(--muted);padding:32px">No orders yet</td></tr></tbody></table>
        </div></div>
      </div>

      <!-- CONVERSATIONS -->
      <div class="page" id="page-conversations">
        <div class="page-title">Conversations</div>
        <div class="page-sub">Monitor chats and take over conversations from the bot</div>
        <div class="conv-list">
          <div class="conv-sidebar">
            <div class="conv-search"><input placeholder="Search by phone…" oninput="filterConvs(this.value)"></div>
            <div id="conv-items" style="flex:1;overflow-y:auto"></div>
          </div>
          <div class="chat-panel" id="chat-panel"><div class="no-conv-msg">Select a conversation</div></div>
        </div>
      </div>

      <!-- MESSAGES -->
      <div class="page" id="page-messages">
        <div class="page-title">Message Log</div>
        <div class="page-sub">All inbound and outbound messages — stored permanently</div>
        <div class="card"><div class="table-wrap">
          <table><thead><tr><th>Time</th><th>Phone</th><th>Direction</th><th>Message</th></tr></thead>
          <tbody id="messages-tbody"></tbody></table>
        </div></div>
      </div>

      <!-- PRODUCTS -->
      <div class="page" id="page-products">
        <div class="page-title">Products & Prices</div>
        <div class="page-sub">Update prices, rename, add or remove products instantly</div>
        <div class="products-toolbar">
          <input class="search-input" placeholder="Search products…" oninput="filterProducts(this.value)">
          <select class="search-input" style="max-width:200px" id="cat-filter" onchange="filterByCategory(this.value)">
            <option value="">All Categories</option>
          </select>
          <button class="btn btn-primary" onclick="openAddModal()">+ Add Product</button>
        </div>
        <div class="card"><div class="table-wrap">
          <table><thead><tr><th>Product</th><th>Category</th><th>Price (Ksh)</th><th>Actions</th></tr></thead>
          <tbody id="products-tbody"></tbody></table>
        </div></div>
      </div>

    </div>
  </div>
</div>

<!-- RENAME MODAL -->
<div class="modal-overlay" id="rename-modal">
  <div class="modal">
    <div class="modal-title">✏️ Rename Product</div>
    <div class="form-group"><label class="form-label">Current Name</label><input class="form-input" id="rename-old" disabled style="opacity:.5"></div>
    <div class="form-group"><label class="form-label">New Name</label><input class="form-input" id="rename-new" placeholder="Enter new product name"></div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('rename-modal')">Cancel</button>
      <button class="btn btn-primary" onclick="submitRename()">Rename</button>
    </div>
  </div>
</div>

<!-- ADD PRODUCT MODAL -->
<div class="modal-overlay" id="add-modal">
  <div class="modal">
    <div class="modal-title">➕ Add New Product</div>
    <div class="form-group"><label class="form-label">Product Name</label><input class="form-input" id="new-name" placeholder="e.g. 15W LED Bulb"></div>
    <div class="form-group"><label class="form-label">Category</label><select class="form-select" id="new-cat"></select></div>
    <div class="form-group"><label class="form-label">Price (Ksh)</label><input class="form-input" id="new-price" type="number" placeholder="e.g. 150"></div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('add-modal')">Cancel</button>
      <button class="btn btn-primary" onclick="submitAdd()">Add Product</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const API = '';
let allProducts = {}, allConvs = {}, selectedPhone = null;

// ── Auth ──────────────────────────────────────────────────────────────────────
async function doLogin() {
  const pw = document.getElementById('pw-input').value;
  const res = await fetch(API+'/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})});
  if (res.ok) {
    document.getElementById('login-screen').style.display='none';
    document.getElementById('app').style.display='flex';
    startApp();
  } else {
    document.getElementById('login-error').textContent='Wrong password. Try again.';
  }
}
async function doLogout() { await fetch(API+'/admin/logout',{method:'POST'}); location.reload(); }

// ── Nav ───────────────────────────────────────────────────────────────────────
function showPage(name, el) {
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('page-'+name).classList.add('active');
  el.classList.add('active');
  const loaders = {metrics:loadMetrics,orders:loadOrders,conversations:loadConvs,messages:loadMessages,products:loadProducts};
  if (loaders[name]) loaders[name]();
}

function startApp() {
  loadMetrics();
  setInterval(loadMetrics, 10000);
}

// ── Metrics ───────────────────────────────────────────────────────────────────
async function loadMetrics() {
  const res = await fetch(API+'/admin/metrics');
  if (!res.ok) return;
  const d = await res.json();
  document.getElementById('m-users').textContent   = d.total_users||0;
  document.getElementById('m-1h').textContent      = d.active_users_1h||0;
  document.getElementById('m-24h').textContent     = d.active_users_24h||0;
  document.getElementById('m-msgs').textContent    = d.total_messages||0;
  document.getElementById('m-orders').textContent  = d.total_orders||0;
  document.getElementById('m-pending').textContent = d.pending_orders||0;
  document.getElementById('m-paid').textContent    = d.paid_orders||0;
  document.getElementById('m-revenue').textContent = 'Ksh '+(d.total_revenue||0).toLocaleString();
  // FAQ
  const faqEl = document.getElementById('faq-list');
  if (d.top_faqs && d.top_faqs.length) {
    const max = d.top_faqs[0][1]||1;
    faqEl.innerHTML = d.top_faqs.map(([kw,cnt])=>`
      <div class="faq-item">
        <div class="faq-row"><span>${kw}</span><span style="color:var(--accent);font-weight:700">${cnt}</span></div>
        <div class="faq-bar"><div class="faq-fill" style="width:${(cnt/max*100).toFixed(0)}%"></div></div>
      </div>`).join('');
  }
  // Recent orders
  const or = await fetch(API+'/admin/orders');
  if (or.ok) {
    const ords = await or.json();
    const el = document.getElementById('recent-orders');
    if (ords.length) {
      el.innerHTML = ords.slice(0,5).map(o=>`
        <div style="padding:10px 0;border-bottom:1px solid var(--border);font-size:13px">
          <div style="display:flex;justify-content:space-between">
            <span style="font-weight:700;color:var(--accent)">${o.order_id}</span>
            ${badgeHtml(o.status)}
          </div>
          <div style="color:var(--muted);margin-top:3px">${o.customer_name||o.phone} · Ksh ${(o.total||0).toLocaleString()}</div>
        </div>`).join('');
    } else {
      el.innerHTML='<div class="empty-state"><div class="empty-icon">🛒</div>No orders yet</div>';
    }
  }
}

// ── Orders ────────────────────────────────────────────────────────────────────
async function loadOrders() {
  const res = await fetch(API+'/admin/orders');
  const orders = await res.json();
  const tbody = document.getElementById('orders-tbody');
  if (!orders.length) {
    tbody.innerHTML='<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:32px">No orders yet</td></tr>'; return;
  }
  tbody.innerHTML = orders.map(o=>`<tr>
    <td><strong style="color:var(--accent)">${o.order_id}</strong></td>
    <td>${o.customer_name||'—'}<br><span style="color:var(--muted);font-size:11px">${o.phone}</span></td>
    <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${o.items}">${o.items}</td>
    <td><strong>Ksh ${(o.total||0).toLocaleString()}</strong></td>
    <td>${badgeHtml(o.status)}</td>
    <td style="color:var(--muted);font-size:11px">${o.timestamp?new Date(o.timestamp).toLocaleString():'—'}</td>
    <td><select style="background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:6px;font-size:12px" onchange="updateStatus('${o.order_id}',this.value)">
      ${['Pending Payment','Payment Received – Processing','Ready for Pickup','Completed','Cancelled'].map(s=>`<option ${o.status===s?'selected':''}>${s}</option>`).join('')}
    </select></td>
  </tr>`).join('');
}

async function updateStatus(id, status) {
  await fetch(API+'/admin/orders/'+id+'/status',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
  showToast('Order '+id+' updated to: '+status);
}

function badgeHtml(s) {
  if (!s) return '';
  const cls = s.includes('Pending')?'badge-yellow':s.includes('Payment Received')?'badge-blue':s.includes('Ready')||s.includes('Completed')?'badge-green':'badge-red';
  return `<span class="badge ${cls}">${s}</span>`;
}

// ── Conversations ──────────────────────────────────────────────────────────────
let convInterval = null;
async function loadConvs() {
  const res = await fetch(API+'/admin/conversations');
  allConvs = await res.json();
  renderConvList(allConvs);
  if (selectedPhone) renderChat(selectedPhone);
  if (convInterval) clearInterval(convInterval);
  convInterval = setInterval(async()=>{
    const r = await fetch(API+'/admin/conversations');
    allConvs = await r.json();
    renderConvList(allConvs);
    if (selectedPhone) renderChat(selectedPhone);
  }, 15000);
}

function renderConvList(convs) {
  const el = document.getElementById('conv-items');
  const phones = Object.keys(convs);
  if (!phones.length) { el.innerHTML='<div class="empty-state" style="padding:32px"><div class="empty-icon">💬</div>No conversations yet</div>'; return; }
  el.innerHTML = phones.map(phone=>{
    const c = convs[phone];
    const msgs = c.messages||[];
    const last = msgs.length?msgs[msgs.length-1].content:'';
    const preview = last.replace(/\*/g,'').substring(0,45)+(last.length>45?'…':'');
    return `<div class="conv-item ${selectedPhone===phone?'active':''}" onclick="selectConv('${phone}')">
      <div class="conv-meta">
        <span class="conv-phone">${phone.replace('whatsapp:','')}</span>
        ${c.admin_takeover?'<span class="takeover-badge">ADMIN</span>':''}
      </div>
      <div class="conv-preview">${preview||'No messages'}</div>
      <div class="conv-meta" style="margin-top:4px">
        <span class="conv-time">${c.last_seen?new Date(c.last_seen).toLocaleTimeString():''}</span>
        <span style="font-size:10px;color:var(--muted)">${c.order_count||0} order${c.order_count!==1?'s':''}</span>
      </div>
    </div>`;
  }).join('');
}

function filterConvs(q) {
  const f={};Object.keys(allConvs).forEach(p=>{if(p.includes(q))f[p]=allConvs[p];});renderConvList(f);
}

function selectConv(phone) {
  selectedPhone=phone; renderConvList(allConvs); renderChat(phone);
}

function renderChat(phone) {
  const c = allConvs[phone]; if (!c) return;
  const msgs = c.messages||[];
  const panel = document.getElementById('chat-panel');
  panel.innerHTML = `
    <div class="chat-header">
      <div>
        <div style="font-weight:600;font-size:14px">${phone.replace('whatsapp:','')}</div>
        <div style="font-size:11px;color:var(--muted)">${c.admin_takeover?'🔴 Admin control':'🤖 Bot control'} · ${c.order_count||0} orders</div>
      </div>
      <div style="display:flex;gap:8px">
        ${c.admin_takeover
          ?`<button class="btn btn-green" onclick="releaseConv('${phone}')">🤖 Return to Bot</button>`
          :`<button class="btn btn-danger" onclick="takeoverConv('${phone}')">👤 Take Over</button>`}
      </div>
    </div>
    <div class="chat-messages" id="chat-msgs">
      ${msgs.length?msgs.map(m=>`<div><div class="msg ${m.role==='user'?'msg-in':m.content.startsWith('[ADMIN]')?'msg-admin':'msg-out'}">${m.content.replace(/</g,'&lt;').replace(/\n/g,'<br>').replace(/\*(.*?)\*/g,'<strong>$1</strong>')}</div></div>`).join(''):'<div style="text-align:center;color:var(--muted);padding:32px">No messages yet</div>'}
    </div>
    ${c.admin_takeover?`
    <div class="chat-input-area">
      <input class="chat-input" id="admin-input" placeholder="Type a message as admin…" onkeydown="if(event.key==='Enter')sendAdminMsg('${phone}')">
      <button class="btn btn-primary" onclick="sendAdminMsg('${phone}')">Send</button>
    </div>`:`<div style="padding:10px 16px;background:var(--surface);border-top:1px solid var(--border);font-size:12px;color:var(--muted);text-align:center">Bot is handling this conversation. Take over to send messages.</div>`}`;
  const msgsEl = document.getElementById('chat-msgs');
  if (msgsEl) msgsEl.scrollTop = msgsEl.scrollHeight;
}

async function takeoverConv(phone) {
  await fetch(API+'/admin/conversations/'+encodeURIComponent(phone)+'/takeover',{method:'POST'});
  allConvs[phone].admin_takeover=true; renderConvList(allConvs); renderChat(phone); showToast('Admin takeover active');
}
async function releaseConv(phone) {
  await fetch(API+'/admin/conversations/'+encodeURIComponent(phone)+'/release',{method:'POST'});
  allConvs[phone].admin_takeover=false; renderConvList(allConvs); renderChat(phone); showToast('Returned to bot control');
}
async function sendAdminMsg(phone) {
  const input = document.getElementById('admin-input');
  const msg = input.value.trim(); if (!msg) return;
  await fetch(API+'/admin/conversations/'+encodeURIComponent(phone)+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
  input.value='';
  const r = await fetch(API+'/admin/conversations'); allConvs=await r.json(); renderChat(phone); showToast('Message sent');
}

// ── Messages ──────────────────────────────────────────────────────────────────
async function loadMessages() {
  const res = await fetch(API+'/admin/messages?limit=200');
  const msgs = await res.json();
  const tbody = document.getElementById('messages-tbody');
  if (!msgs.length) { tbody.innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:32px">No messages yet</td></tr>'; return; }
  tbody.innerHTML = msgs.map(m=>`<tr>
    <td style="color:var(--muted);font-size:11px;white-space:nowrap">${new Date(m.timestamp).toLocaleString()}</td>
    <td style="font-size:12px">${m.phone.replace('whatsapp:','')}</td>
    <td><span class="badge ${m.direction==='inbound'?'badge-blue':'badge-green'}">${m.direction}</span></td>
    <td style="font-size:12px;max-width:350px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${m.message.replace(/</g,'&lt;').substring(0,120)}</td>
  </tr>`).join('');
}

// ── Products ──────────────────────────────────────────────────────────────────
async function loadProducts() {
  const res = await fetch(API+'/admin/products');
  allProducts = await res.json();
  renderProducts(allProducts);
  const cats = [...new Set(Object.values(allProducts).map(p=>p.category))].sort();
  document.getElementById('cat-filter').innerHTML='<option value="">All Categories</option>'+cats.map(c=>`<option>${c}</option>`).join('');
  document.getElementById('new-cat').innerHTML=cats.map(c=>`<option>${c}</option>`).join('');
}

function renderProducts(products) {
  const tbody = document.getElementById('products-tbody');
  const entries = Object.entries(products);
  if (!entries.length) { tbody.innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:32px">No products</td></tr>'; return; }
  tbody.innerHTML = entries.map(([name,info])=>`<tr>
    <td style="font-weight:600">${name}</td>
    <td><span class="badge badge-blue">${info.category}</span></td>
    <td><div style="display:flex;align-items:center;gap:8px">
      <span style="color:var(--muted);font-size:11px">Ksh</span>
      <input class="price-input" type="number" value="${info.price}" id="pr-${btoa(encodeURIComponent(name)).replace(/[=+/]/g,'_')}">
      <button class="btn btn-primary" onclick="savePrice(${JSON.stringify(name)})">Save</button>
    </div></td>
    <td style="display:flex;gap:6px">
      <button class="btn btn-ghost" onclick="openRename(${JSON.stringify(name)})">✏️ Rename</button>
      <button class="btn btn-danger" onclick="delProduct(${JSON.stringify(name)})">Delete</button>
    </td>
  </tr>`).join('');
}

function filterProducts(q) {
  const f={};Object.entries(allProducts).forEach(([k,v])=>{if(k.toLowerCase().includes(q.toLowerCase()))f[k]=v;});renderProducts(f);
}
function filterByCategory(cat) {
  if (!cat) { renderProducts(allProducts); return; }
  const f={};Object.entries(allProducts).forEach(([k,v])=>{if(v.category===cat)f[k]=v;});renderProducts(f);
}

async function savePrice(name) {
  const key = btoa(encodeURIComponent(name)).replace(/[=+/]/g,'_');
  const price = parseInt(document.getElementById('pr-'+key).value);
  await fetch(API+'/admin/products/'+encodeURIComponent(name)+'/price',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({price})});
  showToast('Price updated: '+name);
}

async function delProduct(name) {
  if (!confirm('Delete "'+name+'"?')) return;
  await fetch(API+'/admin/products/'+encodeURIComponent(name),{method:'DELETE'});
  await loadProducts(); showToast('Deleted: '+name);
}

function openRename(name) {
  document.getElementById('rename-old').value=name;
  document.getElementById('rename-new').value=name;
  document.getElementById('rename-modal').classList.add('open');
  setTimeout(()=>document.getElementById('rename-new').focus(),100);
}

async function submitRename() {
  const oldName=document.getElementById('rename-old').value;
  const newName=document.getElementById('rename-new').value.trim();
  if (!newName||newName===oldName) { closeModal('rename-modal'); return; }
  const res = await fetch(API+'/admin/products/'+encodeURIComponent(oldName)+'/rename',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({new_name:newName})});
  const d = await res.json();
  if (res.ok) { closeModal('rename-modal'); await loadProducts(); showToast('Renamed to: '+newName); }
  else showToast('Error: '+d.error);
}

function openAddModal() { document.getElementById('add-modal').classList.add('open'); }

async function submitAdd() {
  const name=document.getElementById('new-name').value.trim();
  const cat=document.getElementById('new-cat').value;
  const price=parseInt(document.getElementById('new-price').value);
  if (!name||!price) { showToast('Fill in all fields'); return; }
  await fetch(API+'/admin/products',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,category:cat,price})});
  closeModal('add-modal');
  document.getElementById('new-name').value='';
  document.getElementById('new-price').value='';
  await loadProducts(); showToast('Added: '+name);
}

function closeModal(id) { document.getElementById(id).classList.remove('open'); }

function showToast(msg) {
  const t=document.getElementById('toast');
  t.textContent='✅ '+msg; t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3000);
}
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
