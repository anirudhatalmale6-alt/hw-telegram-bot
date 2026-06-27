import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DATABASE_PATH = os.getenv("DATABASE_PATH", "store.db")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "7652774937")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
HITPAY_API_KEY = os.getenv("HITPAY_API_KEY", "live_6d5c3f9a09ac2385c57c4cc4ae40fbe668fa7dc6f787b1aeae74aab2f899b260")
HITPAY_SALT = os.getenv("HITPAY_SALT", "WP3XXIYvgdZiyxizhRVQGU8E0LR0GoGXwfPhO5rbMRM7wXRPyz1k3oR9na2u2VHu")
HITPAY_API_URL = "https://api.hit-pay.com/v1/payment-requests"

DELIVERY_OPTIONS = {
    "self_collection": {"label": "Self Collection", "fee": 0.00},
    "standard": {"label": "Standard Delivery", "fee": 5.00},
    "express": {"label": "Express Delivery", "fee": 12.00},
}
