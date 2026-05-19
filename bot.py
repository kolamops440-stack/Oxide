from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio

BOT_TOKEN = "8813471822:AAEWpNtYPJGVtCVeqGO5d4yvrwGOYhffpW8"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    # Текст с премиум эмодзи
    text = 'Привет, Салфетка и Хабр! <tg-emoji emoji-id="5285430309720966085">👍</tg-emoji>'
    
    # Инлайн кнопки с icon_custom_emoji_id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Опасная кнопка!",
                callback_data="btn1",
                icon_custom_emoji_id="5310169226856644648"
            ),
            InlineKeyboardButton(
                text="Успешная кнопка =)",
                callback_data="btn2",
                icon_custom_emoji_id="5310076249404621168"
            )
        ],
        [
            InlineKeyboardButton(
                text="Основная кнопка",
                callback_data="btn3",
                icon_custom_emoji_id="5285430309720966085"
            ),
            InlineKeyboardButton(
                text="Простокнопка -_-",
                callback_data="btn4",
                icon_custom_emoji_id="5285032475490273112"
            )
        ]
    ])
    
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query()
async def handle_buttons(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(f"✅ Нажата кнопка: {callback.data}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
