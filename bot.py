
import asyncio
import logging
import sqlite3
import re
import threading
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

TOKEN = "8972599548:AAFp4yMJcKTp1TvQljMwwBNtpNAofLrUf00"

# === RENDER URL ni o'zingiznikiga almashtiring ===
RENDER_URL = "https://YOUR_APP_NAME.onrender.com"

bot = Bot(token=TOKEN)
dp = Dispatcher()

SOKINISH_LUXATI = [
    "skat", "axmoq", "iflos", "jalab", "qotoq", "suka", "blat", "am", "kot",
    "gandon", "dalbayob", "onangni", "sharmanda", "hezzalak", "yaramas"
]

# --- HTTP SERVER ---
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

# --- KEEP-ALIVE: har 5 daqiqada o'ziga ping ---
def keep_alive():
    while True:
        try:
            urllib.request.urlopen(RENDER_URL, timeout=10)
            print("🏓 Keep-alive ping yuborildi")
        except Exception as e:
            print(f"⚠️ Keep-alive xato: {e}")
        threading.Event().wait(300)  # 5 daqiqa

# --- MA'LUMOTLAR BAZASI (thread-safe) ---
db_lock = threading.Lock()

def baza_yarat():
    with db_lock:
        conn = sqlite3.connect("bot_bazasi.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistika (
                chat_id INTEGER PRIMARY KEY,
                xabarlar_soni INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kanallar (
                chat_id INTEGER,
                kanal TEXT,
                PRIMARY KEY (chat_id, kanal)
            )
        """)
        conn.commit()
        conn.close()

def xabarni_sana(chat_id):
    with db_lock:
        conn = sqlite3.connect("bot_bazasi.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO statistika (chat_id) VALUES (?)", (chat_id,))
        cursor.execute("UPDATE statistika SET xabarlar_soni = xabarlar_soni + 1 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()

def kanallarni_ol(chat_id):
    with db_lock:
        conn = sqlite3.connect("bot_bazasi.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT kanal FROM kanallar WHERE chat_id = ?", (chat_id,))
        natija = [row[0] for row in cursor.fetchall()]
        conn.close()
        return natija

def kanal_qosh(chat_id, kanal):
    with db_lock:
        conn = sqlite3.connect("bot_bazasi.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO kanallar (chat_id, kanal) VALUES (?, ?)", (chat_id, kanal))
        conn.commit()
        conn.close()

def kanal_ochir(chat_id, kanal):
    with db_lock:
        conn = sqlite3.connect("bot_bazasi.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kanallar WHERE chat_id = ? AND kanal = ?", (chat_id, kanal))
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
async def azomi(user_id: int, kanallar: list) -> bool:
    for kanal in kanallar:
        try:
            member = await bot.get_chat_member(kanal, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# --- MAJBURIY A'ZOLIK TUGMASI ---
def azolik_tugmasi(kanallar: list):
    buttons = []
    for kanal in kanallar:
        username = kanal.replace("@", "")
        buttons.append([InlineKeyboardButton(text=f"📢 {kanal}", url=f"https://t.me/{username}")])
    buttons.append([InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="tekshir")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- /guruh buyrug'i ---
@dp.message(Command("guruh"))
async def guruh_handler(message: types.Message):
    if not await admin_mi(message):
        return await message.answer("❌ Faqat adminlar uchun!")
    
    args = message.text.split()
    if len(args) < 2:
        kanallar = kanallarni_ol(message.chat.id)
        if kanallar:
            kanal_list = "\n".join(kanallar)
            await message.answer(
                f"📢 *Majburiy a'zolik kanallari:*\n{kanal_list}\n\n"
                f"➕ Qo'shish: `/guruh @kanalnom`\n"
                f"➖ O'chirish: `/guruhochir @kanalnom`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "📢 Hozircha kanal yo'q.\n\n"
                "Qo'shish uchun: `/guruh @kanalnom`",
                parse_mode="Markdown"
            )
        return

    kanal = args[1]
    if not kanal.startswith("@"):
        return await message.answer("⚠️ Kanal @ bilan boshlanishi kerak!\nMasalan: `/guruh @kanalnom`", parse_mode="Markdown")

    kanal_qosh(message.chat.id, kanal)
    await message.answer(f"✅ *{kanal}* majburiy a'zolik kanaliga qo'shildi!", parse_mode="Markdown")

# --- /guruhochir buyrug'i ---
@dp.message(Command("guruhochir"))
async def guruhochir_handler(message: types.Message):
    if not await admin_mi(message):
        return await message.answer("❌ Faqat adminlar uchun!")
    
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("⚠️ Kanal nomini kiriting!\nMasalan: `/guruhochir @kanalnom`", parse_mode="Markdown")

    kanal = args[1]
    kanal_ochir(message.chat.id, kanal)
    await message.answer(f"🗑️ *{kanal}* ro'yxatdan o'chirildi!", parse_mode="Markdown")

# --- YANGI A'ZO ---
@dp.message(F.new_chat_members)
async def welcome_handler(message: types.Message):
    for user in message.new_chat_members:
        if user.is_bot:
            continue
        kanallar = kanallarni_ol(message.chat.id)
        if kanallar and not await azomi(user.id, kanallar):
            try:
                await bot.restrict_chat_member(
                    message.chat.id, user.id,
                    permissions=ChatPermissions(can_send_messages=False)
                )
            except:
                pass
            await message.answer(
                f"Salom {user.full_name}! 👋\n\n"
                f"Guruhda yozish uchun avval quyidagi kanallarga a'zo bo'ling:",
                reply_markup=azolik_tugmasi(kanallar)
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
    kanallar = kanallarni_ol(callback.message.chat.id)
    if await azomi(callback.from_user.id, kanallar):
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
        await callback.answer("❌ Barcha kanallarga a'zo bo'ling!", show_alert=True)

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
        "/guruh @kanal — majburiy kanal qo'shish\n"
        "/guruhochir @kanal — kanalni o'chirish\n"
        "/guruh — kanallar ro'yxati\n"
        "/statistika — guruh statistikasi\n"
        "/ban — ban qilish\n"
        "/unban — banni olish\n"
        "/mute — sukut qildirish\n"
        "/unmute — sukutni olish\n"
        "/kick — guruhdan chiqarish",
        parse_mode="Markdown"
    )

# --- STATISTIKA ---
@dp.message(Command("statistika"))
async def stat_handler(message: types.Message):
    if message.chat.type == "private":
        return await message.answer("Faqat guruhlarda ishlaydi.")
    with db_lock:
        conn = sqlite3.connect("bot_bazasi.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT xabarlar_soni FROM statistika WHERE chat_id = ?", (message.chat.id,))
        natija = cursor.fetchone()
        conn.close()
    jami_xabarlar = natija[0] if natija else 0
    jami_azolar = await bot.get_chat_member_count(message.chat.id)
    kanallar = kanallarni_ol(message.chat.id)
    kanal_text = "\n".join(kanallar) if kanallar else "Yo'q"
    await message.answer(
        f"📊 *Guruh statistikasi:*\n\n"
        f"👥 A'zolar: {jami_azolar} ta\n"
        f"💬 Jami xabarlar: {jami_xabarlar} ta\n"
        f"📢 Kanallar:\n{kanal_text}",
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
    reklama_belgilari = [r"http", r"t\.me", r"\.uz", r"\.com", r"\.ru", r"www\."]
    if any(re.search(p, xabar_matni) for p in reklama_belgilari):
        try:
            await message.delete()
            await message.answer(f"🚫 {message.from_user.first_name}, reklama taqiqlangan!")
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

# --- ISHGA TUSHIRISH (avtomatik qayta ulanish bilan) ---
async def main():
    logging.basicConfig(level=logging.INFO)
    baza_yarat()

    # HTTP server
    t = threading.Thread(target=http_server, daemon=True)
    t.start()

    # Keep-alive ping
    k = threading.Thread(target=keep_alive, daemon=True)
    k.start()

    print("✅ Bot ishga tushdi!")

    # Avtomatik qayta ulanish
    while True:
        try:
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                polling_timeout=30
            )
        except Exception as e:
            print(f"⚠️ Polling xato: {e}. 5 soniyadan keyin qayta ulanadi...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot to'xtatildi.")
