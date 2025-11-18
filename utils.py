from datetime import datetime, timedelta
from config import BOT_USERNAME, FORCE_JOIN

def generate_share_link(delete_code):
    return f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=lock_{delete_code}"

def generate_referral_link(user_id):
    return f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=ref_{user_id}"

def get_expiry_text(expiry):
    if not expiry:
        return "Never (Premium)"
    return expiry.strftime("%Y-%m-%d %H:%M")
