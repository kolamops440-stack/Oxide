import asyncio
import json
import os
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict
import time
import random

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# ========== КОНФИГ ==========
BOT_TOKEN = "8813471822:AAEWpNtYPJGVtCVeqGO5d4yvrwGOYhffpW8"
ADMIN_ID = 7496589494
CRYPTO_BOT_TOKEN = "560372:AAyQpvWZFSHpzrnVAhVwPF7PbcJmqI7bH0K"
UAH_CARD = "4441111008011946"
UAH_COMMENT = "За цифрові товари"

# ========== ФОТО ==========
MENU_PHOTO = "https://files.catbox.moe/vz52pd.png"
CATALOG_PHOTO = "https://files.catbox.moe/w1ruj1.png"
GAME_SELECT_PHOTO = "https://files.catbox.moe/kxk5w3.png"
SYSTEM_PHOTO = "https://files.catbox.moe/87qpck.png"
PERIOD_PHOTO = "https://files.catbox.moe/b795ua.png"
PAYMENT_PHOTO = "https://files.catbox.moe/tzogel.png"

# ========== Цены и товары ==========
PRICES = {
    "Lebro_Lite": {"24h": 1.5, "7d": 4.5},
    "Lebro_VIP": {"24h": 3, "7d": 7.5, "30d": 15},
    "Plutonium": {"7d": 150, "30d": 300, "90d": 700},
}

PRODUCT_NAMES = {
    "Lebro_Lite": "Lebro [Lite]",
    "Lebro_VIP": "Lebro [VIP]",
    "Plutonium": "Plutonium"
}

PERIODS = {
    "Lebro_Lite": [("24 часа", "24h")],
    "Lebro_VIP": [("24 часа", "24h"), ("7 дней", "7d"), ("30 дней", "30d")],
    "Plutonium": [("7 дней", "7d"), ("30 дней", "30d"), ("90 дней", "90d")],
}

# ========== ID Telegram Premium эмодзи ==========
PREMIUM_EMOJI = {
    "playcheat": "5931409969613116639",
    "star": "5805532930662996322",
    "catalog": "5208513917965328345",
    "profile": "5886412370347036129",
    "purchases": "5983399041197675256",
    "oxide": "5312048193444282508",
    "standoff": "5819078828017849357",
    "back_main": "5877629862306385808",
    "lebro_vip": "5208422125924275090",
    "lebro_lite": "5208422125924275090",
    "period": "5985596818912712352",
    "crypto": "5361914370068613491",
    "uah": "5805532930662996322",
    "back_periods": "5877629862306385808",
    "invoice": "5983399041197675256",
    "sum": "5208513917965328345",
    "product": "5877260593903177342",
    "link": "5877465816030515018",
    "check": "6005843436479975944",
    "cancel": "5985346521103604145",
    "card": "5208431570557360595",
    "receipt": "6050592962730005028",
    "receipt_sent": "5985596818912712352",
    "confirmed": "5985596818912712352",
    "your_key": "6005570495603282482",
    "thanks": "5985596818912712352",
    "user_id": "5886505193180239900",
    "username": "5771887475421090729",
    "name": "5897962422169243693",
    "active_key": "6005570495603282482",
    "expires": "5897962422169243693",
    "game_select": "5960551395730919906",
    "lebroname": "5877260593903177342",
    "to_pay": "5983399041197675256",
    "back_game": "5877629862306385808",
    "agree": "5985346521103604145",
}

