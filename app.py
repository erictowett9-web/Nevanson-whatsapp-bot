import os
import json
import logging
import requests
from flask import Flask, request, jsonify
from groq import Groq
from fuzzywuzzy import fuzz

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Env vars ─────────────────────────────────────────────────────────────────
VERIFY_TOKEN        = os.environ.get("VERIFY_TOKEN", "nevanson_verify_token")
WHATSAPP_TOKEN      = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID     = os.environ.get("PHONE_NUMBER_ID", "")
GROQ_API_KEY        = os.environ.get("GROQ_API_KEY", "")

groq_client = Groq(api_key=GROQ_API_KEY)

# ── In-memory conversation store ─────────────────────────────────────────────
conversations = {}   # { phone: [{"role": ..., "content": ...}, ...] }
orders        = {}   # { order_id: {phone, items, status, total} }
order_counter = [1000]

# ── Shop data ─────────────────────────────────────────────────────────────────
SHOP_NAME    = "NEVANSON ELECTRICALS AND ELECTRONICS"
SHOP_PHONE   = "0741311041 / 0720799896"
SHOP_LOCATION = "Mogogosiek Town – Opposite Stabex Petrol Station"
PAYBILL      = "522533"
PAYBILL_ACC  = "8093799"

PRODUCTS = {
    # ── BULBS ──
    "5W AC Bulb (Yomy)":          {"price": 40,   "category": "Bulbs"},
    "7W AC Bulb (Yomy)":          {"price": 45,   "category": "Bulbs"},
    "9W AC Bulb (Yomy)":          {"price": 35,   "category": "Bulbs"},
    "5W AC Bulb (Hommie)":        {"price": 40,   "category": "Bulbs"},
    "7W AC Bulb (Hommie)":        {"price": 45,   "category": "Bulbs"},
    "9W AC Bulb (Hommie)":        {"price": 50,   "category": "Bulbs"},
    "12W AC Bulb (Hommie)":       {"price": 750,  "category": "Bulbs"},

    # ── FLOODLIGHTS ──
    "50W AC Floodlight":          {"price": 1200, "category": "Floodlights"},
    "100W LED Floodlight (Atta)": {"price": 230,  "category": "Floodlights"},
    "18W Bulkhead (Atta)":        {"price": 280,  "category": "Floodlights"},
    "24W Bulkhead (Atta)":        {"price": 280,  "category": "Floodlights"},

    # ── SWITCHES ──
    "19.2W Switch":               {"price": 60,   "category": "Switches"},
    "29.2W Switch":               {"price": 75,   "category": "Switches"},
    "39.2W Switch":               {"price": 100,  "category": "Switches"},
    "DP Switch 45A":              {"price": 300,  "category": "Switches"},
    "4G 2W Switch (Casher)":      {"price": 200,  "category": "Switches"},

    # ── SOCKETS ──
    "Socket Single":              {"price": 80,   "category": "Sockets"},
    "Socket Double":              {"price": 160,  "category": "Sockets"},
    "Socket Double 13A Tronic":   {"price": 300,  "category": "Sockets"},
    "Socket Single Double":       {"price": 3300, "category": "Sockets"},
    "Extension Socket Plk Sw":    {"price": 230,  "category": "Sockets"},

    # ── CONDUIT & TRUNKING ──
    "Pipe 20mm HLG":              {"price": 75,   "category": "Conduit & Trunking"},
    "Throughbox 4-Way":           {"price": 15,   "category": "Conduit & Trunking"},
    "Throughbox 3-Way":           {"price": 15,   "category": "Conduit & Trunking"},
    "Saddle Clips 25mm":          {"price": 3,    "category": "Conduit & Trunking"},
    "MK Single":                  {"price": 15,   "category": "Conduit & Trunking"},
    "MK Double":                  {"price": 25,   "category": "Conduit & Trunking"},
    "Pattress Double":            {"price": 30,   "category": "Conduit & Trunking"},
    "Pattress Single":            {"price": 20,   "category": "Conduit & Trunking"},
    "1x1 Trunking":               {"price": 70,   "category": "Conduit & Trunking"},
    "1.5 Singles R7B (roll)":     {"price": 1700, "category": "Conduit & Trunking"},
    "Plain Coupler 20mm":         {"price": 10,   "category": "Conduit & Trunking"},
    "Normal Bend 20mm":           {"price": 10,   "category": "Conduit & Trunking"},

    # ── CABLES ──
    "Cable Single Tronic 1.5 (R7B)": {"price": 5400, "category": "Cables"},
    "Cable Single Tronic 2.5 (R7B)": {"price": 3,    "category": "Cables"},

    # ── MCBs / CONSUMER UNITS ──
    "MCB 6A Andeli":              {"price": 110,  "category": "MCBs & Consumer Units"},
    "MCB 32A Andeli":             {"price": 110,  "category": "MCBs & Consumer Units"},
    "MCB 2P 63A Andeli":          {"price": 220,  "category": "MCBs & Consumer Units"},
    "MCB 2P Cloak Andeli":        {"price": 220,  "category": "MCBs & Consumer Units"},
    "MCB 16A Andeli":             {"price": 110,  "category": "MCBs & Consumer Units"},
    "MCB 20A Andeli":             {"price": 110,  "category": "MCBs & Consumer Units"},
    "Consumer Unit Z-Y 2-4":      {"price": 200,  "category": "MCBs & Consumer Units"},
    "Consumer Unit Z-Y 4-6":      {"price": 300,  "category": "MCBs & Consumer Units"},
    "Consumer Unit Z-Y 6-8":      {"price": 850,  "category": "MCBs & Consumer Units"},
    "Element 4T":                 {"price": 350,  "category": "MCBs & Consumer Units"},

    # ── FLUORESCENT / LIGHTING ──
    "Fluorescent DLP 2ft":        {"price": 200,  "category": "Fluorescent Lighting"},
    "Fluorescent DLP 4ft":        {"price": 300,  "category": "Fluorescent Lighting"},
    "Shower Head Horizon":        {"price": 850,  "category": "Shower Fittings"},

    # ── ACCESSORIES ──
    "Junction Box Big":           {"price": 70,   "category": "Accessories"},
    "Wood Screws (5pkts)":        {"price": 190,  "category": "Accessories"},
    "Top Plug Topnexas":          {"price": 30,   "category": "Accessories"},
    "Top Plug HLG":               {"price": 75,   "category": "Accessories"},
    "Holder Angle HLG":           {"price": 65,   "category": "Accessories"},
    "Holder Straight HLG":        {"price": 65,   "category": "Accessories"},
    "DP Angle Holder":            {"price": 35,   "category": "Accessories"},
    "Small Straight Holder":      {"price": 30,   "category": "Accessories"},
    "TV Mast":                    {"price": 300,  "category": "Accessories"},
    "TV Guard Itol":              {"price": 300,  "category": "Accessories"},
    "Fridge Guard Itol":          {"price": 35,   "category": "Accessories"},
    "PCB 2Y1":                    {"price": 16,   "category": "Accessories"},
    "Female Connector":           {"price": 10,   "category": "Accessories"},
    "Male Connector":             {"price": 10,   "category": "Accessories"},
    "Plastic Jackpin":            {"price": 15,   "category": "Accessories"},
    "Meter Box Heavy Gauge":      {"price": 260,  "category": "Accessories"},
    "Earth Rod Small":            {"price": 100,  "category": "Accessories"},
    "DB Enclosure":               {"price": 80,   "category": "Accessories"},
}

