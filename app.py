import os
import logging
from flask import Flask, request
from groq import Groq
from fuzzywuzzy import fuzz
from twilio.twiml.messaging_response import MessagingResponse

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Env vars ─────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
groq_client  = Groq(api_key=GROQ_API_KEY)

# ── In-memory stores ──────────────────────────────────────────────────────────
conversations = {}
orders        = {}
order_counter = [1000]

# ── Shop details ──────────────────────────────────────────────────────────────
SHOP_NAME     = "NEVANSON ELECTRICALS & ELECTRONICS"
SHOP_PHONE    = "0741311041 / 0720799896"
SHOP_LOCATION = "Mogogosiek Town – Opposite Stabex Petrol Station"
PAYBILL       = "522533"
PAYBILL_ACC   = "8093799"

PRODUCTS = {
    # ── BULBS ──
    "5W AC Bulb (Yomy)":              {"price": 40,   "category": "Bulbs"},
    "7W AC Bulb (Yomy)":              {"price": 45,   "category": "Bulbs"},
    "9W AC Bulb (Yomy)":              {"price": 35,   "category": "Bulbs"},
    "5W AC Bulb (Hommie)":            {"price": 40,   "category": "Bulbs"},
    "7W AC Bulb (Hommie)":            {"price": 45,   "category": "Bulbs"},
    "9W AC Bulb (Hommie)":            {"price": 50,   "category": "Bulbs"},
    "12W AC Bulb (Hommie)":           {"price": 750,  "category": "Bulbs"},
    # ── FLOODLIGHTS ──
    "50W AC Floodlight":              {"price": 1200, "category": "Floodlights"},
    "100W LED Floodlight (Atta)":     {"price": 230,  "category": "Floodlights"},
    "18W Bulkhead (Atta)":            {"price": 280,  "category": "Floodlights"},
    "24W Bulkhead (Atta)":            {"price": 280,  "category": "Floodlights"},
    # ── SWITCHES ──
    "19.2W Switch":                   {"price": 60,   "category": "Switches"},
    "29.2W Switch":                   {"price": 75,   "category": "Switches"},
    "39.2W Switch":                   {"price": 100,  "category": "Switches"},
    "DP Switch 45A":                  {"price": 300,  "category": "Switches"},
    "4G 2W Switch (Casher)":          {"price": 200,  "category": "Switches"},
    # ── SOCKETS ──
    "Socket Single":                  {"price": 80,   "category": "Sockets"},
    "Socket Double":                  {"price": 160,  "category": "Sockets"},
    "Socket Double 13A Tronic":       {"price": 300,  "category": "Sockets"},
    "Socket Single Double":           {"price": 3300, "category": "Sockets"},
    "Extension Socket Plk Sw":        {"price": 230,  "category": "Sockets"},
    # ── CONDUIT & TRUNKING ──
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
    # ── CABLES ──
    "Cable Single Tronic 1.5 (R7B)":  {"price": 5400, "category": "Cables"},
    "Cable Single Tronic 2.5 (R7B)":  {"price": 3,    "category": "Cables"},
    # ── MCBs / CONSUMER UNITS ──
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
    # ── FLUORESCENT ──
    "Fluorescent DLP 2ft":            {"price": 200,  "category": "Fluorescent Lighting"},
    "Fluorescent DLP 4ft":            {"price": 300,  "category": "Fluorescent Lighting"},
    # ── SHOWER ──
    "Shower Head Horizon":            {"price": 850,  "category": "Shower Fittings"},
    # ── ACCESSORIES ──
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

CATEGORIES = sorted(set(v["category"] for v in PRODUCTS.values()))

CATEGORY_ICONS = {
    "Accessories":           "🔧",
    "Bulbs":                 "💡",
    "Cables":                "🔌",
    "Conduit & Trunking":    "📦",
    "Floodlights":           "🔦",
    "Fluorescent Lighting":  "🕯️",
    "MCBs & Consumer Units": "⚡",
    "Shower Fittings":       "🚿",
    "Sockets":               "🔌",
    "Switches":              "🔘",
}

# ── Welcome message ───────────────────────────────────────────────────────────
def welcome_message():
    lines = [
        "╔══════════════════════════╗",
        "⚡  *NEVANSON ELECTRICALS*  ⚡",
        "     *& ELECTRONICS*",
        "╚══════════════════════════╝",
        "",
        "👋 *Welcome! How can we help you today?*",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🛍️  *What would you like to do?*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "1️⃣  Browse products by category",
        "2️⃣  Search for a specific item",
        "3️⃣  Place an order",
        "4️⃣  Track my order",
        "5️⃣  Payment information",
        "6️⃣  Contact & location",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📂 *Our Product Categories:*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    for cat in CATEGORIES:
        icon = CATEGORY_ICONS.get(cat, "🔹")
        lines.append(f"{icon}  {cat}")
    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💬 *Just type a category name or*",
        "    *describe what you need!*",
    ]
    return "\n".join(lines)

def payment_message():
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💳 *PAYMENT INFORMATION*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *M-Pesa Paybill*\n"
        f"   📟 Paybill No: *{PAYBILL}*\n"
        f"   🔢 Account No: *{PAYBILL_ACC}*\n\n"
        "📝 *How to pay:*\n"
        "   1. Go to M-Pesa\n"
        "   2. Select *Lipa na M-Pesa*\n"
        "   3. Select *Pay Bill*\n"
        f"   4. Enter Business No: *{PAYBILL}*\n"
        f"   5. Enter Account No: *{PAYBILL_ACC}*\n"
        "   6. Enter amount & confirm\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📞 For assistance call us:\n"
        f"   *{SHOP_PHONE}*"
    )