# Обычные эмодзи (для пользователей без Premium)
NORMAL_EMOJI = {
    "playcheat": "🛡️",
    "star": "⭐",
    "catalog": "🛍️",
    "profile": "👤",
    "purchases": "📦",
    "oxide": "🔥",
    "standoff": "💥",
    "back_main": "🔙",
    "lebro_vip": "💎",
    "lebro_lite": "📱",
    "period": "⏱️",
    "crypto": "💸",
    "uah": "🇺🇦",
    "back_periods": "🔙",
    "invoice": "📄",
    "sum": "💰",
    "product": "📦",
    "link": "🔗",
    "check": "🔄",
    "cancel": "❌",
    "card": "💳",
    "receipt": "📸",
    "receipt_sent": "✅",
    "confirmed": "✅",
    "your_key": "🔑",
    "thanks": "🎉",
    "user_id": "🆔",
    "username": "📛",
    "name": "👤",
    "active_key": "🔑",
    "expires": "⏳",
    "game_select": "📋",
    "lebroname": "📦",
    "to_pay": "💸",
    "back_game": "🔙",
    "agree": "✅",
}

# ========== ДАННЫЕ ==========
DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "users": {}, 
        "pending_uah": {}, 
        "pending_crypto": {},
        "temp_invoices": {}
    }

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

data = load_data()

# ========== FSM ==========
class States(StatesGroup):
    waiting_agreement = State()
    waiting_uah_receipt = State()
    waiting_crypto_payment = State()
    admin_waiting_user_id = State()
    admin_waiting_key = State()
    admin_waiting_crypto_key = State()
    admin_waiting_uah_key = State()
    selecting_game = State()
    selecting_product = State()
    selecting_period = State()
    selecting_payment = State()

# ========== ФУНКЦИИ ДЛЯ ПРОВЕРКИ PREMIUM ==========

async def is_premium_user(user_id: int) -> bool:
    """Проверяет есть ли у пользователя Telegram Premium"""
    try:
        user = await bot.get_chat(user_id)
        return user.premium_until_date is not None if hasattr(user, 'premium_until_date') else False
    except:
        return False

def get_emoji(user_is_premium: bool, emoji_key: str) -> str:
    """Возвращает эмодзи в зависимости от наличия Premium"""
    if user_is_premium:
        return f'<tg-emoji emoji-id="{PREMIUM_EMOJI[emoji_key]}"> </tg-emoji>'
    return NORMAL_EMOJI.get(emoji_key, "")

def make_button(user_is_premium: bool, text: str, callback_data: str, emoji_key: str = None):
    """Создает кнопку с эмодзи (Premium или обычное)"""
    if emoji_key:
        if user_is_premium:
            text = f'<tg-emoji emoji-id="{PREMIUM_EMOJI[emoji_key]}"> </tg-emoji>{text}'
        else:
            text = f'{NORMAL_EMOJI.get(emoji_key, "")} {text}'
    return InlineKeyboardButton(text=text, callback_data=callback_data)

# ========== КЛАВИАТУРЫ ==========

def agreement_keyboard(user_is_premium: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button(user_is_premium, "Я ознакомлен с правилами", "agree", "agree")]
    ])

def main_menu_keyboard(user_is_premium: bool, is_admin=False):
    buttons = [
        [
            make_button(user_is_premium, "Каталог", "menu_catalog", "catalog"),
            make_button(user_is_premium, "Профиль", "menu_profile", "profile")
        ],
        [
            make_button(user_is_premium, "Мои покупки", "menu_purchases", "purchases")
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🔧 Админ-панель", callback_data="menu_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_panel_keyboard(user_is_premium: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Выдать ключ пользователю", callback_data="admin_give_key")],
        [make_button(user_is_premium, "Подтвердить UAH оплату", "admin_confirm_uah", "uah")],
        [make_button(user_is_premium, "Подтвердить CRYPTO оплату", "admin_confirm_crypto", "crypto")],
        [make_button(user_is_premium, "В главное меню", "back_to_main", "back_main")]
    ])

def catalog_keyboard(user_is_premium: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button(user_is_premium, "Oxide Survival Island", "game_oxide", "oxide")],
        [make_button(user_is_premium, "Standoff 2", "game_standoff", "standoff")],
        [make_button(user_is_premium, "В главное меню", "back_to_main", "back_main")]
    ])

