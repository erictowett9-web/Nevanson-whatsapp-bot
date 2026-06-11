# NEVANSON ELECTRICALS AND ELECTRONICS – WhatsApp Bot

A WhatsApp chatbot for Nevanson Electricals built with Python/Flask, Groq AI, and Meta Cloud API.

---

## Features
- 🛍️ Browse products by category (Bulbs, Cables, MCBs, Switches, Sockets, etc.)
- 🔍 AI-powered product search
- 🛒 Place orders via WhatsApp
- 📦 Track order status using Order ID
- ❓ Answer FAQs about cables, brands, payment, and location
- 💳 M-Pesa Paybill payment integration info

---

## Tech Stack
- Python 3.12 + Flask
- Groq AI (llama-3.3-70b-versatile)
- Meta Cloud API (WhatsApp)
- Gunicorn (production server)
- Hosted on Koyeb

---

## Setup Instructions

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/nevanson-whatsapp-bot.git
cd nevanson-whatsapp-bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set environment variables
Create a `.env` file (never commit this!):
```
VERIFY_TOKEN=nevanson_verify_token
WHATSAPP_TOKEN=your_meta_whatsapp_token
PHONE_NUMBER_ID=your_phone_number_id
GROQ_API_KEY=your_groq_api_key
```

### 4. Run locally
```bash
python app.py
```

---

## Deployment on Koyeb

1. Push code to GitHub
2. Create a new Koyeb service → Connect GitHub repo
3. Set build command: `pip install -r requirements.txt`
4. Set run command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
5. Add environment variables in Koyeb dashboard:
   - `VERIFY_TOKEN` = `nevanson_verify_token`
   - `WHATSAPP_TOKEN` = (from Meta Developer portal)
   - `PHONE_NUMBER_ID` = (from Meta Developer portal)
   - `GROQ_API_KEY` = (from console.groq.com)

---

## Meta Cloud API Webhook Setup

1. Go to Meta Developer Portal → Your App → WhatsApp → Configuration
2. Set Webhook URL: `https://YOUR-KOYEB-URL/webhook`
3. Set Verify Token: `nevanson_verify_token`
4. Subscribe to: `messages`

---

## Environment Variables

| Variable | Description |
|---|---|
| `VERIFY_TOKEN` | Token for Meta webhook verification |
| `WHATSAPP_TOKEN` | Meta WhatsApp Cloud API bearer token |
| `PHONE_NUMBER_ID` | WhatsApp Phone Number ID from Meta |
| `GROQ_API_KEY` | Groq API key from console.groq.com |

---

## Shop Details
- **Shop:** Nevanson Electricals and Electronics
- **Location:** Mogogosiek Town – Opposite Stabex Petrol Station
- **Contacts:** 0741311041 / 0720799896
- **M-Pesa Paybill:** 522533 | Account: 8093799
