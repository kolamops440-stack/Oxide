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

# ========== КОНФИГ ==========
BOT_TOKEN = "8614807346:AAFhTgIEGVEIj3q2UTOxkeIIvBisn47TUdc"
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

# ========== ФУНКЦИЯ ДЛЯ ЭМОДЗИ ==========
def emoji(emoji_id: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}"> </tg-emoji>'

def make_premium_button(text: str, callback_data: str, emoji_id: str = None):
    if emoji_id:
        return InlineKeyboardButton(text=f'{emoji(emoji_id)}{text}', callback_data=callback_data)
    return InlineKeyboardButton(text=text, callback_data=callback_data)

# ========== КЛАВИАТУРЫ ==========

def agreement_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_premium_button("Я ознакомлен с правилами", "agree", "5985346521103604145")]
    ])

def main_menu_keyboard(is_admin=False):
    buttons = [
        [
            make_premium_button("Каталог", "menu_catalog", "5208513917965328345"),
            make_premium_button("Профиль", "menu_profile", "5886412370347036129")
        ],
        [
            make_premium_button("Мои покупки", "menu_purchases", "5983399041197675256")
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🔧 Админ-панель", callback_data="menu_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Выдать ключ пользователю", callback_data="admin_give_key")],
        [make_premium_button("Подтвердить UAH оплату", "admin_confirm_uah", "5805532930662996322")],
        [make_premium_button("Подтвердить CRYPTO оплату", "admin_confirm_crypto", "5361914370068613491")],
        [make_premium_button("В главное меню", "back_to_main", "5877629862306385808")]
    ])

def catalog_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_premium_button("Oxide Survival Island", "game_oxide", "5312048193444282508")],
        [make_premium_button("Standoff 2", "game_standoff", "5819078828017849357")],
        [make_premium_button("В главное меню", "back_to_main", "5877629862306385808")]
    ])

def products_keyboard(game):
    buttons = []
    if game == "oxide":
        buttons.append([make_premium_button("Lebro [VIP]", "product_Lebro_VIP", "5208422125924275090")])
        buttons.append([make_premium_button("Lebro [Lite]", "product_Lebro_Lite", "5208422125924275090")])
    else:
        buttons.append([make_premium_button("Plutonium", "product_Plutonium", None)])
    buttons.append([make_premium_button("Назад к играм", "back_to_catalog", "5877629862306385808")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def periods_keyboard(product):
    buttons = []
    for name, code in PERIODS[product]:
        buttons.append([make_premium_button(name, f"period_{code}", "5985596818912712352")])
    buttons.append([make_premium_button("Назад к продуктам", "back_to_products", "5877629862306385808")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_premium_button("CryptoBot (USDT)", "pay_crypto", "5361914370068613491")],
        [make_premium_button("Оплата гривной", "pay_uah", "5805532930662996322")],
        [make_premium_button("Назад к периодам", "back_to_periods", "5877629862306385808")]
    ])

def check_payment_keyboard(invoice_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_premium_button("Проверить оплату", f"check_payment_{invoice_id}", "6005843436479975944")],
        [make_premium_button("Отмена", "cancel_payment", "5985346521103604145")]
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_premium_button("Отмена", "cancel", "5985346521103604145")]
    ])