def products_keyboard(user_is_premium: bool, game: str):
    buttons = []
    if game == "oxide":
        buttons.append([make_button(user_is_premium, "Lebro [VIP]", "product_Lebro_VIP", "lebro_vip")])
        buttons.append([make_button(user_is_premium, "Lebro [Lite]", "product_Lebro_Lite", "lebro_lite")])
    else:
        buttons.append([make_button(user_is_premium, "Plutonium", "product_Plutonium", None)])
    buttons.append([make_button(user_is_premium, "Назад к играм", "back_to_catalog", "back_game")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def periods_keyboard(user_is_premium: bool, product: str):
    buttons = []
    for name, code in PERIODS[product]:
        buttons.append([make_button(user_is_premium, name, f"period_{code}", "period")])
    buttons.append([make_button(user_is_premium, "Назад к продуктам", "back_to_products", "back_game")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_keyboard(user_is_premium: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button(user_is_premium, "CryptoBot (USDT)", "pay_crypto", "crypto")],
        [make_button(user_is_premium, "Оплата гривной", "pay_uah", "uah")],
        [make_button(user_is_premium, "Назад к периодам", "back_to_periods", "back_periods")]
    ])

def check_payment_keyboard(user_is_premium: bool, invoice_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button(user_is_premium, "Проверить оплату", f"check_payment_{invoice_id}", "check")],
        [make_button(user_is_premium, "Отмена", "cancel_payment", "cancel")]
    ])

def cancel_keyboard(user_is_premium: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button(user_is_premium, "Отмена", "cancel", "cancel")]
    ])

def uah_receipt_keyboard(user_is_premium: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button(user_is_premium, "Отмена", "cancel", "cancel")]
    ])

# ========== CRYPTOPAY API ==========

class CryptoPayAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://pay.crypt.bot/api"
    
    async def create_invoice(self, amount: float, currency: str = "USDT", description: str = "") -> Optional[Dict]:
        url = f"{self.base_url}/createInvoice"
        params = {"asset": currency, "amount": str(amount), "description": description[:100]}
        headers = {"Crypto-Pay-API-Token": self.token}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("ok"):
                            return result["result"]
                    return None
        except Exception as e:
            print(f"CryptoPay error: {e}")
            return None
    
    async def check_invoice(self, invoice_id) -> Optional[Dict]:
        url = f"{self.base_url}/getInvoices"
        params = {"invoice_ids": invoice_id}
        headers = {"Crypto-Pay-API-Token": self.token}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("ok") and result["result"].get("items"):
                            return result["result"]["items"][0]
                    return None
        except Exception as e:
            print(f"Check invoice error: {e}")
            return None

crypto_api = CryptoPayAPI(CRYPTO_BOT_TOKEN)

# ========== ФУНКЦИИ ==========

def register_user(user_id, username, full_name):
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "user_id": user_id,
            "username": username or "Нет",
            "full_name": full_name,
            "active_key": None,
            "active_product": None,
            "expires_at": None,
            "purchases": [],
            "agreed": False
        }
        save_data()

def add_purchase(user_id, product_name, period, price, currency, key, status="pending"):
    purchase = {
        "product": product_name,
        "period": period,
        "price": price,
        "currency": currency,
        "key": key if key else "Ожидает выдачи",
        "purchased_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status
    }
    data["users"][str(user_id)]["purchases"].append(purchase)
    
    if status == "active" and key:
        data["users"][str(user_id)]["active_key"] = key
        data["users"][str(user_id)]["active_product"] = product_name
        days = 1 if period == "24h" else int(period.replace("d", ""))
        expires = datetime.now() + timedelta(days=days)
        data["users"][str(user_id)]["expires_at"] = expires.strftime("%Y-%m-%d %H:%M:%S")
    
    save_data()

def activate_key(user_id, key, product_name, period):
    data["users"][str(user_id)]["active_key"] = key
    data["users"][str(user_id)]["active_product"] = product_name
    days = 1 if period == "24h" else int(period.replace("d", ""))
    expires = datetime.now() + timedelta(days=days)
    data["users"][str(user_id)]["expires_at"] = expires.strftime("%Y-%m-%d %H:%M:%S")
    
    for purchase in reversed(data["users"][str(user_id)]["purchases"]):
        if purchase["product"] == product_name and purchase["period"] == period and purchase["status"] == "pending":
            purchase["status"] = "active"
            purchase["key"] = key
            break
    save_data()

