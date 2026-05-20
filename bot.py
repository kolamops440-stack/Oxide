import json
import os
import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

# ========== КОНФИГ ==========
BOT_TOKEN = "8813471822:AAEWpNtYPJGVtCVeqGO5d4yvrwGOYhffpW8"
ADMIN_ID = 7496589494
UAH_CARD = "4441111008011946"
UAH_COMMENT = "За цифрові товари"

# ========== ФУНКЦИЯ ЭМОДЗИ (как в твоём коде) ==========
def emoji(emoji_id: str, char: str = " ") -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{char}</tg-emoji>'

# ========== ID Telegram Premium эмодзи ==========
EMOJI_IDS = {
    "crown": "5931409969613116639",
    "star": "5805532930662996322",
    "catalog": "5208513917965328345",
    "profile": "5886412370347036129",
    "purchases": "5983399041197675256",
    "oxide": "5312048193444282508",
    "standoff": "5819078828017849357",
    "back": "5877629862306385808",
    "vip": "5208422125924275090",
    "lite": "5208422125924275090",
    "time": "5985596818912712352",
    "crypto": "5361914370068613491",
    "uah": "5805532930662996322",
    "invoice": "5983399041197675256",
    "sum": "5208513917965328345",
    "product": "5877260593903177342",
    "link": "5877465816030515018",
    "check": "6005843436479975944",
    "cancel": "5985346521103604145",
    "card": "5208431570557360595",
    "receipt": "6050592962730005028",
    "key": "6005570495603282482",
    "id": "5886505193180239900",
    "username": "5771887475421090729",
    "name": "5897962422169243693",
    "expires": "5897962422169243693",
    "game": "5960551395730919906",
    "category": "5350291836378307462",
}

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

# ========== КЛАВИАТУРЫ (как в твоём коде) ==========

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['catalog'], '🛒')} Магазин", callback_data="menu_catalog", icon_custom_emoji_id=EMOJI_IDS['catalog']),
            InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['profile'], '👤')} Профиль", callback_data="menu_profile", icon_custom_emoji_id=EMOJI_IDS['profile'])
        ],
        [
            InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['purchases'], '📦')} Мои покупки", callback_data="menu_purchases", icon_custom_emoji_id=EMOJI_IDS['purchases'])
        ]
    ])

def admin_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['vip'], '🔑')} Выдать ключ", callback_data="admin_give_key", icon_custom_emoji_id=EMOJI_IDS['vip'])],
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['uah'], '💰')} Подтвердить UAH", callback_data="admin_confirm_uah", icon_custom_emoji_id=EMOJI_IDS['uah'])],
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['back'], '🔙')} В главное меню", callback_data="back_to_main", icon_custom_emoji_id=EMOJI_IDS['back'])]
    ])

def catalog_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['oxide'], '🔥')} Oxide Survival Island", callback_data="game_oxide", icon_custom_emoji_id=EMOJI_IDS['oxide'])],
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['back'], '🔙')} В главное меню", callback_data="back_to_main", icon_custom_emoji_id=EMOJI_IDS['back'])]
    ])

def products_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['vip'], '💎')} Lebro [VIP]", callback_data="product_Lebro_VIP", icon_custom_emoji_id=EMOJI_IDS['vip'])],
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['lite'], '📱')} Lebro [Lite]", callback_data="product_Lebro_Lite", icon_custom_emoji_id=EMOJI_IDS['lite'])],
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['back'], '🔙')} Назад к играм", callback_data="back_to_catalog", icon_custom_emoji_id=EMOJI_IDS['back'])]
    ])

def periods_keyboard(product):
    buttons = []
    for name, code in PERIODS[product]:
        buttons.append([InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['time'], '⏱')} {name}", callback_data=f"period_{code}", icon_custom_emoji_id=EMOJI_IDS['time'])])
    buttons.append([InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['back'], '🔙')} Назад к продуктам", callback_data="back_to_products", icon_custom_emoji_id=EMOJI_IDS['back'])])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['crypto'], '💸')} CryptoBot (USDT)", callback_data="pay_crypto", icon_custom_emoji_id=EMOJI_IDS['crypto'])],
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['uah'], '🇺🇦')} Оплата гривной", callback_data="pay_uah", icon_custom_emoji_id=EMOJI_IDS['uah'])],
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['back'], '🔙')} Назад к периодам", callback_data="back_to_periods", icon_custom_emoji_id=EMOJI_IDS['back'])]
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['cancel'], '❌')} Отмена", callback_data="cancel", icon_custom_emoji_id=EMOJI_IDS['cancel'])]
    ])

def agreement_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['cancel'], '✅')} Я ознакомлен с правилами", callback_data="agree", icon_custom_emoji_id=EMOJI_IDS['cancel'])]
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

