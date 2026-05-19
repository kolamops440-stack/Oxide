import asyncio
import json
import os
from datetime import datetime, timedelta
import random
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== КОНФИГ ==========
BOT_TOKEN = "8813471822:AAEWpNtYPJGVtCVeqGO5d4yvrwGOYhffpW8"
ADMIN_ID = 7496589494
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
}

PRODUCT_NAMES = {
    "Lebro_Lite": "Lebro [Lite]",
    "Lebro_VIP": "Lebro [VIP]",
}

PERIODS = {
    "Lebro_Lite": [("24 часа", "24h")],
    "Lebro_VIP": [("24 часа", "24h"), ("7 дней", "7d"), ("30 дней", "30d")],
}

# ========== ДАННЫЕ ==========
DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "pending_uah": {}}

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

# ========== КЛАВИАТУРЫ ==========

def main_menu_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="🛍 Каталог", callback_data="menu_catalog"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile")
        ],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="menu_purchases")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Выдать ключ", callback_data="admin_give_key")],
        [InlineKeyboardButton(text="💰 Подтвердить UAH", callback_data="admin_confirm_uah")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]
    ])

def catalog_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Oxide Survival Island", callback_data="game_oxide")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]
    ])

def products_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Lebro [VIP]", callback_data="product_Lebro_VIP")],
        [InlineKeyboardButton(text="📱 Lebro [Lite]", callback_data="product_Lebro_Lite")],
        [InlineKeyboardButton(text="🔙 Назад к играм", callback_data="back_to_catalog")]
    ])

def periods_keyboard(product):
    buttons = []
    for name, code in PERIODS[product]:
        buttons.append([InlineKeyboardButton(text=f"⏱ {name}", callback_data=f"period_{code}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад к продуктам", callback_data="back_to_products")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇦 Оплата гривной", callback_data="pay_uah")],
        [InlineKeyboardButton(text="🔙 Назад к периодам", callback_data="back_to_periods")]
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def uah_receipt_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

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

def add_purchase(user_id, product_name, period, price, key):
    purchase = {
        "product": product_name,
        "period": period,
        "price": price,
        "currency": "UAH",
        "key": key,
        "purchased_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active"
    }
    data["users"][str(user_id)]["purchases"].append(purchase)
    data["users"][str(user_id)]["active_key"] = key
    data["users"][str(user_id)]["active_product"] = product_name
    days = 1 if period == "24h" else int(period.replace("d", ""))
    expires = datetime.now() + timedelta(days=days)
    data["users"][str(user_id)]["expires_at"] = expires.strftime("%Y-%m-%d %H:%M:%S")
    save_data()

# ========== БОТ ==========

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def is_admin(user_id):
    return user_id == ADMIN_ID

# ========== ХЭНДЛЕРЫ ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    if not data["users"][str(message.from_user.id)]["agreed"]:
        rules = """📜 <b>Правила PlayCheatGameBot</b>

✅ <b>1. Возврат:</b> Возврата нет

⚠️ <b>2. Ответственность:</b> Не несём ответственности

📜 <b>3. Общие:</b> Оплачивая услугу, вы соглашаетесь

🛡 <b>4. Заключительные:</b> Условия могут меняться

✅ Нажмите на кнопку ниже"""
        
        await message.answer(rules, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я ознакомлен", callback_data="agree")]
        ]))
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
    text = """🛡 <b>PlayCheatGameBot - Магазин читов</b>

⭐ <b>Почему мы?</b>
• Моментальная выдача
• NO ROOT
• Анонимно
• 24/7 поддержка

<b>Выберите действие:</b>"""
    
    if isinstance(message, types.CallbackQuery):
        msg = message.message
    else:
        msg = message
    
    try:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
    except:
        await msg.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())

# ========== КАТАЛОГ ==========

@dp.callback_query(F.data == "menu_catalog")
async def menu_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = "📋 <b>Выберите игру:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=catalog_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "game_oxide")
async def game_oxide(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(game="oxide")
    text = "🎮 <b>Oxide Survival Island - Выберите софт:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=products_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("product_"))
async def select_product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.replace("product_", "")
    await state.update_data(product=product)
    product_name = PRODUCT_NAMES[product]
    text = f"📦 <b>{product_name}</b>\n\nВыберите период:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=periods_keyboard(product))
    await callback.answer()

@dp.callback_query(F.data.startswith("period_"))
async def select_period(callback: types.CallbackQuery, state: FSMContext):
    period = callback.data.replace("period_", "")
    await state.update_data(period=period)
    
    data_state = await state.get_data()
    product = data_state.get("product")
    price = PRICES[product][period]
    
    text = f"💸 <b>К оплате: {price} UAH</b>\n\nВыберите способ оплаты:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=payment_keyboard())
    await callback.answer()

# ========== UAH ОПЛАТА ==========

@dp.callback_query(F.data == "pay_uah")
async def pay_uah(callback: types.CallbackQuery, state: FSMContext):
    text = f"""🇺🇦 <b>Оплата гривной</b>

💳 <b>Карта:</b> <code>{UAH_CARD}</code>
❗ <b>Комментарий:</b> <code>{UAH_COMMENT}</code>

📸 <b>После оплаты отправьте скриншот чека</b>"""
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=uah_receipt_keyboard())
    await state.set_state(States.waiting_uah_receipt)
    await callback.answer()