async def edit_message_with_photo(message, photo_url, caption, reply_markup):
    """Редактирует существующее сообщение с фото"""
    try:
        media = InputMediaPhoto(media=photo_url, caption=caption, parse_mode="HTML")
        await message.edit_media(media=media, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message to edit not found" in str(e):
            # Если сообщение не найдено, отправляем новое
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            raise

def get_formatted_text(user_is_premium: bool, text_with_keys: str) -> str:
    """Форматирует текст с заменой ключей на эмодзи"""
    result = text_with_keys
    for key, premium_id in PREMIUM_EMOJI.items():
        placeholder = f"{{{key}}}"
        if placeholder in result:
            if user_is_premium:
                result = result.replace(placeholder, f'<tg-emoji emoji-id="{premium_id}"> </tg-emoji>')
            else:
                result = result.replace(placeholder, NORMAL_EMOJI.get(key, ""))
    return result

# ========== БОТ ==========

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def is_admin(user_id):
    return user_id == ADMIN_ID

# ========== ОСНОВНЫЕ ХЭНДЛЕРЫ ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    # Проверяем Premium
    user_is_premium = await is_premium_user(message.from_user.id)
    
    if not data["users"][str(message.from_user.id)]["agreed"]:
        rules_template = """{playcheat} <b>Правила PlayCheatGameBot</b>

{agree} <b>1. Возврат:</b> Возврата нет — при покупке цифрового товара потеря, неправильное использование никто не компенсирует.

{agree} <b>2. Ответственность:</b> Исполнитель не несёт ответственности за последствия применения.

{agree} <b>3. Общие:</b> Оплачивая услугу, вы соглашаетесь с данными правилами.

{agree} <b>4. Заключительные:</b> Исполнитель вправе изменять условия.

{agree} Нажмите на кнопку ниже, чтобы продолжить"""
        
        rules = get_formatted_text(user_is_premium, rules_template)
        await message.answer(rules, parse_mode="HTML", reply_markup=agreement_keyboard(user_is_premium))
        await state.set_state(States.waiting_agreement)
    else:
        await show_main_menu(message, user_is_premium)

@dp.callback_query(F.data == "agree")
async def agree_rules(callback: types.CallbackQuery, state: FSMContext):
    data["users"][str(callback.from_user.id)]["agreed"] = True
    save_data()
    await callback.message.delete()
    user_is_premium = await is_premium_user(callback.from_user.id)
    await show_main_menu(callback.message, user_is_premium)
    await state.clear()

async def show_main_menu(message, user_is_premium: bool):
    text_template = """{playcheat} <b>PlayCheatGameBot - Надёжный магазин читов</b>

{star} <b>Почему мы?</b>
• Моментальная выдача после оплаты
• Работает на всех устройствах (NO ROOT)
• Анонимная оплата криптовалютой
• 24/7 поддержка
• Проверенные софты

<b>Выберите действие:</b>"""
    
    text = get_formatted_text(user_is_premium, text_template)
    
    if isinstance(message, types.CallbackQuery):
        msg = message.message
    else:
        msg = message
    
    await edit_message_with_photo(msg, MENU_PHOTO, text, main_menu_keyboard(user_is_premium, is_admin(msg.chat.id)))

# ========== КАТАЛОГ ==========

@dp.callback_query(F.data == "menu_catalog")
async def menu_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_is_premium = await is_premium_user(callback.from_user.id)
    text_template = "{game_select} <b>Выберите игру:</b>"
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, CATALOG_PHOTO, text, catalog_keyboard(user_is_premium))
    await callback.answer()

