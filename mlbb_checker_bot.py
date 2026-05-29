import logging
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

logging.basicConfig(level=logging.INFO)


def check_mlbb(user_id: str, server_id: str):
    url = "https://yanjiestore.com/submitt.php"

    params = {
        "ID": user_id,
        "server": server_id,
    }

    try:
        res = requests.get(url, params=params, timeout=15)
        text = res.text.strip()

        if not text:
            return None

        return text

    except Exception as e:
        print("MLBB API Error:", e)
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🎮 MLBB Account Checker Bot

အသုံးပြုပုံ:

/check 123456789 1234

သို့မဟုတ်

123456789 1234

ID နဲ့ Server ID ပေးရုံနဲ့ MLBB account name / region စစ်ပေးပါမယ်။
"""
    await update.message.reply_text(text)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Format မှားနေပါတယ်\n\nExample:\n/check 123456789 1234"
        )
        return

    user_id = context.args[0]
    server_id = context.args[1]

    await process_checker(update, user_id, server_id)


async def text_checker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().replace(",", " ").split()

    if len(parts) < 2:
        await update.message.reply_text(
            "MLBB ID နဲ့ Server ID ပို့ပေးပါ\n\nExample:\n123456789 1234"
        )
        return

    user_id = parts[0]
    server_id = parts[1]

    await process_checker(update, user_id, server_id)


async def process_checker(update: Update, user_id: str, server_id: str):
    if not user_id.isdigit() or not server_id.isdigit():
        await update.message.reply_text("❌ ID နဲ့ Server ID က number ဖြစ်ရပါမယ်")
        return

    loading_msg = await update.message.reply_text("🔍 Checking MLBB account...")

    result = check_mlbb(user_id, server_id)

    if not result:
        await loading_msg.edit_text(
            "❌ Account မတွေ့ပါ\n\n"
            "ID / Server ID မှားနေခြင်း သို့မဟုတ် API ခဏ Error ဖြစ်နိုင်ပါတယ်။"
        )
        return

    reply = f"""
✅ MLBB Account Found

🆔 User ID: {user_id}
🌐 Server ID: {server_id}

📌 Result:
{result}

💎 Double Diamond:
⚠️ Public checker API နဲ့ recharge history မစစ်နိုင်ပါ။
"""

    await loading_msg.edit_text(reply)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_checker))

    print("MLBB Checker Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
