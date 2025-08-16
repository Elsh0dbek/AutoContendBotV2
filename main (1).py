import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.utils.executor import start_webhook
from datetime import datetime, timedelta
import asyncio
import aiohttp
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import stripe
import paypalrestsdk
from googletrans import Translator
import openai
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pandas as pd
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import numpy as np
from aiogram.dispatcher.webhook import SendMessage
from aiogram.utils.exceptions import TelegramAPIError
from config import BOT_TOKEN, DATABASE_URL, ADMIN_IDS, STRIPE_SECRET_KEY, PAYPAL_CLIENT_ID, PAYPAL_SECRET, OPENAI_API_KEY, REDIS_URL, WEBHOOK_URL, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT
from utils import create_infographic, handle_tap_earn, fetch_trading_signals

load_dotenv()
stripe.api_key = STRIPE_SECRET_KEY
paypalrestsdk.configure({"mode": "sandbox", "client_id": PAYPAL_CLIENT_ID, "client_secret": PAYPAL_SECRET})
openai.api_key = OPENAI_API_KEY

engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)  # Fix for asyncpg issues
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

logging.basicConfig(level=logging.INFO, filename='bot.log', filemode='a')  # Improved logging
bot = Bot(token=BOT_TOKEN)
storage = RedisStorage2(REDIS_URL)  # Redis for FSM
dp = Dispatcher(bot, storage=storage)
scheduler = AsyncIOScheduler()

# Database Models
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    language = Column(String, default='en')
    categories = Column(String)
    daily_limit = Column(Integer, default=5)
    premium_until = Column(DateTime)
    invite_count = Column(Integer, default=0)
    coins = Column(Integer, default=0)

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    subcategories = Column(String)

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    content = Column(String)
    category_id = Column(Integer)
    channel_id = Column(String)
    scheduled_time = Column(DateTime)
    views = Column(Integer, default=0)

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    plan = Column(String)

class ProblemReport(Base):
    __tablename__ = 'problem_reports'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    text = Column(String)
    category = Column(String)

Base.metadata.create_all(engine)

# States (unchanged)

# Core Functions with error handling
async def generate_ai_content(category, subcategory):
    try:
        prompt = f"Generate content for {category} - {subcategory}"
        response = openai.ChatCompletion.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])  # Updated model
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "Kontent yaratishda xato."

# Other functions similar, with try-except

async def send_scheduled_post(post_id):
    session = SessionLocal()
    post = session.query(Post).get(post_id)
    try:
        msg = await bot.send_message(chat_id=post.channel_id, text=post.content)
        post.views = (await bot.get_chat_member_count(post.channel_id))  # Approximate views
        session.commit()
    except TelegramAPIError as e:
        logging.error(f"Telegram error: {e}")
    finally:
        session.delete(post)
        session.commit()

# Channel Report (unchanged, but with logging)

# Anti-spam middleware
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit=5, interval=60):
        self.limit = limit
        self.interval = interval
        self.user_messages = {}

    async def on_process_message(self, message: Message, data: dict):
        user_id = message.from_user.id
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        self.user_messages[user_id].append(datetime.now())
        self.user_messages[user_id] = [t for t in self.user_messages[user_id] if datetime.now() - t < timedelta(seconds=self.interval)]
        if len(self.user_messages[user_id]) > self.limit:
            await message.reply("Flood! Biroz kutib turing.")
            return False
        return True

dp.middleware.setup(AntiFloodMiddleware())

# Eco-content
async def generate_eco_content():
    return await generate_ai_content("Eco", "Sustainability")

@dp.message_handler(commands=['eco'])
async def eco(message: types.Message):
    content = await generate_eco_content()
    await message.reply(content)

# Mini-Apps (basic)
@dp.message_handler(commands=['miniapp'])
async def mini_app(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Open Dashboard", web_app=types.WebAppInfo(url="https://your-mini-app-url.com")))
    await message.reply("Mini-App oching:", reply_markup=keyboard)

# Handlers with error handling (example)
@dp.message_handler(commands=['start'])
async def start(message: types.Message, state: FSMContext):
    try:
        # Unchanged logic
        pass
    except Exception as e:
        logging.error(f"Start error: {e}")
        await message.reply("Xato yuz berdi. Qayta urinib ko'ring.")

# Webhook setup
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    scheduler.start()
    # Init categories (unchanged)

async def on_shutdown(dp):
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()

if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )