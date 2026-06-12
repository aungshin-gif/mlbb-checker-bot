
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

import database as db
import config as cfg

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id in cfg.ADMIN_IDS


def fmt_mmk(amount: int) -> str:
    return f"{amount:,} MMK"


def user_mention(user) -> str:
    name = user.get("full_name") or user.get("username") or str(user.get("user_id"))
    uid = user.get("user_id")
    return f'<a href="tg://user?id={uid}">{name}</a>'


async def notify_admins(app, text: str, **kwargs):
    for admin_id in cfg.ADMIN_IDS:
        try:
            await app.bot.send_message(chat_id=admin_id, text=text, **kwargs)
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")


# ═══════════════════════════════════════════════════════════════════
# /start  /help
# ═══════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.full_name)
    u = db.get_user(user.id)
    if u["is_banned"]:
        await update.message.reply_text("❌ သင့် Account ကို Ban လုပ်ထားသည်။")
        return cfg.STATE_NONE

    welcome = db.get_setting("welcome_message")
    keyboard = [
        [InlineKeyboardButton("🛒 Shop", callback_data="menu_shop"),
         InlineKeyboardButton("💰 Balance", callback_data="menu_balance")],
        [InlineKeyboardButton("💳 Top Up", callback_data="menu_topup"),
         InlineKeyboardButton("📦 My Orders", callback_data="menu_orders")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="menu_help")],
    ]
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])

    await update.message.reply_text(
        f"👋 မင်္ဂလာပါ <b>{user.first_name}</b>!\n\n{welcome}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    return cfg.STATE_NONE


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>Commands များ</b>\n\n"
        "/start - Main Menu\n"
        "/shop - ကုန်ပစ္စည်းများကြည့်ရန်\n"
        "/balance - လက်ကျန်ငွေကြည့်ရန်\n"
        "/topup - ငွေဖြည့်ရန်\n"
        "/orders - မှာယူမှတ်တမ်းကြည့်ရန်\n"
        "/help - Help\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════════════
# BALANCE
# ═══════════════════════════════════════════════════════════════════

async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.full_name)
    u = db.get_user(user.id)
    keyboard = [[InlineKeyboardButton("💳 ငွေဖြည့်မည်", callback_data="menu_topup")]]
    await update.message.reply_text(
        f"💰 <b>လက်ကျန်ငွေ</b>\n\n"
        f"👤 {user.first_name}\n"
        f"💵 Balance: <b>{fmt_mmk(u['balance'])}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════
# SHOP - Browse Products
# ═══════════════════════════════════════════════════════════════════

async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.full_name)
    u = db.get_user(user.id)
    if u["is_banned"]:
        await update.message.reply_text("❌ သင့် Account ကို Ban လုပ်ထားသည်။")
        return

    categories = db.get_categories()
    if not categories:
        await update.message.reply_text("📭 ယခုအချိန် Category မရှိသေးပါ။")
        return

    keyboard = []
    for cat in categories:
        products = db.get_products(category_id=cat["id"])
        if products:
            keyboard.append([InlineKeyboardButton(
                f"📁 {cat['name']}", callback_data=f"cat_{cat['id']}"
            )])

    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    await update.message.reply_text(
        "🛒 <b>Digital Shop</b>\n\nCategory တခုရွေးပါ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════
# CALLBACK QUERY ROUTER
# ═══════════════════════════════════════════════════════════════════

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    db.get_or_create_user(user.id, user.username, user.full_name)

    # ── Main Menu ──────────────────────────────────────────────────
    if data == "main_menu":
        await show_main_menu(query, user)

    elif data == "menu_shop":
        await show_shop_categories(query)

    elif data == "menu_balance":
        u = db.get_user(user.id)
        keyboard = [
            [InlineKeyboardButton("💳 ငွေဖြည့်မည်", callback_data="menu_topup")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"💰 <b>လက်ကျန်ငွေ</b>\n\n"
            f"👤 {user.first_name}\n"
            f"💵 Balance: <b>{fmt_mmk(u['balance'])}</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

    elif data == "menu_topup":
        await show_topup_menu(query, context)

    elif data == "menu_orders":
        await show_orders(query, user)

    elif data == "menu_help":
        text = (
            "📖 <b>Commands များ</b>\n\n"
            "/start - Main Menu\n"
            "/shop - ကုန်ပစ္စည်းများကြည့်ရန်\n"
            "/balance - လက်ကျန်ငွေကြည့်ရန်\n"
            "/topup - ငွေဖြည့်ရန်\n"
            "/orders - မှာယူမှတ်တမ်းကြည့်ရန်\n"
        )
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.HTML)

    # ── Shop / Categories ──────────────────────────────────────────
    elif data.startswith("cat_"):
        cat_id = int(data.split("_")[1])
        await show_products_in_category(query, cat_id)

    elif data.startswith("prod_"):
        prod_id = int(data.split("_")[1])
        await show_product_detail(query, prod_id)

    elif data.startswith("buy_"):
        prod_id = int(data.split("_")[1])
        await process_purchase(query, user, prod_id, context)

    elif data == "back_to_categories":
        await show_shop_categories(query)

    # ── Top-Up ────────────────────────────────────────────────────
    elif data == "topup_wave":
        context.user_data["topup_method"] = "Wave"
        await show_topup_amount_prompt(query, context, "Wave")

    elif data == "topup_kbz":
        context.user_data["topup_method"] = "KBZPay"
        await show_topup_amount_prompt(query, context, "KBZPay")

    # ── Admin Panel ───────────────────────────────────────────────
    elif data == "admin_panel":
        if not is_admin(user.id):
            await query.answer("❌ Admin သာ ဝင်ခွင့်ရှိသည်!", show_alert=True)
            return
        await show_admin_panel(query)

    elif data == "admin_pending_topups":
        if not is_admin(user.id):
            return
        await show_pending_topups(query)

    elif data.startswith("admin_approve_"):
        if not is_admin(user.id):
            return
        req_id = int(data.split("_")[2])
        await handle_approve_topup(query, user, req_id, context)

    elif data.startswith("admin_reject_"):
        if not is_admin(user.id):
            return
        req_id = int(data.split("_")[2])
        await handle_reject_topup(query, user, req_id, context)

    elif data == "admin_products":
        if not is_admin(user.id):
            return
        await show_admin_products(query)

    elif data == "admin_add_product":
        if not is_admin(user.id):
            return
        context.user_data.clear()
        context.user_data["action"] = "add_product"
        await query.edit_message_text(
            "📦 <b>Product အသစ်ထည့်မည်</b>\n\nProduct Name ရိုက်ထည့်ပါ:",
            parse_mode=ParseMode.HTML
        )
        return cfg.STATE_ADD_PRODUCT_NAME

    elif data == "admin_add_category":
        if not is_admin(user.id):
            return
        await query.edit_message_text(
            "📁 <b>Category အသစ်ထည့်မည်</b>\n\nCategory Name ရိုက်ထည့်ပါ:",
            parse_mode=ParseMode.HTML
        )
        return cfg.STATE_ADD_CATEGORY_NAME

    elif data == "admin_stocks":
        if not is_admin(user.id):
            return
        await show_admin_stocks_menu(query)

    elif data.startswith("admin_view_stocks_"):
        if not is_admin(user.id):
            return
        prod_id = int(data.split("_")[3])
        await show_stocks_for_product(query, prod_id)

    elif data.startswith("admin_add_stocks_"):
        if not is_admin(user.id):
            return
        prod_id = int(data.split("_")[3])
        context.user_data["stock_product_id"] = prod_id
        prod = db.get_product(prod_id)
        await query.edit_message_text(
            f"📥 <b>{prod['name']}</b> - Stock ထည့်မည်\n\n"
            "Stock တခုချင်း သို့မဟုတ် တစ်ကြောင်းချင်း ရိုက်ထည့်ပါ:\n"
            "(တစ်ကြောင်းချင်းထည့်ပါ - Enter နှိပ်ပြီး ဆက်ထည့်နိုင်သည်)\n\n"
            "ပြီးသောအခါ /done ရိုက်ပါ",
            parse_mode=ParseMode.HTML
        )
        context.user_data["stock_items"] = []
        return cfg.STATE_ADD_STOCK_CONTENT

    elif data == "admin_settings":
        if not is_admin(user.id):
            return
        await show_admin_settings(query)

    elif data.startswith("admin_setting_edit_"):
        if not is_admin(user.id):
            return
        key = data.replace("admin_setting_edit_", "")
        context.user_data["edit_setting_key"] = key
        current = db.get_setting(key)
        await query.edit_message_text(
            f"⚙️ <b>Setting: {key}</b>\n\n"
            f"Current Value:\n<code>{current}</code>\n\n"
            "New Value ရိုက်ထည့်ပါ:",
            parse_mode=ParseMode.HTML
        )
        return cfg.STATE_EDIT_SETTING_VALUE

    elif data == "admin_users":
        if not is_admin(user.id):
            return
        await show_admin_users(query)

    elif data == "admin_broadcast":
        if not is_admin(user.id):
            return
        await query.edit_message_text(
            "📢 <b>Broadcast Message</b>\n\nUser အားလုံးထံ ပို့မည့် Message ရိုက်ထည့်ပါ:",
            parse_mode=ParseMode.HTML
        )
        return cfg.STATE_BROADCAST

    elif data.startswith("admin_toggle_product_"):
        if not is_admin(user.id):
            return
        prod_id = int(data.split("_")[3])
        db.toggle_product(prod_id)
        await show_admin_products(query)

    elif data.startswith("admin_delete_product_"):
        if not is_admin(user.id):
            return
        prod_id = int(data.split("_")[3])
        db.delete_product(prod_id)
        await query.answer("✅ Product ဖျက်ပြီးပါပြီ", show_alert=True)
        await show_admin_products(query)

    elif data.startswith("admin_delete_category_"):
        if not is_admin(user.id):
            return
        cat_id = int(data.split("_")[3])
        db.delete_category(cat_id)
        await query.answer("✅ Category ဖျက်ပြီးပါပြီ", show_alert=True)
        await show_admin_panel(query)

    elif data == "admin_orders":
        if not is_admin(user.id):
            return
        await show_admin_orders(query)

    elif data.startswith("admin_ban_"):
        if not is_admin(user.id):
            return
        uid = int(data.split("_")[2])
        db.ban_user(uid, True)
        await query.answer(f"✅ User {uid} ကို Ban လုပ်ပြီးပါပြီ", show_alert=True)
        await show_admin_users(query)

    elif data.startswith("admin_unban_"):
        if not is_admin(user.id):
            return
        uid = int(data.split("_")[2])
        db.ban_user(uid, False)
        await query.answer(f"✅ User {uid} ကို Unban လုပ်ပြီးပါပြီ", show_alert=True)
        await show_admin_users(query)

    elif data == "admin_categories":
        if not is_admin(user.id):
            return
        await show_admin_categories(query)


# ═══════════════════════════════════════════════════════════════════
# SHOP DISPLAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def show_main_menu(query, user):
    welcome = db.get_setting("welcome_message")
    keyboard = [
        [InlineKeyboardButton("🛒 Shop", callback_data="menu_shop"),
         InlineKeyboardButton("💰 Balance", callback_data="menu_balance")],
        [InlineKeyboardButton("💳 Top Up", callback_data="menu_topup"),
         InlineKeyboardButton("📦 My Orders", callback_data="menu_orders")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="menu_help")],
    ]
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    await query.edit_message_text(
        f"👋 မင်္ဂလာပါ <b>{user.first_name}</b>!\n\n{welcome}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_shop_categories(query):
    categories = db.get_categories()
    if not categories:
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(
            "📭 ယခုအချိန် Category မရှိသေးပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    keyboard = []
    for cat in categories:
        products = db.get_products(category_id=cat["id"])
        if products:
            keyboard.append([InlineKeyboardButton(
                f"📁 {cat['name']}", callback_data=f"cat_{cat['id']}"
            )])

    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    await query.edit_message_text(
        "🛒 <b>Digital Shop</b>\n\nCategory တခုရွေးပါ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_products_in_category(query, cat_id: int):
    products = db.get_products(category_id=cat_id)
    if not products:
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back_to_categories")]]
        await query.edit_message_text(
            "📭 ဤ Category တွင် Product မရှိသေးပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    keyboard = []
    for prod in products:
        stock_info = f"({prod['stock_count']} ခုရှိ)" if prod['stock_count'] > 0 else "(Stock မရှိ)"
        keyboard.append([InlineKeyboardButton(
            f"{'✅' if prod['stock_count'] > 0 else '❌'} {prod['name']} - {fmt_mmk(prod['price'])} {stock_info}",
            callback_data=f"prod_{prod['id']}"
        )])

    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="back_to_categories")])
    cat_name = products[0]["category_name"] if products else "Category"
    await query.edit_message_text(
        f"📁 <b>{cat_name}</b>\n\nProduct တခုရွေးပါ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_product_detail(query, prod_id: int):
    prod = db.get_product(prod_id)
    if not prod:
        await query.answer("Product မတွေ့ပါ!", show_alert=True)
        return

    stock_count = prod["stock_count"]
    type_icon = "🔒 Private" if prod["product_type"] == "private" else "🔗 Shared"
    duration_text = f"⏱ Duration: {prod['duration']}" if prod['duration'] else ""
    desc_text = f"\n📝 {prod['description']}" if prod['description'] else ""

    text = (
        f"📦 <b>{prod['name']}</b>\n"
        f"📁 Category: {prod['category_name']}\n"
        f"💰 Price: <b>{fmt_mmk(prod['price'])}</b>\n"
        f"🏷 Type: {type_icon}\n"
        f"{duration_text}\n"
        f"📊 Stock: {'✅ ' + str(stock_count) + ' ခုရှိ' if stock_count > 0 else '❌ Stock မရှိ'}"
        f"{desc_text}"
    )

    keyboard = []
    if stock_count > 0:
        keyboard.append([InlineKeyboardButton(
            f"🛒 ဝယ်မည် ({fmt_mmk(prod['price'])})",
            callback_data=f"buy_{prod_id}"
        )])
    keyboard.append([InlineKeyboardButton(
        f"◀️ Back", callback_data=f"cat_{prod['category_id']}"
    )])

    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
    )


async def process_purchase(query, user, prod_id: int, context):
    u = db.get_user(user.id)
    if u["is_banned"]:
        await query.answer("❌ သင့် Account ကို Ban လုပ်ထားသည်!", show_alert=True)
        return

    prod = db.get_product(prod_id)
    if not prod:
        await query.answer("Product မတွေ့ပါ!", show_alert=True)
        return

    stock = db.get_available_stock(prod_id)
    if not stock:
        await query.answer("❌ Stock မရှိတော့ပါ! ငွေမဖြတ်ပါ။", show_alert=True)
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data=f"prod_{prod_id}")]]
        await query.edit_message_text(
            f"❌ <b>{prod['name']}</b>\n\nStock ကုန်သွားပါပြီ! ငွေမဖြတ်ပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return

    if u["balance"] < prod["price"]:
        shortage = prod["price"] - u["balance"]
        keyboard = [
            [InlineKeyboardButton("💳 ငွေဖြည့်မည်", callback_data="menu_topup")],
            [InlineKeyboardButton("◀️ Back", callback_data=f"prod_{prod_id}")]
        ]
        await query.edit_message_text(
            f"❌ <b>Balance မလုံလောက်ပါ!</b>\n\n"
            f"💰 လိုအပ်သော: {fmt_mmk(prod['price'])}\n"
            f"💵 လက်ကျန်: {fmt_mmk(u['balance'])}\n"
            f"⚠️ ထပ်ဖြည့်ရန်: {fmt_mmk(shortage)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return

    # Deduct balance and mark stock sold
    db.update_balance(user.id, -prod["price"])
    db.mark_stock_sold(stock["id"], user.id)
    db.create_order(user.id, prod_id, stock["id"], prod["price"])

    new_balance = u["balance"] - prod["price"]
    keyboard = [
        [InlineKeyboardButton("🛒 ဆက်ဝယ်မည်", callback_data="menu_shop")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]

    await query.edit_message_text(
        f"✅ <b>ဝယ်ယူမှု အောင်မြင်ပါသည်!</b>\n\n"
        f"📦 Product: <b>{prod['name']}</b>\n"
        f"💰 ဖြတ်သွားသော: {fmt_mmk(prod['price'])}\n"
        f"💵 လက်ကျန်: {fmt_mmk(new_balance)}\n\n"
        f"🔑 <b>သင်ဝယ်ယူသော Item:</b>\n"
        f"<code>{stock['content']}</code>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    # Notify admins
    await notify_admins(
        context.application,
        f"🛒 <b>New Purchase!</b>\n\n"
        f"👤 User: {user.first_name} (@{user.username or 'N/A'}) [ID: {user.id}]\n"
        f"📦 Product: {prod['name']}\n"
        f"💰 Amount: {fmt_mmk(prod['price'])}",
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════
# TOP-UP FLOW
# ═══════════════════════════════════════════════════════════════════

async def show_topup_menu(query, context):
    wave_num = db.get_setting("wave_number")
    kbz_num = db.get_setting("kbz_number")
    pay_name = db.get_setting("payment_name")

    keyboard = [
        [InlineKeyboardButton("📱 Wave Pay", callback_data="topup_wave")],
        [InlineKeyboardButton("🏦 KBZ Pay", callback_data="topup_kbz")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    await query.edit_message_text(
        f"💳 <b>ငွေဖြည့်မည်</b>\n\n"
        f"Payment Method ရွေးပါ:\n\n"
        f"📱 Wave Pay: <code>{wave_num}</code>\n"
        f"🏦 KBZ Pay: <code>{kbz_num}</code>\n"
        f"👤 Name: <b>{pay_name}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_topup_amount_prompt(query, context, method: str):
    wave_num = db.get_setting("wave_number")
    kbz_num = db.get_setting("kbz_number")
    pay_name = db.get_setting("payment_name")
    num = wave_num if method == "Wave" else kbz_num
    icon = "📱" if method == "Wave" else "🏦"

    await query.edit_message_text(
        f"{icon} <b>{method} Pay ဖြင့် ငွေဖြည့်မည်</b>\n\n"
        f"📞 Phone: <code>{num}</code>\n"
        f"👤 Name: <b>{pay_name}</b>\n\n"
        f"1️⃣ အထက်ပါ Number သို့ ငွေလွှဲပါ\n"
        f"2️⃣ ဖြည့်မည့် ငွေပမာဏ ရိုက်ထည့်ပါ (MMK):\n\n"
        f"<i>Example: 5000</i>",
        parse_mode=ParseMode.HTML
    )
    return cfg.STATE_TOPUP_AMOUNT


async def handle_topup_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ မှန်ကန်သော ငွေပမာဏ ရိုက်ထည့်ပါ (ဂဏန်းသာ):")
        return cfg.STATE_TOPUP_AMOUNT

    amount = int(text)
    if amount < 500:
        await update.message.reply_text("❌ အနည်းဆုံး 500 MMK ဖြည့်ရပါမည်:")
        return cfg.STATE_TOPUP_AMOUNT

    context.user_data["topup_amount"] = amount
    method = context.user_data.get("topup_method", "Wave")
    wave_num = db.get_setting("wave_number")
    kbz_num = db.get_setting("kbz_number")
    pay_name = db.get_setting("payment_name")
    num = wave_num if method == "Wave" else kbz_num

    await update.message.reply_text(
        f"✅ ငွေပမာဏ: <b>{fmt_mmk(amount)}</b>\n\n"
        f"📸 ငွေလွှဲပြီးကြောင်း Screenshot ပုံ ပို့ပါ:\n\n"
        f"📞 {method}: <code>{num}</code>\n"
        f"👤 Name: <b>{pay_name}</b>",
        parse_mode=ParseMode.HTML
    )
    return cfg.STATE_TOPUP_SCREENSHOT


async def handle_topup_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get("topup_amount", 0)
    method = context.user_data.get("topup_method", "Wave")

    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("❌ ပုံ သို့မဟုတ် File တင်ပါ:")
        return cfg.STATE_TOPUP_SCREENSHOT

    req_id = db.create_topup_request(user.id, amount, method, file_id)

    await update.message.reply_text(
        f"✅ <b>Top-Up Request တင်ပြီးပါပြီ!</b>\n\n"
        f"🆔 Request ID: #{req_id}\n"
        f"💰 Amount: {fmt_mmk(amount)}\n"
        f"💳 Method: {method}\n\n"
        f"⏳ Admin မှ စစ်ဆေးပြီး Approve လုပ်ပေးပါမည်။",
        parse_mode=ParseMode.HTML
    )

    # Notify admins with screenshot
    u = db.get_user(user.id)
    caption = (
        f"💳 <b>New Top-Up Request #{req_id}</b>\n\n"
        f"👤 User: {user.first_name} (@{user.username or 'N/A'})\n"
        f"🆔 User ID: {user.id}\n"
        f"💰 Amount: {fmt_mmk(amount)}\n"
        f"💳 Method: {method}\n"
        f"💵 Current Balance: {fmt_mmk(u['balance'])}"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ Approve", callback_data=f"admin_approve_{req_id}"),
            InlineKeyboardButton(f"❌ Reject", callback_data=f"admin_reject_{req_id}")
        ]
    ])

    for admin_id in cfg.ADMIN_IDS:
        try:
            if file_id:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=file_id,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=caption,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")

    context.user_data.clear()
    return cfg.STATE_NONE


# ═══════════════════════════════════════════════════════════════════
# ORDERS
# ═══════════════════════════════════════════════════════════════════

async def show_orders(query, user):
    orders = db.get_user_orders(user.id, limit=10)
    if not orders:
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(
            "📦 မှာယူမှတ်တမ်း မရှိသေးပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    text = "📦 <b>မှာယူမှတ်တမ်း (နောက်ဆုံး 10 ခု)</b>\n\n"
    for i, order in enumerate(orders, 1):
        text += (
            f"{i}. <b>{order['product_name']}</b>\n"
            f"   💰 {fmt_mmk(order['amount_paid'])}"
            f"{' | ⏱ ' + order['duration'] if order['duration'] else ''}\n"
            f"   🔑 <code>{order['content']}</code>\n"
            f"   📅 {order['created_at']}\n\n"
        )

    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
    )


async def cmd_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.full_name)
    orders = db.get_user_orders(user.id, limit=10)
    if not orders:
        await update.message.reply_text("📦 မှာယူမှတ်တမ်း မရှိသေးပါ။")
        return

    text = "📦 <b>မှာယူမှတ်တမ်း (နောက်ဆုံး 10 ခု)</b>\n\n"
    for i, order in enumerate(orders, 1):
        text += (
            f"{i}. <b>{order['product_name']}</b>\n"
            f"   💰 {fmt_mmk(order['amount_paid'])}"
            f"{' | ⏱ ' + order['duration'] if order['duration'] else ''}\n"
            f"   🔑 <code>{order['content']}</code>\n"
            f"   📅 {order['created_at']}\n\n"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════════════
# ADMIN PANEL FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def show_admin_panel(query):
    pending = db.get_pending_topups()
    users = db.get_all_users()
    keyboard = [
        [InlineKeyboardButton(
            f"💳 Pending Top-Ups ({len(pending)})",
            callback_data="admin_pending_topups"
        )],
        [InlineKeyboardButton("📦 Products", callback_data="admin_products"),
         InlineKeyboardButton("📁 Categories", callback_data="admin_categories")],
        [InlineKeyboardButton("📥 Stocks", callback_data="admin_stocks"),
         InlineKeyboardButton("📊 Orders", callback_data="admin_orders")],
        [InlineKeyboardButton(f"👥 Users ({len(users)})", callback_data="admin_users")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]
    await query.edit_message_text(
        "⚙️ <b>Admin Panel</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_pending_topups(query):
    pending = db.get_pending_topups()
    if not pending:
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="admin_panel")]]
        await query.edit_message_text(
            "✅ Pending Top-Up မရှိပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    keyboard = []
    for req in pending:
        name = req["full_name"] or req["username"] or str(req["user_id"])
        keyboard.append([InlineKeyboardButton(
            f"#{req['id']} | {name} | {fmt_mmk(req['amount'])} | {req['payment_method']}",
            callback_data=f"admin_approve_{req['id']}"
        )])
        keyboard.append([
            InlineKeyboardButton(f"✅ Approve #{req['id']}", callback_data=f"admin_approve_{req['id']}"),
            InlineKeyboardButton(f"❌ Reject #{req['id']}", callback_data=f"admin_reject_{req['id']}")
        ])

    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="admin_panel")])
    await query.edit_message_text(
        f"💳 <b>Pending Top-Ups ({len(pending)})</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def handle_approve_topup(query, admin_user, req_id: int, context):
    req = db.approve_topup(req_id, admin_user.id)
    if not req:
        await query.answer("Request မတွေ့ပါ သို့မဟုတ် ပြီးသားဖြစ်နေသည်!", show_alert=True)
        return

    await query.answer(f"✅ #{req_id} Approved!", show_alert=True)

    # Notify user
    try:
        await context.bot.send_message(
            chat_id=req["user_id"],
            text=(
                f"✅ <b>Top-Up Approved!</b>\n\n"
                f"💰 Amount: <b>{fmt_mmk(req['amount'])}</b>\n"
                f"💳 Method: {req['payment_method']}\n\n"
                f"💵 Balance ထဲသို့ ထည့်ပြီးပါပြီ!"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.warning(f"Could not notify user {req['user_id']}: {e}")

    await show_pending_topups(query)


async def handle_reject_topup(query, admin_user, req_id: int, context):
    req = db.reject_topup(req_id, admin_user.id)
    if not req:
        await query.answer("Request မတွေ့ပါ သို့မဟုတ် ပြီးသားဖြစ်နေသည်!", show_alert=True)
        return

    await query.answer(f"❌ #{req_id} Rejected!", show_alert=True)

    # Notify user
    try:
        await context.bot.send_message(
            chat_id=req["user_id"],
            text=(
                f"❌ <b>Top-Up Rejected!</b>\n\n"
                f"💰 Amount: {fmt_mmk(req['amount'])}\n"
                f"💳 Method: {req['payment_method']}\n\n"
                f"⚠️ ပြဿနာရှိပါက Admin ကို ဆက်သွယ်ပါ။"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.warning(f"Could not notify user {req['user_id']}: {e}")

    await show_pending_topups(query)


async def show_admin_products(query):
    products = db.get_products(active_only=False)
    if not products:
        keyboard = [
            [InlineKeyboardButton("➕ Product ထည့်မည်", callback_data="admin_add_product")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_panel")]
        ]
        await query.edit_message_text(
            "📦 Product မရှိသေးပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    keyboard = []
    for prod in products:
        status = "✅" if prod["is_active"] else "❌"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {prod['name']} | {fmt_mmk(prod['price'])} | Stock: {prod['stock_count']}",
                callback_data=f"admin_toggle_product_{prod['id']}"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(f"📥 Stock ထည့်", callback_data=f"admin_add_stocks_{prod['id']}"),
            InlineKeyboardButton(f"👁 Stock ကြည့်", callback_data=f"admin_view_stocks_{prod['id']}"),
            InlineKeyboardButton(f"🗑 ဖျက်", callback_data=f"admin_delete_product_{prod['id']}")
        ])

    keyboard.append([InlineKeyboardButton("➕ Product ထည့်မည်", callback_data="admin_add_product")])
    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="admin_panel")])
    await query.edit_message_text(
        f"📦 <b>Products ({len(products)})</b>\n<i>(ဖိနှိပ်ပြီး Enable/Disable လုပ်နိုင်)</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_admin_categories(query):
    categories = db.get_categories()
    keyboard = []
    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(f"📁 {cat['name']}", callback_data=f"cat_{cat['id']}"),
            InlineKeyboardButton(f"🗑 ဖျက်", callback_data=f"admin_delete_category_{cat['id']}")
        ])
    keyboard.append([InlineKeyboardButton("➕ Category ထည့်မည်", callback_data="admin_add_category")])
    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="admin_panel")])
    await query.edit_message_text(
        f"📁 <b>Categories ({len(categories)})</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_admin_stocks_menu(query):
    products = db.get_products(active_only=False)
    if not products:
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="admin_panel")]]
        await query.edit_message_text("📦 Product မရှိသေးပါ။",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = []
    for prod in products:
        keyboard.append([InlineKeyboardButton(
            f"📦 {prod['name']} (Stock: {prod['stock_count']})",
            callback_data=f"admin_view_stocks_{prod['id']}"
        )])
        keyboard.append([
            InlineKeyboardButton(f"➕ Stock ထည့်", callback_data=f"admin_add_stocks_{prod['id']}")
        ])

    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="admin_panel")])
    await query.edit_message_text(
        "📥 <b>Stock Management</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_stocks_for_product(query, prod_id: int):
    prod = db.get_product(prod_id)
    stocks = db.get_all_stocks_for_product(prod_id)

    available = [s for s in stocks if not s["is_sold"]]
    sold = [s for s in stocks if s["is_sold"]]

    text = (
        f"📦 <b>{prod['name']}</b> - Stocks\n\n"
        f"✅ Available: {len(available)} ခု\n"
        f"❌ Sold: {len(sold)} ခု\n\n"
    )

    if available:
        text += "<b>Available Stocks:</b>\n"
        for i, s in enumerate(available[:20], 1):
            text += f"{i}. <code>{s['content']}</code>\n"
        if len(available) > 20:
            text += f"... နှင့် {len(available) - 20} ခု ပိုရှိသည်\n"

    keyboard = [
        [InlineKeyboardButton("➕ Stock ထည့်", callback_data=f"admin_add_stocks_{prod_id}")],
        [InlineKeyboardButton("◀️ Back", callback_data="admin_stocks")]
    ]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
    )


