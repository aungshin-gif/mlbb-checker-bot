import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "MLBB Checker Bot Ready\n\nUse:\n/check USER_ID SERVER_ID"
    )

def check_mlbb(user_id, server_id):
    try:
        url = f"https://yanjiestore.com/submitt.php?ID={user_id}&server={server_id}"

        r = requests.get(url, timeout=15)

        if r.status_code == 200:
            return r.text

        return None

    except Exception as e:
        print(e)
        return None

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) != 2:
        await update.message.reply_text(
            "Example:\n/check 123456789 1234"
        )
        return

    user_id = context.args[0]
    server_id = context.args[1]

    msg = await update.message.reply_text("Checking...")

    result = check_mlbb(user_id, server_id)

    if not result:
        await msg.edit_text("Account Not Found")
        return

    await msg.edit_text(
        f"✅ Result\n\nID: {user_id}\nServer: {server_id}\n\n{result}"
    )

def main():

    if not BOT_TOKEN:
        print("BOT_TOKEN NOT FOUND")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))

    print("BOT RUNNING...")

    app.run_polling()

if __name__ == "__main__":
    main()