@dp.callback_query(F.data == "game_oxide")
async def game_oxide(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(game="oxide", product=None, period=None)
    user_is_premium = await is_premium_user(callback.from_user.id)
    text_template = "{standoff} <b>Oxide Survival Island - Выберите софт:</b>"
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, GAME_SELECT_PHOTO, text, products_keyboard(user_is_premium, "oxide"))
    await callback.answer()

@dp.callback_query(F.data == "game_standoff")
async def game_standoff(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(game="standoff", product=None, period=None)
    user_is_premium = await is_premium_user(callback.from_user.id)
    text_template = "{standoff} <b>Standoff 2 - Выберите софт:</b>"
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, GAME_SELECT_PHOTO, text, products_keyboard(user_is_premium, "standoff"))
    await callback.answer()

@dp.callback_query(F.data.startswith("product_"))
async def select_product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.replace("product_", "")
    await state.update_data(product=product, period=None)
    user_is_premium = await is_premium_user(callback.from_user.id)
    product_name = PRODUCT_NAMES[product]
    text_template = f"{{lebroname}} <b>{product_name}</b>\n\nВыберите период действия:"
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, SYSTEM_PHOTO, text, periods_keyboard(user_is_premium, product))
    await callback.answer()

@dp.callback_query(F.data.startswith("period_"))
async def select_period(callback: types.CallbackQuery, state: FSMContext):
    period = callback.data.replace("period_", "")
    await state.update_data(period=period)
    
    data_state = await state.get_data()
    product = data_state.get("product")
    if not product:
        await callback.answer("Ошибка: выберите товар заново", show_alert=True)
        user_is_premium = await is_premium_user(callback.from_user.id)
        await show_main_menu(callback, user_is_premium)
        return
    
    user_is_premium = await is_premium_user(callback.from_user.id)
    price = PRICES[product][period]
    currency = "USDT" if "Lebro" in product else "UAH"
    
    text_template = f"{{to_pay}} <b>К оплате: {price} {currency}</b>\n\nВыберите способ оплаты:"
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, payment_keyboard(user_is_premium))
    await callback.answer()

# ========== CRYPTO ОПЛАТА ==========

@dp.callback_query(F.data == "pay_crypto")
async def pay_crypto(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    product = data_state.get("product")
    period = data_state.get("period")
    
    if not product or not period:
        await callback.answer("Ошибка: выберите товар заново", show_alert=True)
        user_is_premium = await is_premium_user(callback.from_user.id)
        await show_main_menu(callback, user_is_premium)
        return
    
    user_is_premium = await is_premium_user(callback.from_user.id)
    product_name = PRODUCT_NAMES[product]
    price = PRICES[product][period]
    
    invoice = await crypto_api.create_invoice(price, "USDT", f"{product_name} {period}")
    
    if not invoice:
        text_template = "Ошибка создания счета. Попробуйте позже."
        text = get_formatted_text(user_is_premium, text_template)
        await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, payment_keyboard(user_is_premium))
        await callback.answer()
        return
    
    invoice_id = invoice["invoice_id"]
    pay_url = invoice["pay_url"]
    
    auto_key = f"AUTO-{product_name[:4]}-{period}-{random.randint(1000, 9999)}"
    
    data["temp_invoices"][str(invoice_id)] = {
        "user_id": callback.from_user.id,
        "product": product,
        "period": period,
        "product_name": product_name,
        "price": price,
        "key": auto_key
    }
    save_data()
    
    text_template = f"""{{invoice}} <b>Создан счет на оплату</b>

{{sum}} <b>Сумма:</b> {price} USDT
{{product}} <b>Товар:</b> {product_name} ({period})

{{link}} <b>Ссылка для оплаты:</b> <a href="{pay_url}">Оплатить</a>

{{check}} После оплаты нажмите кнопку ниже для проверки"""
    
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, check_payment_keyboard(user_is_premium, invoice_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: types.CallbackQuery, state: FSMContext):
    invoice_id = int(callback.data.replace("check_payment_", ""))
    
    invoice_info = data["temp_invoices"].get(str(invoice_id))
    if not invoice_info:
        await callback.answer("Счет не найден", show_alert=True)
        return
    
    invoice = await crypto_api.check_invoice(invoice_id)
    
    if not invoice:
        await callback.answer("Ошибка проверки", show_alert=True)
        return
    
    status = invoice.get("status")
    
    if status == "paid":
        user_id = invoice_info["user_id"]
        product_name = invoice_info["product_name"]
        period = invoice_info["period"]
        price = invoice_info["price"]
        auto_key = invoice_info.get("key")
        
        add_purchase(user_id, product_name, period, price, "USDT", auto_key, status="active")
        activate_key(user_id, auto_key, product_name, period)
        
        if str(invoice_id) in data["temp_invoices"]:
            del data["temp_invoices"][str(invoice_id)]
        save_data()
        
        user_is_premium = await is_premium_user(callback.from_user.id)
        text_template = f"""{{confirmed}} <b>Ваша CRYPTO оплата подтверждена!</b>

{{product}} <b>Товар:</b> {product_name} ({period})
{{your_key}} <b>Ваш ключ:</b> <code>{auto_key}</code>

{{thanks}} Спасибо за покупку!"""
        
        text = get_formatted_text(user_is_premium, text_template)
        await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, None)
        await state.clear()
        
    elif status == "expired":
        await callback.answer("Счет просрочен. Создайте новый.", show_alert=True)
    else:
        await callback.answer(f"Статус: {status}. Оплата не обнаружена.", show_alert=True)

