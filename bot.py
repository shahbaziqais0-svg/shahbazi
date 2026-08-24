import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
SYSTEM_INSTRUCTION = os.getenv("SYSTEM_INSTRUCTION", "You are a helpful AI assistant.")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/models")

def get_gemini_response(prompt: str) -> str:
    url = f"{GEMINI_BASE_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    data = {
        "contents": [{
            "parts": [{"text": f"{SYSTEM_INSTRUCTION}\n\nUser: {prompt}"}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "candidates" in result and len(result["candidates"]) > 0:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        return "پاسخی از مدل دریافت نشد."
    except Exception as e:
        return f"خطا در ارتباط با جمینای: {str(e)}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 سلام! من ربات متصل به جمینای هستم. پیامت رو برام بفرست.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🤖 من با مدل {GEMINI_MODEL} فعال هستم.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    ai_response = get_gemini_response(user_text)
    await update.message.reply_text(ai_response)

def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        raise ValueError("کلیدهای TELEGRAM_BOT_TOKEN و GEMINI_API_KEY را در Environment Variables تنظیم کنید.")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running on Render...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