# Unique categories
CATEGORIES = sorted(set(v["category"] for v in PRODUCTS.values()))

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are a helpful WhatsApp sales assistant for {SHOP_NAME}, 
an electrical and electronics shop located at {SHOP_LOCATION}.
Shop contacts: {SHOP_PHONE}.
Payment: M-Pesa Paybill {PAYBILL}, Account {PAYBILL_ACC}.

Your role:
- Help customers browse products by category or search by name
- Give accurate prices in Kenyan Shillings (Ksh)
- Accept and confirm orders
- Track order status when customers provide their order ID
- Answer FAQs about the shop

Key FAQs:
- Cable brands available: Tronic, ASL, Evin East Africa
- Cable sizes: 1.0mm, 1.5mm, 2.5mm, 4.0mm, 6.0mm (singles and twin earth)
- All electrical wiring materials are available including modern wall brackets and chandeliers
- Delivery: customers can visit the shop or call to arrange pickup
- Payment via M-Pesa Paybill {PAYBILL} Account {PAYBILL_ACC}

Product categories: {", ".join(CATEGORIES)}

When a customer wants to order:
1. Confirm the items and quantities
2. Calculate the total
3. Tell them to pay via M-Pesa and send their name + order ID as the reference
4. Give them their order ID

Keep responses friendly, concise, and in the same language the customer uses (English or Swahili).
Always end with a helpful follow-up question or offer.
"""

# ── Helper: send WhatsApp message ─────────────────────────────────────────────
def send_whatsapp_message(to, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        logger.info(f"WhatsApp API response: {resp.status_code} {resp.text}")
        return resp.json()
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        return None

# ── Helper: search products ───────────────────────────────────────────────────
def search_products(query, threshold=60):
    query_lower = query.lower()
    results = []
    for name, info in PRODUCTS.items():
        score = fuzz.partial_ratio(query_lower, name.lower())
        if score >= threshold:
            results.append((name, info, score))
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:8]

# ── Helper: get products by category ─────────────────────────────────────────
def get_by_category(category_query):
    cat_lower = category_query.lower()
    results = []
    for name, info in PRODUCTS.items():
        if cat_lower in info["category"].lower():
            results.append((name, info))
    return results

# ── Helper: create order ──────────────────────────────────────────────────────
def create_order(phone, items_text, total):
    order_counter[0] += 1
    order_id = f"NEV{order_counter[0]}"
    orders[order_id] = {
        "phone": phone,
        "items": items_text,
        "status": "Pending Payment",
        "total": total,
        "order_id": order_id,
    }
    return order_id

# ── Helper: get order status ──────────────────────────────────────────────────
def get_order_status(order_id):
    return orders.get(order_id.upper())

# ── Helper: build products context for Groq ───────────────────────────────────
def build_product_context(user_message):
    context = ""
    # Category browse
    for cat in CATEGORIES:
        if cat.lower() in user_message.lower():
            items = get_by_category(cat)
            if items:
                lines = [f"  • {n}: Ksh {i['price']:,}" for n, i in items]
                context += f"\n📦 {cat}:\n" + "\n".join(lines)

    # Keyword search
    results = search_products(user_message)
    if results and not context:
        lines = [f"  • {n}: Ksh {i['price']:,}" for n, i, _ in results]
        context += "\n🔍 Matching products:\n" + "\n".join(lines)

    # Order tracking
    words = user_message.upper().split()
    for word in words:
        if word.startswith("NEV") and len(word) >= 7:
            order = get_order_status(word)
            if order:
                context += f"\n📋 Order {word}: {order['status']} | Items: {order['items']} | Total: Ksh {order['total']:,}"

    return context

# ── Helper: generate AI response ─────────────────────────────────────────────
def generate_ai_response(phone, user_message):
    if phone not in conversations:
        conversations[phone] = []

    product_context = build_product_context(user_message)

    enhanced_message = user_message
    if product_context:
        enhanced_message = f"{user_message}\n\n[PRODUCT DATA FOR THIS QUERY:{product_context}]"

    conversations[phone].append({"role": "user", "content": enhanced_message})

    # Keep last 10 turns
    recent = conversations[phone][-10:]

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + recent,
            max_tokens=600,
            temperature=0.5,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq error: {e}")
        reply = (
            f"Sorry, I'm having trouble right now. Please call us directly:\n"
            f"📞 {SHOP_PHONE}\n"
            f"📍 {SHOP_LOCATION}"
        )

    conversations[phone].append({"role": "assistant", "content": reply})
    return reply

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "shop": SHOP_NAME})

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified ✅")
        return challenge, 200
    logger.warning("Webhook verification failed ❌")
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.get_json()
    logger.info(f"Incoming: {json.dumps(data, indent=2)}")

    try:
        entry   = data["entry"][0]
        changes = entry["changes"][0]
        value   = changes["value"]

        if "messages" not in value:
            return jsonify({"status": "no_message"}), 200

        message = value["messages"][0]
        phone   = message["from"]
        msg_type = message.get("type", "")

        if msg_type == "text":
            text = message["text"]["body"].strip()
        elif msg_type == "interactive":
            inter = message["interactive"]
            if inter["type"] == "button_reply":
                text = inter["button_reply"]["title"]
            elif inter["type"] == "list_reply":
                text = inter["list_reply"]["title"]
            else:
                text = "help"
        else:
            text = "help"

        logger.info(f"Message from {phone}: {text}")

        # Greeting shortcut
        greet_keywords = ["hi", "hello", "hujambo", "habari", "hey", "start", "menu"]
        if text.lower().strip() in greet_keywords:
            reply = (
                f"👋 Welcome to *{SHOP_NAME}*!\n"
                f"📍 {SHOP_LOCATION}\n\n"
                f"How can I help you today? You can:\n"
                f"1️⃣ Browse products by category\n"
                f"2️⃣ Search for a specific item\n"
                f"3️⃣ Place an order\n"
                f"4️⃣ Track your order (send your Order ID e.g. NEV1001)\n"
                f"5️⃣ Ask any question about our products\n\n"
                f"Type a category name to get started:\n"
                + "\n".join(f"🔹 {c}" for c in CATEGORIES)
            )
        else:
            reply = generate_ai_response(phone, text)

        send_whatsapp_message(phone, reply)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
