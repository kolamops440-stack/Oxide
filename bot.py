import asyncio
import json
import os
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict
import time
import random
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# ========== Цены ==========
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
    admin_waiting_user_id = State()
    admin_waiting_key = State()
    admin_waiting_crypto_key = State()
    admin_waiting_uah_key = State()

# ========== ФУНКЦИИ ==========

def emoji(emoji_id: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}"> </tg-emoji>'

def make_button(text: str, callback_data: str, emoji_id: str = None):
    if emoji_id:
        return InlineKeyboardButton(text=f'{emoji(emoji_id)}{text}', callback_data=callback_data)
    return InlineKeyboardButton(text=text, callback_data=callback_data)

async def safe_edit_message(message, photo_url, caption, reply_markup):
    try:
        media = InputMediaPhoto(media=photo_url, caption=caption, parse_mode="HTML")
        await message.edit_media(media=media, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as e:
        if "message to edit not found" in str(e):
            try:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo_url,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                return True
            except Exception as send_err:
                logger.error(f"Send error: {send_err}")
                return False
        else:
            logger.error(f"Edit error: {e}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

async def safe_send_message(chat_id, text, reply_markup=None):
    try:
        return await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

# ========== КЛАВИАТУРЫ ==========

def agreement_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button("Я ознакомлен с правилами", "agree", "agree")]
    ])

def main_menu_keyboard():
    buttons = [
        [
            make_button("Каталог", "menu_catalog", "catalog"),
            make_button("Профиль", "menu_profile", "profile")
        ],
        [
            make_button("Мои покупки", "menu_purchases", "purchases")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Выдать ключ пользователю", callback_data="admin_give_key")],
        [make_button("Подтвердить UAH оплату", "admin_confirm_uah", "uah")],
        [make_button("В главное меню", "back_to_main", "back_main")]
    ])

def catalog_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button("Oxide Survival Island", "game_oxide", "oxide")],
        [make_button("Standoff 2", "game_standoff", "standoff")],
        [make_button("В главное меню", "back_to_main", "back_main")]
    ])

def products_keyboard(game):
    buttons = []
    if game == "oxide":
        buttons.append([make_button("Lebro [VIP]", "product_Lebro_VIP", "lebro_vip")])
        buttons.append([make_button("Lebro [Lite]", "product_Lebro_Lite", "lebro_lite")])
    else:
        buttons.append([make_button("Plutonium", "product_Plutonium", None)])
    buttons.append([make_button("Назад к играм", "back_to_catalog", "back_game")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def periods_keyboard(product):
    buttons = []
    for name, code in PERIODS[product]:
        buttons.append([make_button(name, f"period_{code}", "period")])
    buttons.append([make_button("Назад к продуктам", "back_to_products", "back_game")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button("CryptoBot (USDT)", "pay_crypto", "crypto")],
        [make_button("Оплата гривной", "pay_uah", "uah")],
        [make_button("Назад к периодам", "back_to_periods", "back_periods")]
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button("Отмена", "cancel", "cancel")]
    ])

def uah_receipt_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_button("Отмена", "cancel", "cancel")]
    ])

# ========== ФУНКЦИИ ПОЛЬЗОВАТЕЛЕЙ ==========

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
    
    if not data["users"][str(message.from_user.id)]["agreed"]:
        rules = f"""{emoji(PREMIUM_EMOJI['playcheat'])} <b>Правила PlayCheatGameBot</b>

{emoji(PREMIUM_EMOJI['agree'])} <b>1. Возврат:</b> Возврата нет — при покупке цифрового товара потеря, неправильное использование никто не компенсирует.

{emoji(PREMIUM_EMOJI['agree'])} <b>2. Ответственность:</b> Исполнитель не несёт ответственности за последствия применения.

{emoji(PREMIUM_EMOJI['agree'])} <b>3. Общие:</b> Оплачивая услугу, вы соглашаетесь с данными правилами.

{emoji(PREMIUM_EMOJI['agree'])} <b>4. Заключительные:</b> Исполнитель вправе изменять условия.

{emoji(PREMIUM_EMOJI['agree'])} Нажмите на кнопку ниже, чтобы продолжить"""
        
        await safe_send_message(message.chat.id, rules, agreement_keyboard())
        await state.set_state(States.waiting_agreement)
    else:
        await show_main_menu(message)

