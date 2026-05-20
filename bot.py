import asyncio
import logging
import sqlite3
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

TOKEN = "8972599548:AAFp4yMJcKTp1TvQljMwwBNtpNAofLrUf00"
KANAL = "@theazizbekgporg"

bot = Bot(token=TOKEN)
dp = Dispatcher()

SOKINISH_LUXATI = [
    "skat", "axmoq", "iflos", "jalab", "qotoq", "suka", "blat", "am", "kot",
    "gandon", "dalbayob", "onangni", "sharmanda", "hezzalak", "yaramas"
]

# --- HTTP SERVER (Render uchun) ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")
    def log_message(self, format, *args):
        pass

def http_server():
    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

# --- MA'LUMOTLAR BAZASI ---
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

# --- ADMIN TEKSHIRUVI ---
async def admin_mi(message: types.Message):
    try:
        user = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return user.status in ["administrator", "creator"]
    except:
        return False

# --- KANALGA A'ZO TEKSHIRUVI ---
async def azomi(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(KANAL, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

# --- MAJBURIY A'ZOLIK TUGMASI ---
def azolik_tugmasi():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=f"https://t.me/{KANAL[1:]}")],
        [InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="tekshir")]
    ])

# --- YANGI A'ZO ---
@dp.message(F.new_chat_members)
async def welcome_handler(message: types.Message):
    for user in message.new_chat_members:
        if user.is_bot:
            continue
        agar_azo = await azomi(user.id)
        if not agar_azo:
            try:
                await bot.restrict_chat_member(
                    message.chat.id, user.id,
                    permissions=ChatPermissions(can_send_messages=False)
                )
            except:
                pass
            await message.answer(
                f"Salom {user.full_name}! 👋\n\n"
                f"Guruhda yozish uchun avval kanalimizga a'zo bo'ling:",
                reply_markup=azolik_tugmasi()
            )
        else:
            await message.answer(
                f"Assalomu alaykum, {user.full_name}! 👋\n\n"
                f"🌟 *Guruhimizga xush kelibsiz!*\n"
                f"🚫 Reklama taqiqlangan.\n"
                f"❗ Haqoratli so'zlar ishlatmang.\n\n"
                f"Xush kayfiyat! 😊",
                parse_mode="Markdown"
            )

# --- A'ZO BO'LDIM TUGMASI ---
@dp.callback_query(F.data == "tekshir")
async def tekshir_handler(callback: types.CallbackQuery):
    agar_azo = await azomi(callback.from_user.id)
    if agar_azo:
        try:
            await bot.restrict_chat_member(
                callback.message.chat.id,
                callback.from_user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True
                )
            )
        except:
            pass
        await callback.message.edit_text(
            f"✅ Rahmat! Endi guruhda yoza olasiz!\n\n"
            f"Assalomu alaykum, {callback.from_user.full_name}! 👋\n"
            f"🌟 *Guruhimizga xush kelibsiz!*",
            parse_mode="Markdown"
        )
    else:
        await callback.answer("❌ Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)

# --- START ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "🤖 *Salom! Men guruh nazoratchisiman.*\n\n"
        "✅ Yangi a'zolarni qarshilayman\n"
        "✅ Majburiy a'zolikni tekshiraman\n"
        "✅ Reklamalarni o'chiraman\n"
        "✅ So'kinishlarni cheklayman\n\n"
        "👑 *Admin buyruqlari:*\n"
        "/statistika — guruh statistikasi\n"
        "/ban — foydalanuvchini ban qilish\n"
        "/unban — banni olib tashlash\n"
        "/mute — sukut qildirish\n"
        "/unmute — sukutni olib tashlash\n"
        "/kick — guruhdan chiqarish",
        parse_mode="Markdown"
    )

# --- STATISTIKA ---
@dp.message(Command("statistika"))
async def stat_handler(message: types.Message):
    if message.chat.type == "private":
        return await message.answer("Faqat guruhlarda ishlaydi.")
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
        f"💬 Jami xabarlar: {jami_xabarlar} ta\n"
        f"📢 Kanal: {KANAL}",
        parse_mode="Markdown"
    )

# --- BAN ---
@dp.message(Command("ban"))
async def ban_handler(message: types.Message):
    if not await admin_mi(message):
        return await message.answer("❌ Faqat adminlar uchun!")
    if not message.reply_to_message:
        return await message.answer("⚠️ Xabariga reply qiling")
    user = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, user.id)
        await message.answer(f"🚫 {user.full_name} ban qilindi!")
    except:
        await message.answer("❌ Ban qilib bo'lmadi.")

# --- UNBAN ---
@dp.message(Command("unban"))
async def unban_handler(message: types.Message):
    if not await admin_mi(message):
        return await message.answer("❌ Faqat adminlar uchun!")
    if not message.reply_to_message:
        return await message.answer("⚠️ Xabariga reply qiling")
    user = message.reply_to_message.from_user
    try:
        await bot.unban_chat_member(message.chat.id, user.id)
        await message.answer(f"✅ {user.full_name} bani olib tashlandi!")
    except:
        await message.answer("❌ Unban qilib bo'lmadi.")

# --- MUTE ---
@dp.message(Command("mute"))
async def mute_handler(message: types.Message):
    if not await admin_mi(message):
        return await message.answer("❌ Faqat adminlar uchun!")
    if not message.reply_to_message:
        return await message.answer("⚠️ Xabariga reply qiling")
    user = message.reply_to_message.from_user
    try:
        await bot.restrict_chat_member(
            message.chat.id, user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await message.answer(f"🔇 {user.full_name} mute qilindi!")
    except:
        await message.answer("❌ Mute qilib bo'lmadi.")

# --- UNMUTE ---
@dp.message(Command("unmute"))
async def unmute_handler(message: types.Message):
    if not await admin_mi(message):
        return await message.answer("❌ Faqat adminlar uchun!")
    if not message.reply_to_message:
        return await message.answer("⚠️ Xabariga reply qiling")
    user = message.reply_to_message.from_user
    try:
        await bot.restrict_chat_member(
            message.chat.id, user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True
            )
        )
        await message.answer(f"🔊 {user.full_name} mute olib tashlandi!")
    except:
        await message.answer("❌ Unmute qilib bo'lmadi.")

# --- KICK ---
@dp.message(Command("kick"))
async def kick_handler(message: types.Message):
    if not await admin_mi(message):
        return await message.answer("❌ Faqat adminlar uchun!")
    if not message.reply_to_message:
        return await message.answer("⚠️ Xabariga reply qiling")
    user = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, user.id)
        await bot.unban_chat_member(message.chat.id, user.id)
        await message.answer(f"👢 {user.full_name} guruhdan chiqarildi!")
    except:
        await message.answer("❌ Chiqarib bo'lmadi.")

# --- GURUH FILTRI ---
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

# --- ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    baza_yarat()
    # HTTP serverni alohida thread da ishga tushirish
    t = threading.Thread(target=http_server, daemon=True)
    t.start()
    print("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot to'xtatildi.")