@dp.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_is_premium = await is_premium_user(callback.from_user.id)
    await show_main_menu(callback, user_is_premium)
    await callback.answer("Оплата отменена")

# ========== UAH ОПЛАТА ==========

@dp.callback_query(F.data == "pay_uah")
async def pay_uah(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    product = data_state.get("product")
    period = data_state.get("period")
    
    if not product or not period:
        await callback.answer("Ошибка: выберите товар заново", show_alert=True)
        user_is_premium = await is_premium_user(callback.from_user.id)
        await show_main_menu(callback, user_is_premium)
        return
    
    user_is_premium = await is_premium_user(callback.from_user.id)
    product_name = PRODUCT_NAMES[product]
    price = PRICES[product][period]
    
    await state.update_data(uah_product=product, uah_period=period, uah_price=price, uah_product_name=product_name)
    
    text_template = f"""{{period}} <b>Оплата гривной</b>

{{sum}} <b>Сумма:</b> {price} грн
{{product}} <b>Товар:</b> {product_name} ({period})

{{card}} <b>Карта для оплаты:</b> <code>{UAH_CARD}</code>
❗ <b>Комментарий:</b> <code>{UAH_COMMENT}</code>

{{receipt}} <b>После оплаты отправьте скриншот чека сюда</b>

{{card}} Без чека ключ НЕ будет выдан"""
    
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, uah_receipt_keyboard(user_is_premium))
    await state.set_state(States.waiting_uah_receipt)
    await callback.answer()

@dp.message(States.waiting_uah_receipt, F.photo)
async def receive_uah_receipt(message: types.Message, state: FSMContext):
    data_state = await state.get_data()
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    
    pending_id = f"uah_{user_id}_{int(datetime.now().timestamp())}"
    data["pending_uah"][pending_id] = {
        "user_id": user_id,
        "product": data_state.get("uah_product_name"),
        "period": data_state.get("uah_period"),
        "price": data_state.get("uah_price"),
        "photo": photo_id,
        "username": message.from_user.username or "Нет"
    }
    save_data()
    
    admin_text = f"🔔 НОВАЯ ОПЛАТА UAH\n\n👤 Пользователь: @{message.from_user.username or 'Нет'} (ID: {user_id})\n📦 Товар: {data_state.get('uah_product_name')} ({data_state.get('uah_period')})\n💰 Сумма: {data_state.get('uah_price')} грн"
    
    await bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, parse_mode="HTML")
    
    user_is_premium = await is_premium_user(message.from_user.id)
    text_template = "{receipt_sent} Чек отправлен! Администратор выдаст ключ после проверки."
    text = get_formatted_text(user_is_premium, text_template)
    await message.answer(text, parse_mode="HTML")
    await state.clear()
    await show_main_menu(message, user_is_premium)