def uah_receipt_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_premium_button("Отмена", "cancel", "5985346521103604145")]
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
    media = InputMediaPhoto(media=photo_url, caption=caption, parse_mode="HTML")
    await message.edit_media(media=media, reply_markup=reply_markup)

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
        rules = f"""{emoji("5931409969613116639")} <b>Правила PlayCheatGameBot</b>

{emoji("5985346521103604145")} <b>1. Возврат:</b> Возврата нет — при покупке цифрового товара потеря, неправильное использование никто не компенсирует.

{emoji("5985346521103604145")} <b>2. Ответственность:</b> Исполнитель не несёт ответственности за последствия применения.

{emoji("5985346521103604145")} <b>3. Общие:</b> Оплачивая услугу, вы соглашаетесь с данными правилами.

{emoji("5985346521103604145")} <b>4. Заключительные:</b> Исполнитель вправе изменять условия.

{emoji("5985346521103604145")} Нажмите на кнопку ниже, чтобы продолжить"""
        await message.answer(rules, parse_mode="HTML", reply_markup=agreement_keyboard())
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
    text = f"""{emoji("5931409969613116639")} <b>PlayCheatGameBot - Надёжный магазин читов</b>

{emoji("5805532930662996322")} <b>Почему мы?</b>
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
    
    await edit_message_with_photo(msg, MENU_PHOTO, text, main_menu_keyboard(is_admin(msg.chat.id)))

# ========== КАТАЛОГ ==========

@dp.callback_query(F.data == "menu_catalog")
async def menu_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = f"{emoji('5960551395730919906')} <b>Выберите игру:</b>"
    await edit_message_with_photo(callback.message, CATALOG_PHOTO, text, catalog_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "game_oxide")
async def game_oxide(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(game="oxide", product=None, period=None)
    text = f"{emoji('5819078828017849357')} <b>Oxide Survival Island - Выберите софт:</b>"
    await edit_message_with_photo(callback.message, GAME_SELECT_PHOTO, text, products_keyboard("oxide"))
    await callback.answer()

@dp.callback_query(F.data == "game_standoff")
async def game_standoff(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(game="standoff", product=None, period=None)
    text = f"{emoji('5819078828017849357')} <b>Standoff 2 - Выберите софт:</b>"
    await edit_message_with_photo(callback.message, GAME_SELECT_PHOTO, text, products_keyboard("standoff"))
    await callback.answer()

@dp.callback_query(F.data.startswith("product_"))
async def select_product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.replace("product_", "")
    await state.update_data(product=product, period=None)
    product_name = PRODUCT_NAMES[product]
    text = f"{emoji('5877260593903177342')} <b>{product_name}</b>\n\nВыберите период действия:"
    await edit_message_with_photo(callback.message, SYSTEM_PHOTO, text, periods_keyboard(product))
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
    
    text = f"{emoji('5983399041197675256')} <b>К оплате: {price} {currency}</b>\n\nВыберите способ оплаты:"
    await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, payment_keyboard())
    await callback.answer()

# ========== CRYPTO ОПЛАТА ==========

@dp.callback_query(F.data == "pay_crypto")
async def pay_crypto(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    product = data_state.get("product")
    period = data_state.get("period")
    
    if not product or not period:
        await callback.answer("Ошибка: выберите товар заново", show_alert=True)
        await show_main_menu(callback)
        return
    
    product_name = PRODUCT_NAMES[product]
    price = PRICES[product][period]
    
    invoice = await crypto_api.create_invoice(price, "USDT", f"{product_name} {period}")
    
    if not invoice:
        text = "Ошибка создания счета. Попробуйте позже."
        await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, payment_keyboard())
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
    
    text = f"""{emoji("5983399041197675256")} <b>Создан счет на оплату</b>

{emoji("5208513917965328345")} <b>Сумма:</b> {price} USDT
{emoji("5877260593903177342")} <b>Товар:</b> {product_name} ({period})

{emoji("5877465816030515018")} <b>Ссылка для оплаты:</b> <a href="{pay_url}">Оплатить</a>

{emoji("6005843436479975944")} После оплаты нажмите кнопку ниже для проверки"""
    
    await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, check_payment_keyboard(invoice_id))
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
        
        text = f"""{emoji("5985596818912712352")} <b>Ваша CRYPTO оплата подтверждена!</b>

{emoji("5208513917965328345")} <b>Товар:</b> {product_name} ({period})
{emoji("6005570495603282482")} <b>Ваш ключ:</b> <code>{auto_key}</code>

{emoji("5985596818912712352")} Спасибо за покупку!"""
        
        await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, None)
        await state.clear()
        
    elif status == "expired":
        await callback.answer("Счет просрочен. Создайте новый.", show_alert=True)
    else:
        await callback.answer(f"Статус: {status}. Оплата не обнаружена.", show_alert=True)

@dp.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback)
    await callback.answer("Оплата отменена")

# ========== UAH ОПЛАТА ==========

@dp.callback_query(F.data == "pay_uah")
async def pay_uah(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    product = data_state.get("product")
    period = data_state.get("period")
    
    if not product or not period:
        await callback.answer("Ошибка: выберите товар заново", show_alert=True)
        await show_main_menu(callback)
        return
    
    product_name = PRODUCT_NAMES[product]
    price = PRICES[product][period]
    
    await state.update_data(uah_product=product, uah_period=period, uah_price=price, uah_product_name=product_name)
    
    text = f"""{emoji("5985596818912712352")} <b>Оплата гривной</b>

{emoji("5208513917965328345")} <b>Сумма:</b> {price} грн
{emoji("5877260593903177342")} <b>Товар:</b> {product_name} ({period})

{emoji("5208431570557360595")} <b>Карта для оплаты:</b> <code>{UAH_CARD}</code>
❗ <b>Комментарий:</b> <code>{UAH_COMMENT}</code>

