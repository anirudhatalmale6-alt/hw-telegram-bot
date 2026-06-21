import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_DEMO")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_DEMO")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DATABASE_PATH = os.getenv("DATABASE_PATH", "store.db")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
PAYNOW_UEN = os.getenv("PAYNOW_UEN", "DEMO-UEN-123")
PAYNOW_COMPANY = os.getenv("PAYNOW_COMPANY", "Health Wellness Store")

DELIVERY_OPTIONS = {
    "self_collection": {"label": "Self Collection", "fee": 0.00},
    "standard": {"label": "Standard Delivery", "fee": 5.00},
    "express": {"label": "Express Delivery", "fee": 12.00},
}