async def show_admin_settings(query):
    settings = db.get_all_settings()
    keyboard = []
    for key, value in settings.items():
        display = value[:30] + "..." if len(value) > 30 else value
        keyboard.append([InlineKeyboardButton(
            f"✏️ {key}: {display}",
            callback_data=f"admin_setting_edit_{key}"
        )])
    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="admin_panel")])
    await query.edit_message_text(
        "⚙️ <b>Bot Settings</b>\n\n<i>Setting တခုကို ဖိနှိပ်ပြင်ဆင်နိုင်သည်</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


async def show_admin_users(query):
    users = db.get_all_users()
    text = f"👥 <b>Users ({len(users)})</b>\n\n"
    keyboard = []
    for u in users[:20]:
        name = u["full_name"] or u["username"] or str(u["user_id"])
        ban_status = "🚫" if u["is_banned"] else "✅"
        text += f"{ban_status} {name} | {fmt_mmk(u['balance'])}\n"
        if u["is_banned"]:
            keyboard.append([InlineKeyboardButton(
                f"✅ Unban {name[:15]}",
                callback_data=f"admin_unban_{u['user_id']}"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                f"🚫 Ban {name[:15]}",
                callback_data=f"admin_ban_{u['user_id']}"
            )])

    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="admin_panel")])
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
    )


