from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
FORCE_JOIN = os.getenv("FORCE_JOIN_CHANNEL")
CREATOR = os.getenv("CREATOR_USERNAME", "@daxbots")
REFERRALS_NEEDED = 10