def contact_message():
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📍 *FIND US*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏪 *{SHOP_NAME}*\n\n"
        f"📌 *Location:*\n   {SHOP_LOCATION}\n\n"
        f"📞 *Call us:*\n   {SHOP_PHONE}\n\n"
        "🕒 *Business Hours:*\n"
        "   Mon – Sat: 8:00 AM – 6:00 PM\n"
        "   Sun: 9:00 AM – 2:00 PM\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💬 We're always happy to help!"
    )

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are a friendly and professional WhatsApp sales assistant for {SHOP_NAME},
an electrical and electronics shop in {SHOP_LOCATION}.
Contacts: {SHOP_PHONE} | M-Pesa Paybill: {PAYBILL}, Account: {PAYBILL_ACC}.

Your personality: warm, helpful, knowledgeable about electrical products, professional.

Your responsibilities:
- Help customers find products and get prices in Kenyan Shillings (Ksh)
- Accept and confirm orders with a unique Order ID (format: NEV1001)
- Track orders when customer provides Order ID
- Answer FAQs clearly and helpfully

Key product knowledge:
- Cable brands: Tronic, ASL, Evin East Africa
- Cable sizes: 1.0mm, 1.5mm, 2.5mm, 4.0mm, 6.0mm (singles and twin earth available)
- All electrical wiring materials available including modern wall brackets and chandeliers
- Payment: M-Pesa Paybill {PAYBILL}, Account {PAYBILL_ACC}

Formatting rules for WhatsApp:
- Use *bold* for product names, prices, and important info
- Use emojis naturally to make messages friendly
- Keep product listings clean and easy to read
- Always show prices as: Ksh X,XXX
- When listing products use format: • *Product Name* — Ksh X,XXX
- End every message with a helpful follow-up offer

When taking an order:
1. Confirm items and quantities with the customer
2. Show a clear order summary with total
3. Provide Order ID and payment instructions
4. Thank the customer warmly

Product categories available: {", ".join(CATEGORIES)}
"""

# ── Helpers ───────────────────────────────────────────────────────────────────
def search_products(query, threshold=60):
    results = []
    for name, info in PRODUCTS.items():
        score = fuzz.partial_ratio(query.lower(), name.lower())
        if score >= threshold:
            results.append((name, info, score))
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:8]

def get_by_category(category_query):
    return [(n, i) for n, i in PRODUCTS.items()
            if category_query.lower() in i["category"].lower()]

def build_product_context(user_message):
    context = ""
    for cat in CATEGORIES:
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
            order = orders.get(word)
            if order:
                context += (
                    f"\n📋 Order {word}:\n"
                    f"  Status: {order['status']}\n"
                    f"  Items: {order['items']}\n"
                    f"  Total: Ksh {order['total']:,}"
                )
    return context

def generate_ai_response(phone, user_message):
    if phone not in conversations:
        conversations[phone] = []

    product_context = build_product_context(user_message)
    enhanced = user_message
    if product_context:
        enhanced = f"{user_message}\n\n[PRODUCT DATA:{product_context}]"

    conversations[phone].append({"role": "user", "content": enhanced})
    recent = conversations[phone][-10:]

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + recent,
            max_tokens=700,
            temperature=0.5,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq error: {e}")
        reply = (
            "⚠️ *Sorry, I'm having a technical issue right now.*\n\n"
            "Please reach us directly:\n"
            f"📞 *{SHOP_PHONE}*\n"
            f"📍 {SHOP_LOCATION}"
        )

    conversations[phone].append({"role": "assistant", "content": reply})
    return reply

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return f"✅ {SHOP_NAME} WhatsApp Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming = request.form.get("Body", "").strip()
    phone    = request.form.get("From", "")

    logger.info(f"Message from {phone}: {incoming}")

    text_lower = incoming.lower().strip()

    # ── Keyword shortcuts ──
    greet_keywords = ["hi", "hello", "hujambo", "habari", "hey", "start", "menu", "0"]
    payment_keywords = ["payment", "pay", "mpesa", "paybill", "lipa", "5"]
    contact_keywords = ["contact", "location", "address", "where", "directions", "6"]

    if text_lower in greet_keywords:
        reply = welcome_message()
    elif text_lower in payment_keywords:
        reply = payment_message()
    elif text_lower in contact_keywords:
        reply = contact_message()
    else:
        reply = generate_ai_response(phone, incoming)

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)