async def show_admin_orders(query):
    orders = db.get_all_orders(limit=30)
    if not orders:
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="admin_panel")]]
        await query.edit_message_text("📊 Order မရှိသေးပါ။",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = f"📊 <b>Recent Orders ({len(orders)})</b>\n\n"
    for order in orders[:15]:
        name = order["full_name"] or order["username"] or str(order["user_id"])
        text += (
            f"• {name} → {order['product_name']}\n"
            f"  {fmt_mmk(order['amount_paid'])} | {order['created_at']}\n\n"
        )

    keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="admin_panel")]]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════
# CONVERSATION HANDLERS (State Machine)
# ═══════════════════════════════════════════════════════════════════

# ── Add Product Flow ───────────────────────────────────────────────

async def state_add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"] = {"name": update.message.text.strip()}
    categories = db.get_categories()
    if not categories:
        await update.message.reply_text(
            "❌ Category မရှိသေးပါ! /admin မှ Category ဦးစွာ ထည့်ပါ။"
        )
        return cfg.STATE_NONE

    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(cat["name"], callback_data=f"setcat_{cat['id']}")])
    await update.message.reply_text(
        "📁 Category ရွေးပါ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return cfg.STATE_ADD_PRODUCT_CATEGORY


async def state_add_product_category_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_id = int(query.data.split("_")[1])
    context.user_data["new_product"]["category_id"] = cat_id
    await query.edit_message_text("💰 Price (MMK) ရိုက်ထည့်ပါ:\n<i>Example: 3000</i>",
                                   parse_mode=ParseMode.HTML)
    return cfg.STATE_ADD_PRODUCT_PRICE


async def state_add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ မှန်ကန်သော ငွေပမာဏ ရိုက်ထည့်ပါ:")
        return cfg.STATE_ADD_PRODUCT_PRICE
    context.user_data["new_product"]["price"] = int(text)
    await update.message.reply_text(
        "⏱ Duration ရိုက်ထည့်ပါ:\n"
        "<i>Example: 1 Month, 2 Months, 3 Months, Lifetime, etc.</i>\n\n"
        "မလိုပါက - ရိုက်ပါ",
        parse_mode=ParseMode.HTML
    )
    return cfg.STATE_ADD_PRODUCT_DURATION


async def state_add_product_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["new_product"]["duration"] = "" if val == "-" else val
    keyboard = [
        [InlineKeyboardButton("🔒 Private", callback_data="settype_private")],
        [InlineKeyboardButton("🔗 Shared", callback_data="settype_shared")],
    ]
    await update.message.reply_text("🏷 Product Type ရွေးပါ:",
                                     reply_markup=InlineKeyboardMarkup(keyboard))
    return cfg.STATE_ADD_PRODUCT_TYPE


async def state_add_product_type_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ptype = query.data.split("_")[1]
    context.user_data["new_product"]["product_type"] = ptype
    await query.edit_message_text(
        "📝 Description ရိုက်ထည့်ပါ:\n<i>မလိုပါက - ရိုက်ပါ</i>",
        parse_mode=ParseMode.HTML
    )
    return cfg.STATE_ADD_PRODUCT_DESC


async def state_add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    np = context.user_data["new_product"]
    np["description"] = "" if val == "-" else val

    prod_id = db.add_product(
        name=np["name"],
        category_id=np["category_id"],
        price=np["price"],
        duration=np.get("duration", ""),
        product_type=np.get("product_type", "private"),
        description=np.get("description", "")
    )

    await update.message.reply_text(
        f"✅ <b>Product ထည့်ပြီးပါပြီ!</b>\n\n"
        f"🆔 ID: #{prod_id}\n"
        f"📦 Name: {np['name']}\n"
        f"💰 Price: {fmt_mmk(np['price'])}\n"
        f"⏱ Duration: {np.get('duration') or 'N/A'}\n\n"
        f"📥 ယခု Stock ထည့်ရန် /admin မှ Stocks သို့ သွားပါ",
        parse_mode=ParseMode.HTML
    )
    context.user_data.clear()
    return cfg.STATE_NONE


# ── Add Category Flow ──────────────────────────────────────────────

async def state_add_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    cat_id = db.add_category(name)
    if cat_id:
        await update.message.reply_text(f"✅ Category '<b>{name}</b>' ထည့်ပြီးပါပြီ!",
                                         parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ '{name}' ဆိုသော Category ရှိပြီးသားဖြစ်သည်!")
    return cfg.STATE_NONE


# ── Add Stock Flow ─────────────────────────────────────────────────

async def state_add_stock_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    prod_id = context.user_data.get("stock_product_id")
    prod = db.get_product(prod_id)

    if text == "/done":
        items = context.user_data.get("stock_items", [])
        if items:
            count = db.add_stocks_bulk(prod_id, items)
            await update.message.reply_text(
                f"✅ <b>{prod['name']}</b> တွင် Stock {count} ခု ထည့်ပြီးပါပြီ!",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ Stock မထည့်ရသေးပါ!")
        context.user_data.clear()
        return cfg.STATE_NONE

    # Support multi-line input
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    context.user_data.setdefault("stock_items", []).extend(lines)
    total = len(context.user_data["stock_items"])
    await update.message.reply_text(
        f"✅ {len(lines)} ခု ထည့်ပြီး (စုစုပေါင်း: {total} ခု)\n"
        f"ဆက်ထည့်နိုင်သည် သို့မဟုတ် /done ရိုက်ပါ"
    )
    return cfg.STATE_ADD_STOCK_CONTENT


# ── Edit Setting Flow ──────────────────────────────────────────────

async def state_edit_setting_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("edit_setting_key")
    value = update.message.text.strip()
    db.set_setting(key, value)
    await update.message.reply_text(
        f"✅ Setting '<b>{key}</b>' ကို Update လုပ်ပြီးပါပြီ!\n\n"
        f"New Value: <code>{value}</code>",
        parse_mode=ParseMode.HTML
    )
    context.user_data.clear()
    return cfg.STATE_NONE


# ── Broadcast Flow ─────────────────────────────────────────────────

async def state_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return cfg.STATE_NONE

    message_text = update.message.text.strip()
    users = db.get_all_users()
    success = 0
    failed = 0

    await update.message.reply_text(f"📢 User {len(users)} ဦးထံ ပို့နေသည်...")

    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=f"📢 <b>Announcement</b>\n\n{message_text}",
                parse_mode=ParseMode.HTML
            )
            success += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast ပြီးပါပြီ!\n✅ Success: {success}\n❌ Failed: {failed}"
    )
    context.user_data.clear()
    return cfg.STATE_NONE


# ── Cancel ────────────────────────────────────────────────────────

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancel လုပ်ပြီးပါပြီ။ /start ဖြင့် ပြန်စနိုင်သည်။")
    return cfg.STATE_NONE


# ── Admin shortcut ─────────────────────────────────────────────────

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin သာ ဝင်ခွင့်ရှိသည်!")
        return
    pending = db.get_pending_topups()
    users = db.get_all_users()
    keyboard = [
        [InlineKeyboardButton(
            f"💳 Pending Top-Ups ({len(pending)})",
            callback_data="admin_pending_topups"
        )],
        [InlineKeyboardButton("📦 Products", callback_data="admin_products"),
         InlineKeyboardButton("📁 Categories", callback_data="admin_categories")],
        [InlineKeyboardButton("📥 Stocks", callback_data="admin_stocks"),
         InlineKeyboardButton("📊 Orders", callback_data="admin_orders")],
        [InlineKeyboardButton(f"👥 Users ({len(users)})", callback_data="admin_users")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]
    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


# ── Top-up shortcut ────────────────────────────────────────────────

async def cmd_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.full_name)
    wave_num = db.get_setting("wave_number")
    kbz_num = db.get_setting("kbz_number")
    pay_name = db.get_setting("payment_name")
    keyboard = [
        [InlineKeyboardButton("📱 Wave Pay", callback_data="topup_wave")],
        [InlineKeyboardButton("🏦 KBZ Pay", callback_data="topup_kbz")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    await update.message.reply_text(
        f"💳 <b>ငွေဖြည့်မည်</b>\n\n"
        f"📱 Wave Pay: <code>{wave_num}</code>\n"
        f"🏦 KBZ Pay: <code>{kbz_num}</code>\n"
        f"👤 Name: <b>{pay_name}</b>\n\n"
        f"Payment Method ရွေးပါ:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    db.init_db()

    app = Application.builder().token(cfg.BOT_TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(callback_router),
        ],
        states={
            cfg.STATE_TOPUP_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topup_amount)
            ],
            cfg.STATE_TOPUP_SCREENSHOT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, handle_topup_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topup_screenshot),
            ],
            cfg.STATE_ADD_PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_add_product_name)
            ],
            cfg.STATE_ADD_PRODUCT_CATEGORY: [
                CallbackQueryHandler(state_add_product_category_cb, pattern="^setcat_")
            ],
            cfg.STATE_ADD_PRODUCT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_add_product_price)
            ],
            cfg.STATE_ADD_PRODUCT_DURATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_add_product_duration)
            ],
            cfg.STATE_ADD_PRODUCT_TYPE: [
                CallbackQueryHandler(state_add_product_type_cb, pattern="^settype_")
            ],
            cfg.STATE_ADD_PRODUCT_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_add_product_desc)
            ],
            cfg.STATE_ADD_CATEGORY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_add_category_name)
            ],
            cfg.STATE_ADD_STOCK_CONTENT: [
                MessageHandler(filters.TEXT, state_add_stock_content)
            ],
            cfg.STATE_EDIT_SETTING_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_edit_setting_value)
            ],
            cfg.STATE_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, state_broadcast)
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("topup", cmd_topup))
    app.add_handler(CommandHandler("admin", cmd_admin))

    print("🤖 Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