@dp.callback_query(F.data == "agree")
async def agree_rules(callback: types.CallbackQuery, state: FSMContext):
    data["users"][str(callback.from_user.id)]["agreed"] = True
    save_data()
    await callback.message.delete()
    await show_main_menu(callback.message)
    await state.clear()

async def show_main_menu(message):
    text = f"""{emoji(PREMIUM_EMOJI['playcheat'])} <b>PlayCheatGameBot - Надёжный магазин читов</b>

{emoji(PREMIUM_EMOJI['star'])} <b>Почему мы?</b>
• Моментальная выдача после оплаты
• Работает на всех устройствах (NO ROOT)
• Анонимная оплата криптовалютой
• 24/7 поддержка
• Проверенные софты

<b>Выберите действие:</b>"""
    
    if isinstance(message, types.CallbackQuery):
        msg = message.message
    else:
        msg = message
    
    await safe_edit_message(msg, MENU_PHOTO, text, main_menu_keyboard())

# ========== КАТАЛОГ ==========

@dp.callback_query(F.data == "menu_catalog")
async def menu_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = f"{emoji(PREMIUM_EMOJI['game_select'])} <b>Выберите игру:</b>"
    await safe_edit_message(callback.message, CATALOG_PHOTO, text, catalog_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "game_oxide")
