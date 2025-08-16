import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
ADMIN_IDS = [int(os.getenv('ADMIN_ID'))]
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_SECRET = os.getenv('PAYPAL_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')