@dp.message(States.waiting_uah_receipt, F.photo)
async def receive_uah_receipt(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    data_state = await state.get_data()
    product = data_state.get("product")
    period = data_state.get("period")
    price = PRICES[product][period]
    
    pending_id = f"uah_{user_id}_{int(datetime.now().timestamp())}"
    data["pending_uah"][pending_id] = {
        "user_id": user_id,
        "product": product,
        "period": period,
        "price": price,
        "photo": photo_id,
        "username": message.from_user.username or "Нет"
    }
    save_data()
    
    admin_text = f"🔔 НОВАЯ ОПЛАТА UAH\n\n👤 @{message.from_user.username or 'Нет'} (ID: {user_id})\n📦 {PRODUCT_NAMES[product]} ({period})\n💰 {price} UAH"
    await bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, parse_mode="HTML")
    
    await message.answer("✅ Чек отправлен! Админ выдаст ключ.")
    await state.clear()
    await show_main_menu(message)

# ========== ПРОФИЛЬ ==========

@dp.callback_query(F.data == "menu_profile")
async def menu_profile(callback: types.CallbackQuery):
    user = data["users"][str(callback.from_user.id)]
    
    active = user.get("active_key") or "Нет ключа"
    product = user.get("active_product") or "—"
    expires = user.get("expires_at") or "—"
    
    text = f"""👤 <b>Ваш профиль</b>

🆔 ID: <code>{user['user_id']}</code>
📛 Юзернейм: @{user['username']}
👤 Имя: {user['full_name']}

🔑 Активный ключ: <code>{active}</code>
📦 Товар: {product}
⏳ Срок до: {expires}"""
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
    await callback.answer()

# ========== МОИ ПОКУПКИ ==========

@dp.callback_query(F.data == "menu_purchases")
async def menu_purchases(callback: types.CallbackQuery):
    purchases = data["users"][str(callback.from_user.id)].get("purchases", [])
    
    if not purchases:
        text = "📭 <b>У вас пока нет покупок</b>"
    else:
        text = "📜 <b>ИСТОРИЯ ПОКУПОК:</b>\n\n"
        for i, p in enumerate(reversed(purchases[-10:]), 1):
            text += f"{i}. <b>{p['product']}</b>\n   Период: {p['period']}\n   Цена: {p['price']} {p['currency']}\n   Ключ: <code>{p['key']}</code>\n   Дата: {p['purchased_at']}\n\n"
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
    await callback.answer()

# ========== АДМИН ПАНЕЛЬ ==========

@dp.callback_query(F.data == "menu_admin")
async def menu_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    text = "🔧 <b>Админ-панель</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_panel_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_give_key")
async def admin_give_key(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    text = "✏️ <b>Введите ID пользователя:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=cancel_keyboard())
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
        await message.answer("🔑 <b>Введите ключ:</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
        await state.set_state(States.admin_waiting_key)
    except:
        await message.answer("❌ Введите ID числом!")

@dp.message(States.admin_waiting_key)
async def send_key(message: types.Message, state: FSMContext):
    key = message.text
    data_state = await state.get_data()
    user_id = data_state["target_user"]
    
    data["users"][str(user_id)]["active_key"] = key
    save_data()
    
    try:
        await bot.send_message(user_id, f"✅ <b>Вам выдан ключ!</b>\n\n🔑 Ключ: <code>{key}</code>", parse_mode="HTML")
        await message.answer(f"✅ Ключ отправлен пользователю {user_id}!")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}\n\nКлюч: <code>{key}</code>", parse_mode="HTML")
    
    await state.clear()
    await show_main_menu(message)

@dp.callback_query(F.data == "admin_confirm_uah")
async def admin_confirm_uah(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    if not data["pending_uah"]:
        await callback.answer("Нет оплат!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for pid, info in data["pending_uah"].items():
        builder.button(text=f"✅ {info['username']} - {info['product']}", callback_data=f"confirm_{pid}")
    builder.button(text="🔙 Назад", callback_data="menu_admin")
    builder.adjust(1)
    
    await callback.message.edit_text("📋 Выберите оплату:", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_payment(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    pending_id = callback.data.replace("confirm_", "")
    pending = data["pending_uah"].get(pending_id)
    
    if not pending:
        await callback.answer("Уже обработано!", show_alert=True)
        return
    
    await state.update_data(pending_id=pending_id, user_id=pending["user_id"], 
                          product=pending["product"], period=pending["period"], price=pending["price"])
    
    text = f"✏️ <b>Введите ключ для @{pending['username']}</b>\n\nТовар: {PRODUCT_NAMES[pending['product']]} ({pending['period']})"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=cancel_keyboard())
    await state.set_state(States.admin_waiting_key)
    await callback.answer()

# ========== НАВИГАЦИЯ ==========

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_main_menu(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = "📋 <b>Выберите игру:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=catalog_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    game = data_state.get("game", "oxide")
    text = f"🎮 <b>Oxide Survival Island - Выберите софт:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=products_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_periods")
async def back_to_periods(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    product = data_state.get("product")
    if not product:
        await show_main_menu(callback)
        return
    product_name = PRODUCT_NAMES[product]
    text = f"📦 <b>{product_name}</b>\n\nВыберите период:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=periods_keyboard(product))
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