{emoji("6050592962730005028")} <b>После оплаты отправьте скриншот чека сюда</b>

{emoji("5208431570557360595")} Без чека ключ НЕ будет выдан"""
    
    await edit_message_with_photo(callback.message, PAYMENT_PHOTO, text, uah_receipt_keyboard())
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
    
    text = f"{emoji('5985596818912712352')} Чек отправлен! Администратор выдаст ключ после проверки."
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
    
    text = f"""{emoji("5886412370347036129")} <b>Ваш профиль</b>

{emoji("5886505193180239900")} <b>ID:</b> <code>{user['user_id']}</code>
{emoji("5771887475421090729")} <b>Юзернейм:</b> @{user['username']}
{emoji("5897962422169243693")} <b>Имя:</b> {user['full_name']}

{emoji("6005570495603282482")} <b>Активный ключ:</b> <code>{active}</code>
{emoji("5208513917965328345")} <b>Товар:</b> {product}
{emoji("5897962422169243693")} <b>Срок до:</b> {expires}"""
    
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, main_menu_keyboard(is_admin(callback.from_user.id)))
    await callback.answer()

# ========== МОИ ПОКУПКИ ==========

@dp.callback_query(F.data == "menu_purchases")
async def menu_purchases(callback: types.CallbackQuery):
    purchases = data["users"][str(callback.from_user.id)].get("purchases", [])
    
    if not purchases:
        text = "📭 <b>У вас пока нет покупок</b>"
    else:
        text = f"{emoji('5983399041197675256')} <b>ИСТОРИЯ ПОКУПОК:</b>\n\n"
        for i, p in enumerate(reversed(purchases[-10:]), 1):
            status_emoji = "✅" if p['status'] == 'active' else "⏳"
            text += f"{i}. {status_emoji} <b>{p['product']}</b>\n   Период: {p['period']}\n   Цена: {p['price']} {p['currency']}\n   Ключ: <code>{p['key']}</code>\n   Дата: {p['purchased_at']}\n\n"
    
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, main_menu_keyboard(is_admin(callback.from_user.id)))
    await callback.answer()

# ========== АДМИН ПАНЕЛЬ ==========

@dp.callback_query(F.data == "menu_admin")
async def menu_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    text = "🔧 <b>Админ-панель</b>"
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, admin_panel_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_give_key")
async def admin_give_key(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    text = "✏️ <b>Введите ID пользователя:</b>"
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, cancel_keyboard())
    await state.set_state(States.admin_waiting_user_id)
    await callback.answer()

@dp.callback_query(F.data == "admin_confirm_uah")
async def admin_confirm_uah(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    if not data["pending_uah"]:
        await callback.answer("Нет ожидающих UAH оплат!", show_alert=True)
        return
    
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
    
    await state.update_data(pending_id=pending_id, user_id=pending["user_id"], product_name=pending["product"], period=pending["period"])
    
    text = f"✏️ <b>Введите ключ для пользователя @{pending['username']}</b>\n\nТовар: {pending['product']} ({pending['period']})"
    await edit_message_with_photo(callback.message, MENU_PHOTO, text, cancel_keyboard())
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
        await message.answer("Введите ключ:", reply_markup=cancel_keyboard())
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
    await show_main_menu(callback)
    await callback.answer()

@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = f"{emoji('5960551395730919906')} <b>Выберите игру:</b>"
    await edit_message_with_photo(callback.message, CATALOG_PHOTO, text, catalog_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    game = data_state.get("game", "oxide")
    text = f"{emoji('5819078828017849357')} <b>{'Oxide Survival Island' if game == 'oxide' else 'Standoff 2'} - Выберите софт:</b>"
    await edit_message_with_photo(callback.message, GAME_SELECT_PHOTO, text, products_keyboard(game))
    await callback.answer()

@dp.callback_query(F.data == "back_to_periods")
async def back_to_periods(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    product = data_state.get("product")
    if not product:
        await show_main_menu(callback)
        return
    product_name = PRODUCT_NAMES[product]
    text = f"{emoji('5877260593903177342')} <b>{product_name}</b>\n\nВыберите период:"
    await edit_message_with_photo(callback.message, PERIOD_PHOTO, text, periods_keyboard(product))
    await callback.answer()

@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback)
    await callback.answer()

# ========== ЗАПУСК ==========

async def main():
    # Удаляем вебхук встроенным методом бота
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("✅ Бот запущен!")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print("📦 Жду команды...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
