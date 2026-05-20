import asyncio
import logging
import sqlite3
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

TOKEN = "8972599548:AAFp4yMJcKTp1TvQljMwwBNtpNAofLrUf00"

bot = Bot(token=TOKEN)
dp = Dispatcher()

SOKINISH_LUXATI = [
    "skat", "axmoq", "iflos", "jalab", "qotoq", "suka", "blat", "am", "kot",
    "gandon", "dalbayob", "onangni", "sharmanda", "hezzalak", "yaramas"
]

def baza_yarat():
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS statistika (
            chat_id INTEGER PRIMARY KEY,
            xabarlar_soni INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def xabarni_sana(chat_id):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO statistika (chat_id) VALUES (?)", (chat_id,))
    cursor.execute("UPDATE statistika SET xabarlar_soni = xabarlar_soni + 1 WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

async def admin_mi(message: types.Message):
    try:
        user = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return user.status in ["administrator", "creator"]
    except:
        return False

@dp.message(F.new_chat_members)
async def welcome_handler(message: types.Message):
    for user in message.new_chat_members:
        await message.answer(
            f"Assalomu alaykum, {user.full_name}! 👋\n\n"
            f"🌟 *Guruhimizga xush kelibsiz!*\n"
            f"🚫 Reklama va ssilkalar taqiqlangan.\n"
            f"❗ Haqoratli so'zlar ishlatmang.\n\n"
            f"Xush kayfiyat tilaymiz! 😊",
            parse_mode="Markdown"
        )

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "🤖 *Salom! Men guruh nazoratchisiman.*\n\n"
        "✅ Yangi a'zolarni qarshilayman.\n"
        "✅ Reklamalarni o'chiraman.\n"
        "✅ So'kinishlarni cheklayman.\n\n"
        "Meni guruhga qo'shib, *admin* qiling!",
        parse_mode="Markdown"
    )

@dp.message(Command("statistika"))
async def stat_handler(message: types.Message):
    if message.chat.type == "private":
        return await message.answer("Ushbu buyruq faqat guruhlarda ishlaydi.")
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT xabarlar_soni FROM statistika WHERE chat_id = ?", (message.chat.id,))
    natija = cursor.fetchone()
    conn.close()
    jami_xabarlar = natija[0] if natija else 0
    jami_azolar = await bot.get_chat_member_count(message.chat.id)
    await message.answer(
        f"📊 *Guruh statistikasi:*\n\n"
        f"👥 A'zolar: {jami_azolar} ta\n"
        f"💬 Jami xabarlar: {jami_xabarlar} ta",
        parse_mode="Markdown"
    )

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def group_filter(message: types.Message):
    if await admin_mi(message):
        xabarni_sana(message.chat.id)
        return
    xabar_matni = message.text.lower() if message.text else ""
    reklama_belgilari = [r"http", r"t\.me", r"@", r"\.uz", r"\.com", r"\.ru", r"www\."]
    if any(re.search(p, xabar_matni) for p in reklama_belgilari) or message.entities:
        try:
            await message.delete()
            await message.answer(f"🚫 {message.from_user.first_name}, reklamangiz o'chirildi!")
        except:
            pass
        return
    if any(soz in xabar_matni for soz in SOKINISH_LUXATI):
        try:
            await message.delete()
            await message.answer(f"❗ {message.from_user.first_name}, iltimos, chiroyli muomala qiling!")
        except:
            pass
        return
    xabarni_sana(message.chat.id)

async def main():
    logging.basicConfig(level=logging.INFO)
    baza_yarat()
    print("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot to'xtatildi.")