def add_purchase(user_id, product_name, period, price, currency, key, status="active"):
    purchase = {
        "product": product_name,
        "period": period,
        "price": price,
        "currency": currency,
        "key": key,
        "purchased_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status
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
        rules = f'''
{emoji(EMOJI_IDS["crown"], "👑")} <b>ПРАВИЛА PlayCheatGameBot</b>

{emoji(EMOJI_IDS["cancel"], "✅")} <b>1. Возврат:</b> Возврата нет

{emoji(EMOJI_IDS["cancel"], "⚠️")} <b>2. Ответственность:</b> Не несём ответственности

{emoji(EMOJI_IDS["cancel"], "📜")} <b>3. Общие:</b> Оплачивая услугу, вы соглашаетесь

{emoji(EMOJI_IDS["cancel"], "🛡️")} <b>4. Заключительные:</b> Условия могут меняться

{emoji(EMOJI_IDS["cancel"], "✅")} Нажмите на кнопку ниже
'''
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
    text = f'''
{emoji(EMOJI_IDS["crown"], "👑")} <b>PlayCheatGameBot - Надёжный магазин читов</b>

{emoji(EMOJI_IDS["star"], "⭐")} <b>Почему мы?</b>
• Моментальная выдача после оплаты
• Работает на всех устройствах (NO ROOT)
• Анонимная оплата криптовалютой
• 24/7 поддержка
• Проверенные софты

<b>Выберите действие:</b>
'''
    if isinstance(message, types.CallbackQuery):
        msg = message.message
    else:
        msg = message
    try:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    except:
        await msg.answer(text, parse_mode="HTML", reply_markup=main_menu())

# ========== КАТАЛОГ ==========

@dp.callback_query(F.data == "menu_catalog")
async def menu_catalog(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = f"{emoji(EMOJI_IDS['game'], '📋')} <b>Выберите игру:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=catalog_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "game_oxide")
async def game_oxide(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(game="oxide")
    text = f"{emoji(EMOJI_IDS['standoff'], '🎮')} <b>Oxide Survival Island - Выберите софт:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=products_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("product_"))
async def select_product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.replace("product_", "")
    await state.update_data(product=product)
    product_name = PRODUCT_NAMES[product]
    text = f"{emoji(EMOJI_IDS['product'], '📦')} <b>{product_name}</b>\n\nВыберите период действия:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=periods_keyboard(product))
    await callback.answer()

@dp.callback_query(F.data.startswith("period_"))
async def select_period(callback: types.CallbackQuery, state: FSMContext):
    period = callback.data.replace("period_", "")
    await state.update_data(period=period)
    data_state = await state.get_data()
    product = data_state.get("product")
    price = PRICES[product][period]
    text = f"{emoji(EMOJI_IDS['sum'], '💸')} <b>К оплате: {price} USDT</b>\n\nВыберите способ оплаты:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=payment_keyboard())
    await callback.answer()

# ========== CRYPTO ОПЛАТА ==========

@dp.callback_query(F.data == "pay_crypto")
async def pay_crypto(callback: types.CallbackQuery, state: FSMContext):
    data_state = await state.get_data()
    product = data_state.get("product")
    period = data_state.get("period")
    product_name = PRODUCT_NAMES[product]
    price = PRICES[product][period]
    auto_key = f"DEMO-{product_name[:4]}-{period}-{random.randint(1000, 9999)}"
    add_purchase(callback.from_user.id, product_name, period, price, "USDT", auto_key)
    text = f'''
{emoji(EMOJI_IDS["invoice"], "✅")} <b>Оплата прошла успешно!</b>

{emoji(EMOJI_IDS["sum"], "💰")} <b>Сумма:</b> {price} USDT
{emoji(EMOJI_IDS["product"], "📦")} <b>Товар:</b> {product_name} ({period})
{emoji(EMOJI_IDS["key"], "🔑")} <b>Ваш ключ:</b> <code>{auto_key}</code>

{emoji(EMOJI_IDS["star"], "🎉")} Спасибо за покупку!
'''
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

# ========== UAH ОПЛАТА ==========

@dp.callback_query(F.data == "pay_uah")
async def pay_uah(callback: types.CallbackQuery, state: FSMContext):
    text = f'''
{emoji(EMOJI_IDS["uah"], "🇺🇦")} <b>Оплата гривной</b>

{emoji(EMOJI_IDS["card"], "💳")} <b>Карта:</b> <code>{UAH_CARD}</code>
❗ <b>Комментарий:</b> <code>{UAH_COMMENT}</code>

{emoji(EMOJI_IDS["receipt"], "📸")} <b>После оплаты отправьте скриншот чека</b>

{emoji(EMOJI_IDS["card"], "⚠️")} Без чека ключ НЕ будет выдан
'''
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=cancel_keyboard())
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
    product_name = PRODUCT_NAMES[product]
    pending_id = f"uah_{user_id}_{int(datetime.now().timestamp())}"
    data["pending_uah"][pending_id] = {
        "user_id": user_id,
        "product": product,
        "period": period,
        "price": price,
        "product_name": product_name,
        "photo": photo_id,
        "username": message.from_user.username or "Нет"
    }
    save_data()
    admin_text = f"🔔 НОВАЯ ОПЛАТА UAH\n\n👤 @{message.from_user.username or 'Нет'} (ID: {user_id})\n📦 {product_name} ({period})\n💰 {price} UAH"
    await bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, parse_mode="HTML")
    text = f"{emoji(EMOJI_IDS['receipt'], '✅')} Чек отправлен! Администратор выдаст ключ после проверки."
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
    text = f'''
{emoji(EMOJI_IDS["profile"], "👤")} <b>Ваш профиль</b>

{emoji(EMOJI_IDS["id"], "🆔")} <b>ID:</b> <code>{user['user_id']}</code>
{emoji(EMOJI_IDS["username"], "📛")} <b>Юзернейм:</b> @{user['username']}
{emoji(EMOJI_IDS["name"], "👤")} <b>Имя:</b> {user['full_name']}

{emoji(EMOJI_IDS["key"], "🔑")} <b>Активный ключ:</b> <code>{active}</code>
{emoji(EMOJI_IDS["product"], "📦")} <b>Товар:</b> {product}
{emoji(EMOJI_IDS["expires"], "⏳")} <b>Срок до:</b> {expires}
'''
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await callback.answer()

# ========== МОИ ПОКУПКИ ==========

@dp.callback_query(F.data == "menu_purchases")
async def menu_purchases(callback: types.CallbackQuery):
    purchases = data["users"][str(callback.from_user.id)].get("purchases", [])
    if not purchases:
        text = "📭 <b>У вас пока нет покупок</b>"
    else:
        text = f"{emoji(EMOJI_IDS['purchases'], '📜')} <b>ИСТОРИЯ ПОКУПОК:</b>\n\n"
        for i, p in enumerate(reversed(purchases[-10:]), 1):
            text += f"{i}. <b>{p['product']}</b>\n   Период: {p['period']}\n   Цена: {p['price']} {p['currency']}\n   Ключ: <code>{p['key']}</code>\n   Дата: {p['purchased_at']}\n\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu())
    await callback.answer()

# ========== АДМИН ПАНЕЛЬ ==========

@dp.callback_query(F.data == "menu_admin")
async def menu_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    text = f"{emoji(EMOJI_IDS['crown'], '🔧')} <b>Админ-панель</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_panel())
    await callback.answer()

@dp.callback_query(F.data == "admin_give_key")
async def admin_give_key(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    text = f"{emoji(EMOJI_IDS['product'], '✏️')} <b>Введите ID пользователя:</b>"
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
            await show_main_menu(message)
            return
        await state.update_data(target_user=user_id)
        text = f"{emoji(EMOJI_IDS['key'], '🔑')} <b>Введите ключ:</b>"
        await message.answer(text, parse_mode="HTML", reply_markup=cancel_keyboard())
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
        await bot.send_message(user_id, f"{emoji(EMOJI_IDS['crown'], '✅')} <b>Вам выдан ключ!</b>\n\n{emoji(EMOJI_IDS['key'], '🔑')} Ключ: <code>{key}</code>", parse_mode="HTML")
        await message.answer(f"✅ Ключ отправлен пользователю {user_id}!")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка\n\nКлюч: <code>{key}</code>", parse_mode="HTML")
    await state.clear()
    await show_main_menu(message)

@dp.callback_query(F.data == "admin_confirm_uah")
async def admin_confirm_uah(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    if not data["pending_uah"]:
        await callback.answer("Нет оплат!", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    buttons = []
    for pid, info in data["pending_uah"].items():
        buttons.append([InlineKeyboardButton(text=f"✅ {info['username']} - {info['product_name']}", callback_data=f"confirm_{pid}")])
    buttons.append([InlineKeyboardButton(text=f"{emoji(EMOJI_IDS['back'], '🔙')} Назад", callback_data="menu_admin", icon_custom_emoji_id=EMOJI_IDS['back'])])
    keyboard.inline_keyboard = buttons
    text = f"{emoji(EMOJI_IDS['catalog'], '📋')} <b>Выберите оплату:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
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
    await state.update_data(pending_id=pending_id, user_id=pending["user_id"], product=pending["product"], period=pending["period"], product_name=pending["product_name"])
    text = f"{emoji(EMOJI_IDS['key'], '✏️')} <b>Введите ключ для @{pending['username']}</b>\n\nТовар: {pending['product_name']} ({pending['period']})"
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
    text = f"{emoji(EMOJI_IDS['game'], '📋')} <b>Выберите игру:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=catalog_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_products")
async def back_to_products(callback: types.CallbackQuery, state: FSMContext):
    text = f"{emoji(EMOJI_IDS['standoff'], '🎮')} <b>Oxide Survival Island - Выберите софт:</b>"
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
    text = f"{emoji(EMOJI_IDS['product'], '📦')} <b>{product_name}</b>\n\nВыберите период:"
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