# ========== ПРОФИЛЬ ==========

@dp.callback_query(F.data == "menu_profile")
async def menu_profile(callback: types.CallbackQuery):
    user_is_premium = await is_premium_user(callback.from_user.id)
    user = data["users"][str(callback.from_user.id)]
    
    active = user.get("active_key") or "Нет активного ключа"
    product = user.get("active_product") or "—"
    expires = user.get("expires_at") or "—"
    
    text_template = f"""{{profile}} <b>Ваш профиль</b>

{{user_id}} <b>ID:</b> <code>{user['user_id']}</code>
{{username}} <b>Юзернейм:</b> @{user['username']}
{{name}} <b>Имя:</b> {user['full_name']}

{{active_key}} <b>Активный ключ:</b> <code>{active}</code>
{{product}} <b>Товар:</b> {product}
{{expires}} <b>Срок до:</b> {expires}"""
    
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, main_menu_keyboard(user_is_premium, is_admin(callback.from_user.id)))
    await callback.answer()

# ========== МОИ ПОКУПКИ ==========

@dp.callback_query(F.data == "menu_purchases")
async def menu_purchases(callback: types.CallbackQuery):
    user_is_premium = await is_premium_user(callback.from_user.id)
    purchases = data["users"][str(callback.from_user.id)].get("purchases", [])
    
    if not purchases:
        text = "📭 <b>У вас пока нет покупок</b>"
    else:
        text_template = "{purchases} <b>ИСТОРИЯ ПОКУПОК:</b>\n\n"
        text = get_formatted_text(user_is_premium, text_template)
        for i, p in enumerate(reversed(purchases[-10:]), 1):
            status_emoji = "✅" if p['status'] == 'active' else "⏳"
            text += f"{i}. {status_emoji} <b>{p['product']}</b>\n   Период: {p['period']}\n   Цена: {p['price']} {p['currency']}\n   Ключ: <code>{p['key']}</code>\n   Дата: {p['purchased_at']}\n\n"
    
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, main_menu_keyboard(user_is_premium, is_admin(callback.from_user.id)))
    await callback.answer()

# ========== АДМИН ПАНЕЛЬ (упрощенно) ==========

@dp.callback_query(F.data == "menu_admin")
async def menu_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    user_is_premium = await is_premium_user(callback.from_user.id)
    text = "🔧 <b>Админ-панель</b>"
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, admin_panel_keyboard(user_is_premium))
    await callback.answer()

@dp.callback_query(F.data == "admin_give_key")
async def admin_give_key(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    user_is_premium = await is_premium_user(callback.from_user.id)
    text = "✏️ <b>Введите ID пользователя:</b>"
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, cancel_keyboard(user_is_premium))
    await state.set_state(States.admin_waiting_user_id)
    await callback.answer()

