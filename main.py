import asyncio
import http.server
import logging
import os
import socketserver
import threading
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# توکن ربات تلگرام
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8862836655:AAHgueF9p3AmUdyN8BoGjEDLcMylVkHzXIw").strip()

ADMIN_USER_ID = 6757681583
TARGET_CHAT_ID = "@shahnawazplast"
SUPPORT_PHONE = "09193286922"
MARKET_CHECK_INTERVAL = 1800

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# وب‌سرور داخلی سبک Render
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            logging.info(f"وب‌سرور فعال است روی پورت {port}")
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"خطای وب‌سرور: {e}")

def ask_free_ai(prompt_text: str) -> str:
    """ارسال درخواست به موتور هوش مصنوعی آزاد بدون نیاز به ثبت یا خرید کلید API"""
    url = "https://text.pollinations.ai/"
    
    system_instruction = (
        "شما کارشناس ارشد و مشاور تخصصی بازار پلیمر، مواد اولیه پلاستیک، بورس کالا و صنعت پتروشیمی برای مجموعه شهنواز پلاست هستید.\n"
        "قوانین پاسخ‌دهی:\n"
        "۱. لحن کاملاً حرفه‌ای، محترمانه و به زبان فارسی روان.\n"
        "۲. تحلیل تخصصی گریدهای پلیمری (فیلم، بادی، تزریقی، 0209، F7000، 0075، BL3، 2420 و...).\n"
        "۳. درج مبالغ و تحلیل قیمت‌ها بر اساس «تومان بر هر کیلوگرم».\n"
        "۴. ارائه پیشنهاد شفاف عملیاتی (خرید پله‌ای / انتظار / تثبیت موجودی انبار).\n"
        "۵. در انتهای پیام ذکر شماره مشاوره: 09193286922"
    )

    full_payload = f"{system_instruction}\n\nپرسش کاربر:\n{prompt_text}"

    try:
        res = requests.post(
            url,
            data=full_payload.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
            timeout=35,
        )
        if res.status_code == 200 and res.text:
            return res.text.strip()
        return "⚠️ در حال حاضر پاسخی از سرور تحلیل بازار دریافت نشد."
    except Exception as err:
        return f"⚠️ خطای موقت ارتباط با سرور تحلیل: {str(err)}"

def get_main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 مظنه و قیمت روز گریدها", callback_data="btn_prices"),
            InlineKeyboardButton("💡 مشاوره خرید و انبارداری", callback_data="btn_advice"),
        ],
        [
            InlineKeyboardButton("📈 تحلیل تالار بورس کالا", callback_data="btn_bourse"),
            InlineKeyboardButton("📞 ارتباط با واحد فروش", callback_data="btn_contact"),
        ]
    ])

async def market_sentinel_loop(app):
    await asyncio.sleep(20)
    while True:
        prompt = """
        یک گزارش کوتاه و شیک (حداکثر ۱۰۰ کلمه) درباره وضعیت بازار پلیمر و پتروشیمی برای کانال بنویسید:
        
        📌 [عنوان جذاب]
        🔹 رویداد مهم بازار (وضعیت بورس کالا، ارز و رقابت‌ها)
        💰 تابلوی مظنه گریدهای پرمصرف (تومان بر کیلوگرم):
        ▫️ فیلم سنگین (F7000 / 020): ... تومان
        ▫️ فیلم سبک (0075 / 2420 / 0209): ... تومان
        ▫️ بادی (BL3): ... تومان
        ▫️ تزریقی / PP: ... تومان
        🎯 توصیه عملیاتی به تولیدکننده
        ⏳ مهلت اعتبار تحلیل
        
        اگر تحول خاصی رخ نداده فقط بنویسید NO_UPDATE
        """
        try:
            report = ask_free_ai(prompt)
            if "NO_UPDATE" not in report and "خطا" not in report and len(report) > 40:
                final_post = (
                    f"{report}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"☎️ مشاوره و سفارش: {SUPPORT_PHONE}\n"
                    f"📢 رسانه تخصصی: {TARGET_CHAT_ID}"
                )
                await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_post)
        except Exception as e:
            logging.error(f"خطا در ارسال کانال: {e}")

        await asyncio.sleep(MARKET_CHECK_INTERVAL)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **دستیار هوشمند بازار پلیمر شهنواز پلاست** ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "سلام! سامانه جامع تحلیل تخصصی مواد اولیه، بورس کالا و پیش‌بینی بازار آنلاین است.\n\n"
        "▫️ استعلام و تحلیل گریدهای پلیمری (فیلم، بادی، تزریقی)\n"
        "▫️ بررسی وضعیت عرضه‌ها و رقابت در بورس کالا\n"
        "▫️ مشاوره فنی و راهبرد مدیریت انبار مواد\n\n"
        "💬 *می‌توانید سوال خود را تایپ کرده یا از گزینه‌های زیر استفاده نمایید:*"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.MARKDOWN,
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "btn_prices":
        prompt = "یک گزارش شیک و مرتب از تابلوی مظنه گریدهای پرمصرف پلیمری (فیلم، بادی، تزریقی، 0209، F7000) به تومان بر کیلوگرم ارائه دهید."
    elif data == "btn_advice":
        prompt = "استراتژی و توصیه عملیاتی خرید مواد اولیه پلیمری در وضعیت فعلی بازار و نرخ ارز چیست؟"
    elif data == "btn_bourse":
        prompt = "تحلیل کوتاه و کاربردی از وضعیت رقابت‌ها و عرضه‌های تالار پتروشیمی بورس کالا ارائه دهید."
    elif data == "btn_contact":
        contact_info = (
            "📞 **واحد بازرگانی و مشاوره شهنواز پلاست**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 همراه / واتساپ: `{SUPPORT_PHONE}`\n"
            f"📢 کانال رسمی: {TARGET_CHAT_ID}\n\n"
            "▫️ جهت استعلام قطعی قیمت و ثبت پیش‌فاکتور تماس حاصل فرمایید."
        )
        await query.message.reply_text(contact_info, parse_mode=ParseMode.MARKDOWN)
        return

    status_msg = await query.message.reply_text("🔎 *در حال تحلیل هوشمند بازار...*", parse_mode=ParseMode.MARKDOWN)
    reply = ask_free_ai(prompt)
    try:
        await status_msg.edit_text(reply, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await status_msg.edit_text(reply)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    user_text = update.message.text

    if chat_type in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        return

    status_msg = await update.message.reply_text("🔎 *در حال استخراج و تحلیل داده‌ها...*", parse_mode=ParseMode.MARKDOWN)
    reply = ask_free_ai(user_text)
    
    try:
        await status_msg.edit_text(reply, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await status_msg.edit_text(reply)

async def post_init(application):
    asyncio.create_task(market_sentinel_loop(application))

if __name__ == "__main__":
    web_thread = threading.Thread(target=run_dummy_server, daemon=True)
    web_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("ربات تحلیل بازار شهنواز پلاست آنلاین شد.")
    app.run_polling(drop_pending_updates=True)
