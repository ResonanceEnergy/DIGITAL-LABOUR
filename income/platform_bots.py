"""White-Label Bot Templates — Pre-configured bots for Chatbase + Botpress reselling.

Generates bot configuration templates that can be deployed on Chatbase or Botpress,
then resold to clients as managed AI support/sales bots.

Revenue model:
    - Build once, deploy for each client
    - Charge $200-1000/mo per client for managed bot service
    - Client gets: custom-branded bot, monthly reports, optimization

Usage:
    python -m income.platform_bots                # Print all templates
    python -m income.platform_bots --chatbase      # Chatbase configs only
    python -m income.platform_bots --botpress      # Botpress configs only
    python -m income.platform_bots --save          # Save to files
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "output" / "bot_templates"


# ── Chatbase Bot Templates ──────────────────────────────────────

CHATBASE_TEMPLATES = [
    {
        "name": "SaaS Support Bot",
        "platform": "chatbase",
        "description": "AI-powered customer support for SaaS companies. Handles FAQs, ticket triage, and escalation.",
        "target_client": "SaaS companies with 50-500 support tickets/month",
        "monthly_price": "$400/mo managed",
        "setup_fee": "$200 one-time",
        "config": {
            "model": "gpt-4o",
            "temperature": 0.3,
            "system_prompt": (
                "You are a helpful customer support agent for {COMPANY_NAME}. "
                "You answer questions about {PRODUCT_NAME} based on the provided knowledge base. "
                "Be professional, empathetic, and solution-oriented. "
                "If you cannot answer a question, say: 'Let me connect you with our team — "
                "please email support@{DOMAIN} and we'll get back to you within 2 hours.' "
                "Never make up features or pricing. Only reference what's in your training data."
            ),
            "suggested_messages": [
                "How do I get started?",
                "What are your pricing plans?",
                "I need help with my account",
                "How do I cancel my subscription?",
                "I found a bug — who do I contact?",
            ],
            "branding": {
                "bot_name": "{COMPANY_NAME} Assistant",
                "welcome_message": "Hi! I'm {COMPANY_NAME}'s AI assistant. How can I help you today?",
                "color": "#2563eb",
                "position": "bottom-right",
            },
        },
        "setup_steps": [
            "1. Create Chatbase account: https://chatbase.co",
            "2. Click 'New Chatbot' → choose GPT-4o model",
            "3. Upload client's FAQ/docs as training data",
            "4. Set system prompt (replace {COMPANY_NAME}, {PRODUCT_NAME}, {DOMAIN})",
            "5. Configure branding (logo, color, welcome message)",
            "6. Test with 10 sample questions",
            "7. Generate embed code → send to client for their website",
            "8. Set up monthly usage report (Chatbase analytics)",
        ],
    },
    {
        "name": "E-commerce Sales Bot",
        "platform": "chatbase",
        "description": "Product recommendation and pre-sales bot for e-commerce stores.",
        "target_client": "E-commerce stores with 1K-50K monthly visitors",
        "monthly_price": "$600/mo managed",
        "setup_fee": "$300 one-time",
        "config": {
            "model": "gpt-4o",
            "temperature": 0.5,
            "system_prompt": (
                "You are a helpful shopping assistant for {COMPANY_NAME}. "
                "You help customers find the right products based on their needs. "
                "You know all products, pricing, and availability from the catalog. "
                "Be enthusiastic but honest. If a product is out of stock or doesn't exist, say so. "
                "Always try to recommend alternatives. "
                "For orders and returns, direct to: {SUPPORT_EMAIL}"
            ),
            "suggested_messages": [
                "What's on sale right now?",
                "Help me find a gift under $50",
                "Do you have this in my size?",
                "What's your return policy?",
                "Track my order",
            ],
        },
        "setup_steps": [
            "1. Create Chatbase account",
            "2. Upload product catalog (CSV/JSON) as training data",
            "3. Upload FAQ, return policy, shipping info",
            "4. Configure system prompt with client details",
            "5. Set up product recommendation logic",
            "6. Brand with client's colors and logo",
            "7. Test with common shopping scenarios",
            "8. Embed on client's store (Shopify/WooCommerce compatible)",
        ],
    },
    {
        "name": "Lead Qualification Bot",
        "platform": "chatbase",
        "description": "Qualifies website visitors and captures lead info for sales teams.",
        "target_client": "B2B companies wanting to automate lead qualification",
        "monthly_price": "$500/mo managed",
        "setup_fee": "$250 one-time",
        "config": {
            "model": "gpt-4o",
            "temperature": 0.4,
            "system_prompt": (
                "You are a friendly sales assistant for {COMPANY_NAME}. "
                "Your goal is to understand what the visitor needs and qualify them as a potential customer. "
                "Ask about: company size, current solution, budget range, timeline. "
                "Be conversational, not interrogative. "
                "If they seem qualified, suggest booking a demo: {CALENDLY_LINK} "
                "If they have technical questions, provide brief answers from the knowledge base."
            ),
            "suggested_messages": [
                "What does your company do?",
                "I'd like to see a demo",
                "What are your pricing options?",
                "How is this different from [competitor]?",
                "Can I talk to someone?",
            ],
        },
        "setup_steps": [
            "1. Create Chatbase account",
            "2. Upload client's pitch deck, pricing, FAQ as training data",
            "3. Configure qualification criteria with client",
            "4. Set up Calendly/booking link integration",
            "5. Configure lead capture (email required before detailed answers)",
            "6. Brand and customize",
            "7. Test qualification flow end-to-end",
            "8. Set up weekly lead report delivery to client",
        ],
    },
]


# ── Botpress Bot Templates ─────────────────────────────────────

BOTPRESS_TEMPLATES = [
    {
        "name": "Multi-Channel Support Agent",
        "platform": "botpress",
        "description": "Production support agent with conversation flows, handoff, and analytics.",
        "target_client": "Companies needing multi-channel support (web, WhatsApp, Slack)",
        "monthly_price": "$800/mo managed",
        "setup_fee": "$500 one-time",
        "config": {
            "nodes": [
                {"id": "welcome", "type": "standard", "content": "Welcome message + language detection"},
                {"id": "classify", "type": "ai", "content": "Classify intent: support, sales, billing, other"},
                {"id": "support_flow", "type": "ai", "content": "Handle support queries from KB"},
                {"id": "sales_flow", "type": "ai", "content": "Qualify lead, book demo"},
                {"id": "billing_flow", "type": "standard", "content": "Redirect to billing portal"},
                {"id": "escalate", "type": "handoff", "content": "Transfer to human agent"},
                {"id": "feedback", "type": "standard", "content": "Collect satisfaction rating"},
            ],
            "integrations": ["webchat", "whatsapp", "slack", "messenger"],
            "knowledge_bases": ["faq", "product_docs", "pricing"],
        },
        "setup_steps": [
            "1. Create Botpress Cloud account: https://botpress.com",
            "2. Create new bot → choose 'AI Agent' template",
            "3. Upload client's knowledge base (FAQ, docs, pricing)",
            "4. Build conversation flows (7 nodes as defined)",
            "5. Configure AI task nodes (GPT-4o via Botpress AI)",
            "6. Set up channel integrations (web, WhatsApp, Slack)",
            "7. Configure human handoff rules",
            "8. Test all flows with 20+ scenarios",
            "9. Deploy and share embed code with client",
            "10. Set up monthly analytics report",
        ],
    },
    {
        "name": "Appointment Booking Bot",
        "platform": "botpress",
        "description": "Conversational appointment scheduler for service businesses.",
        "target_client": "Clinics, salons, consultants, service providers",
        "monthly_price": "$300/mo managed",
        "setup_fee": "$150 one-time",
        "config": {
            "nodes": [
                {"id": "greet", "type": "standard", "content": "Welcome + service menu"},
                {"id": "select_service", "type": "choice", "content": "Select service type"},
                {"id": "check_availability", "type": "api", "content": "Check calendar via API"},
                {"id": "collect_info", "type": "form", "content": "Name, phone, email"},
                {"id": "confirm", "type": "standard", "content": "Confirm booking + send reminder"},
            ],
            "integrations": ["webchat", "whatsapp", "sms"],
        },
        "setup_steps": [
            "1. Create Botpress account",
            "2. Build booking flow (5 nodes)",
            "3. Integrate with client's calendar (Google Cal / Calendly API)",
            "4. Configure service types and duration",
            "5. Set up SMS/email confirmation via Twilio/Zoho",
            "6. Brand with client colors",
            "7. Test booking flow end-to-end",
            "8. Deploy on client's website + WhatsApp",
        ],
    },
]


# ── Output Functions ────────────────────────────────────────────

def print_chatbase():
    print(f"\n{'='*70}")
    print("  CHATBASE BOT TEMPLATES — Ready to Deploy + Resell")
    print(f"{'='*70}")
    for i, bot in enumerate(CHATBASE_TEMPLATES, 1):
        print(f"\n{'─'*70}")
        print(f"  BOT {i}: {bot['name']}")
        print(f"  Target: {bot['target_client']}")
        print(f"  Pricing: {bot['monthly_price']} + {bot['setup_fee']}")
        print(f"{'─'*70}")
        print(f"  {bot['description']}")
        print(f"\n  SETUP STEPS:")
        for step in bot["setup_steps"]:
            print(f"    {step}")
    print()


def print_botpress():
    print(f"\n{'='*70}")
    print("  BOTPRESS BOT TEMPLATES — Ready to Deploy + Resell")
    print(f"{'='*70}")
    for i, bot in enumerate(BOTPRESS_TEMPLATES, 1):
        print(f"\n{'─'*70}")
        print(f"  BOT {i}: {bot['name']}")
        print(f"  Target: {bot['target_client']}")
        print(f"  Pricing: {bot['monthly_price']} + {bot['setup_fee']}")
        print(f"{'─'*70}")
        print(f"  {bot['description']}")
        print(f"\n  Flow nodes: {len(bot['config']['nodes'])}")
        for node in bot["config"]["nodes"]:
            print(f"    [{node['type']}] {node['id']} — {node['content']}")
        print(f"\n  SETUP STEPS:")
        for step in bot["setup_steps"]:
            print(f"    {step}")
    print()


def save_templates():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for bot in CHATBASE_TEMPLATES + BOTPRESS_TEMPLATES:
        slug = bot["name"].lower().replace(" ", "_").replace("-", "_")
        filepath = OUTPUT_DIR / f"{bot['platform']}_{slug}.json"
        filepath.write_text(json.dumps(bot, indent=2), encoding="utf-8")
        print(f"  [SAVED] {filepath.name}")
    print(f"\n  Templates saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Bot Platform Templates")
    parser.add_argument("--chatbase", action="store_true")
    parser.add_argument("--botpress", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    if args.chatbase:
        print_chatbase()
    elif args.botpress:
        print_botpress()
    elif args.save:
        save_templates()
    else:
        print_chatbase()
        print_botpress()