async def game_oxide(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(game="oxide")
    text = f"{emoji(PREMIUM_EMOJI['standoff'])} <b>Oxide Survival Island - Выберите софт:</b>"
    await safe_edit_message(callback.message, GAME_SELECT_PHOTO, text, products_keyboard("oxide"))
    await callback.answer()

@dp.callback_query(F.data == "game_standoff")
async def game_standoff(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(game="standoff")
    text = f"{emoji(PREMIUM_EMOJI['standoff'])} <b>Standoff 2 - Выберите софт:</b>"
    await safe_edit_message(callback.message, GAME_SELECT_PHOTO, text, products_keyboard("standoff"))
    await callback.answer()

@dp.callback_query(F.data.startswith("product_"))
async def select_product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.replace("product_", "")
    await state.update_data(product=product)
    product_name = PRODUCT_NAMES[product]
    text = f"{emoji(PREMIUM_EMOJI['lebroname'])} <b>{product_name}</b>\n\nВыберите период действия:"
    await safe_edit_message(callback.message, SYSTEM_PHOTO, text, periods_keyboard(product))
    await callback.answer()

@dp.callback_query(F.data.startswith("period_"))
async def select_period(callback: types.CallbackQuery, state: FSMContext):
    period = callback.data.replace("period_", "")
    await state.update_data(period=period)
    
    data_state = await state.get_data()
    product = data_state.get("product")
    if not product:
        await callback.answer("Ошибка: выберите товар заново", show_alert=True)
        await show_main_menu(callback)
        return
    
    price = PRICES[product][period]
    currency = "USDT" if "Lebro" in product else "UAH"
    
    text = f"{emoji(PREMIUM_EMOJI['to_pay'])} <b>К оплате: {price} {currency}</b>\n\nВыберите способ оплаты:"
    await safe_edit_message(callback.message, PAYMENT_PHOTO, text, payment_keyboard())
    await callback.answer()

# ========== CRYPTO ОПЛАТА (ДЕМО) ==========

@dp.callback_query(F.data == "pay_crypto")
async def pay_crypto(callback: types.CallbackQuery, state: FSMContext):
    auto_key = f"DEMO-KEY-{random.randint(10000, 99999)}"
    
    await callback.message.edit_caption(
        caption=f"{emoji(PREMIUM_EMOJI['confirmed'])} <b>Оплата прошла успешно!</b>\n\n{emoji(PREMIUM_EMOJI['your_key'])} <b>Ваш ключ:</b> <code>{auto_key}</code>\n\n{emoji(PREMIUM_EMOJI['thanks'])} Спасибо за покупку!",
        parse_mode="HTML"
    )
    await callback.answer()

# ========== UAH ОПЛАТА ==========

@dp.callback_query(F.data == "pay_uah")
async def pay_uah(callback: types.CallbackQuery, state: FSMContext):
    text = f"""{emoji(PREMIUM_EMOJI['period'])} <b>Оплата гривной</b>

{emoji(PREMIUM_EMOJI['card'])} <b>Карта для оплаты:</b> <code>{UAH_CARD}</code>
❗ <b>Комментарий:</b> <code>{UAH_COMMENT}</code>

{emoji(PREMIUM_EMOJI['receipt'])} <b>После оплаты отправьте скриншот чека сюда</b>

{emoji(PREMIUM_EMOJI['card'])} Без чека ключ НЕ будет выдан"""
    
    await callback.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=uah_receipt_keyboard())
    await state.set_state(States.waiting_uah_receipt)
    await callback.answer()

@dp.message(States.waiting_uah_receipt, F.photo)
async def receive_uah_receipt(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    
    pending_id = f"uah_{user_id}_{int(datetime.now().timestamp())}"
    data["pending_uah"][pending_id] = {
        "user_id": user_id,
        "photo": photo_id,
        "username": message.from_user.username or "Нет"
    }
    save_data()
    
    admin_text = f"🔔 НОВАЯ ОПЛАТА UAH\n\n👤 Пользователь: @{message.from_user.username or 'Нет'} (ID: {user_id})"
    
    await bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, parse_mode="HTML")
    
    text = f"{emoji(PREMIUM_EMOJI['receipt_sent'])} Чек отправлен! Администратор выдаст ключ после проверки."
    await message.answer(text, parse_mode="HTML")
    await state.clear()
    await show_main_menu(message)

# ========== ПРОФИЛЬ ==========

@dp.callback_query(F.data == "menu_profile")
async def menu_profile(callback: types.CallbackQuery):
    user = data["users"][str(callback.from_user.id)]
    
    active = user.get("active_key") or "Нет активного ключа"
    product = user.get("active_product") or "—"
    expires = user.get("expires_at") or "—"
    
    text = f"""{emoji(PREMIUM_EMOJI['profile'])} <b>Ваш профиль</b>

{emoji(PREMIUM_EMOJI['user_id'])} <b>ID:</b> <code>{user['user_id']}</code>
{emoji(PREMIUM_EMOJI['username'])} <b>Юзернейм:</b> @{user['username']}
{emoji(PREMIUM_EMOJI['name'])} <b>Имя:</b> {user['full_name']}

{emoji(PREMIUM_EMOJI['active_key'])} <b>Активный ключ:</b> <code>{active}</code>
{emoji(PREMIUM_EMOJI['product'])} <b>Товар:</b> {product}
{emoji(PREMIUM_EMOJI['expires'])} <b>Срок до:</b> {expires}"""
    
    await safe_edit_message(callback.message, MENU_PHOTO, text, main_menu_keyboard())
    await callback.answer()

# ========== МОИ ПОКУПКИ ==========

@dp.callback_query(F.data == "menu_purchases")
async def menu_purchases(callback: types.CallbackQuery):
    purchases = data["users"][str(callback.from_user.id)].get("purchases", [])
    
    if not purchases:
        text = "📭 <b>У вас пока нет покупок</b>"
    else:
        text = f"{emoji(PREMIUM_EMOJI['purchases'])} <b>ИСТОРИЯ ПОКУПОК:</b>\n\n"
        for i, p in enumerate(reversed(purchases[-10:]), 1):
            status_emoji = "✅" if p['status'] == 'active' else "⏳"
            text += f"{i}. {status_emoji} <b>{p['product']}</b>\n   Период: {p['period']}\n   Цена: {p['price']} {p['currency']}\n   Ключ: <code>{p['key']}</code>\n   Дата: {p['purchased_at']}\n\n"
    
    await safe_edit_message(callback.message, MENU_PHOTO, text, main_menu_keyboard())
    await callback.answer()

# ========== АДМИН ПАНЕЛЬ ==========

@dp.callback_query(F.data == "menu_admin")
async def menu_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    text = "🔧 <b>Админ-панель</b>"
    await safe_edit_message(callback.message, MENU_PHOTO, text, admin_panel_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_give_key")
async def admin_give_key(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    text = "✏️ <b>Введите ID пользователя:</b>"
    await safe_edit_message(callback.message, MENU_PHOTO, text, cancel_keyboard())
    await state.set_state(States.admin_waiting_user_id)
    await callback.answer()

@dp.message(States.admin_waiting_user_id)
async def get_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        if str(user_id) not in data["users"]:
            await message.answer("❌ Пользователь не найден!")
            await state.clear()
            return
        await state.update_data(target_user=user_id)
        await message.answer("🔑 <b>Введите ключ для выдачи:</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
        await state.set_state(States.admin_waiting_key)
    except:
        await message.answer("❌ Введите корректный ID (число)!")

@dp.message(States.admin_waiting_key)
async def send_key_to_user(message: types.Message, state: FSMContext):
    key = message.text
    data_state = await state.get_data()
    user_id = data_state["target_user"]
    
    data["users"][str(user_id)]["active_key"] = key
    data["users"][str(user_id)]["active_product"] = "Выдан администратором"
    data["users"][str(user_id)]["expires_at"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    save_data()
    
    try:
        await bot.send_message(user_id, f"{emoji(PREMIUM_EMOJI['confirmed'])} <b>Вам выдан ключ администратором!</b>\n\n{emoji(PREMIUM_EMOJI['your_key'])} Ключ: <code>{key}</code>\n\nИспользуйте его для активации.", parse_mode="HTML")
        await message.answer(f"✅ Ключ отправлен пользователю {user_id}!")
    except Exception as e:
        logger.error(f"Failed to send key to user {user_id}: {e}")
        await message.answer(f"⚠️ Не удалось отправить ключ пользователю {user_id}. Возможно, пользователь не начал диалог с ботом.\n\nКлюч: <code>{key}</code>", parse_mode="HTML")
    
    await state.clear()
    await show_main_menu(message)

@dp.callback_query(F.data == "admin_confirm_uah")
async def admin_confirm_uah(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    if not data["pending_uah"]:
        await callback.answer("Нет ожидающих UAH оплат!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for pid, info in data["pending_uah"].items():
        builder.button(text=f"✅ {info['username']}", callback_data=f"confirm_uah_{pid}")
    builder.button(text="🔙 Назад", callback_data="menu_admin")
    builder.adjust(1)
    
    text = "📋 <b>Выберите UAH оплату для подтверждения:</b>"
    await safe_edit_message(callback.message, MENU_PHOTO, text, builder.as_markup())
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
    
    await state.update_data(pending_id=pending_id, user_id=pending["user_id"])
    
    text = f"✏️ <b>Введите ключ для пользователя @{pending['username']}</b>"
    await safe_edit_message(callback.message, MENU_PHOTO, text, cancel_keyboard())
    await state.set_state(States.admin_waiting_uah_key)
    await callback.answer()

@dp.message(States.admin_waiting_uah_key)
async def send_uah_key(message: types.Message, state: FSMContext):
    data_state = await state.get_data()
    key = message.text
    pending_id = data_state["pending_id"]
    user_id = data_state["user_id"]
    
    data["users"][str(user_id)]["active_key"] = key
    data["users"][str(user_id)]["active_product"] = "Выдан администратором"
    data["users"][str(user_id)]["expires_at"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    if pending_id in data["pending_uah"]:
        del data["pending_uah"][pending_id]
    save_data()
    
    try:
        await bot.send_message(user_id, f"{emoji(PREMIUM_EMOJI['confirmed'])} <b>Ваша оплата подтверждена!</b>\n\n{emoji(PREMIUM_EMOJI['your_key'])} <b>Ваш ключ:</b> <code>{key}</code>\n\n{emoji(PREMIUM_EMOJI['thanks'])} Спасибо за покупку!", parse_mode="HTML")
        await message.answer(f"✅ Ключ выдан пользователю {user_id}!")
    except Exception as e:
        logger.error(f"Failed to send key to user {user_id}: {e}")
        await message.answer(f"⚠️ Не удалось отправить ключ пользователю {user_id}.\n\nКлюч: <code>{key}</code>", parse_mode="HTML")
    
    await state.clear()
    await show_main_menu(message)

# ========== НАВИГАЦИЯ ==========

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = f"{emoji(PREMIUM_EMOJI['game_select'])} <b>Выберите игру:</b>"
    await safe_edit_message(callback.message, CATALOG_PHOTO, text, catalog_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    game = data_state.get("game", "oxide")
    text = f"{emoji(PREMIUM_EMOJI['standoff'])} <b>{'Oxide Survival Island' if game == 'oxide' else 'Standoff 2'} - Выберите софт:</b>"
    await safe_edit_message(callback.message, GAME_SELECT_PHOTO, text, products_keyboard(game))
    await callback.answer()

@dp.callback_query(F.data == "back_to_periods")
async def back_to_periods(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    product = data_state.get("product")
    if not product:
        await show_main_menu(callback)
        return
    product_name = PRODUCT_NAMES[product]
    text = f"{emoji(PREMIUM_EMOJI['lebroname'])} <b>{product_name}</b>\n\nВыберите период:"
    await safe_edit_message(callback.message, PERIOD_PHOTO, text, periods_keyboard(product))
    await callback.answer()

@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback.message)
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