@dp.callback_query(F.data == "admin_confirm_uah")
async def admin_confirm_uah(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    if not data["pending_uah"]:
        await callback.answer("Нет ожидающих UAH оплат!", show_alert=True)
        return
    
    user_is_premium = await is_premium_user(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    for pid, info in data["pending_uah"].items():
        builder.button(text=f"✅ {info['username']} - {info['product']} ({info['price']} грн)", callback_data=f"confirm_uah_{pid}")
    builder.button(text="🔙 Назад", callback_data="menu_admin")
    builder.adjust(1)
    
    text = "📋 <b>Выберите UAH оплату для подтверждения:</b>"
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_uah_"))
async def confirm_uah_payment(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    pending_id = callback.data.replace("confirm_uah_", "")
    pending = data["pending_uah"].get(pending_id)
    
    if not pending:
        await callback.answer("Уже обработано!", show_alert=True)
        return
    
    user_is_premium = await is_premium_user(callback.from_user.id)
    await state.update_data(pending_id=pending_id, user_id=pending["user_id"], product_name=pending["product"], period=pending["period"])
    
    text = f"✏️ <b>Введите ключ для пользователя @{pending['username']}</b>\n\nТовар: {pending['product']} ({pending['period']})"
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, cancel_keyboard(user_is_premium))
    await state.set_state(States.admin_waiting_uah_key)
    await callback.answer()

@dp.message(States.admin_waiting_user_id)
async def get_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        if str(user_id) not in data["users"]:
            await message.answer("Пользователь не найден!")
            await state.clear()
            return
        await state.update_data(target_user=user_id)
        user_is_premium = await is_premium_user(message.from_user.id)
        await message.answer("Введите ключ:", reply_markup=cancel_keyboard(user_is_premium))
        await state.set_state(States.admin_waiting_key)
    except:
        await message.answer("Введите корректный ID!")

@dp.message(States.admin_waiting_key)
async def send_key(message: types.Message, state: FSMContext):
    data_state = await state.get_data()
    user_id = data_state["target_user"]
    key = message.text
    
    data["users"][str(user_id)]["active_key"] = key
    save_data()
    
    await bot.send_message(user_id, f"✅ Вам выдан ключ: <code>{key}</code>", parse_mode="HTML")
    await message.answer(f"✅ Ключ отправлен пользователю {user_id}")
    await state.clear()

@dp.message(States.admin_waiting_uah_key)
async def send_uah_key(message: types.Message, state: FSMContext):
    data_state = await state.get_data()
    key = message.text
    pending_id = data_state["pending_id"]
    user_id = data_state["user_id"]
    product_name = data_state["product_name"]
    period = data_state["period"]
    
    add_purchase(user_id, product_name, period, 0, "UAH", key, status="active")
    activate_key(user_id, key, product_name, period)
    
    if pending_id in data["pending_uah"]:
        del data["pending_uah"][pending_id]
    save_data()
    
    await bot.send_message(user_id, f"✅ Ваша оплата подтверждена!\n\nКлюч: <code>{key}</code>", parse_mode="HTML")
    await message.answer(f"✅ Ключ выдан пользователю {user_id}")
    await state.clear()

# ========== НАВИГАЦИЯ ==========

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_is_premium = await is_premium_user(callback.from_user.id)
    await show_main_menu(callback, user_is_premium)
    await callback.answer()

@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_is_premium = await is_premium_user(callback.from_user.id)
    text_template = "{game_select} <b>Выберите игру:</b>"
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, CATALOG_PHOTO, text, catalog_keyboard(user_is_premium))
    await callback.answer()

@dp.callback_query(F.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    game = data_state.get("game", "oxide")
    user_is_premium = await is_premium_user(callback.from_user.id)
    text_template = f"{{standoff}} <b>{'Oxide Survival Island' if game == 'oxide' else 'Standoff 2'} - Выберите софт:</b>"
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, GAME_SELECT_PHOTO, text, products_keyboard(user_is_premium, game))
    await callback.answer()

@dp.callback_query(F.data == "back_to_periods")
async def back_to_periods(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    product = data_state.get("product")
    if not product:
        user_is_premium = await is_premium_user(callback.from_user.id)
        await show_main_menu(callback, user_is_premium)
        return
    user_is_premium = await is_premium_user(callback.from_user.id)
    product_name = PRODUCT_NAMES[product]
    text_template = f"{{lebroname}} <b>{product_name}</b>\n\nВыберите период:"
    text = get_formatted_text(user_is_premium, text_template)
    await edit_message_with_photo(callback.message, PERIOD_PHOTO, text, periods_keyboard(user_is_premium, product))
    await callback.answer()

@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_is_premium = await is_premium_user(callback.from_user.id)
    await show_main_menu(callback, user_is_premium)
    await callback.answer()

# ========== ЗАПУСК ==========

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("✅ Бот запущен!")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print("📦 Жду команды...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
