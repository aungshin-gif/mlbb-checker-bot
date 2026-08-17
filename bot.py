import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
G2BULK_API_KEY = os.getenv("G2BULK_API_KEY", "")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", "10000"))
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
API_BASE = "https://api.g2bulk.com/v1"

if not BOT_TOKEN or not G2BULK_API_KEY:
    raise RuntimeError("TELEGRAM_BOT_TOKEN and G2BULK_API_KEY are required")

@dataclass(frozen=True)
class Game:
    code: str
    name: str
    emoji: str
    style: str

GAMES = [
    Game("mlbb", "Mobile Legends", "🔵", "primary"),
    Game("pubgm", "PUBG Mobile", "🟢", "success"),
    Game("freefire_global", "Free Fire Global", "🟡", "primary"),
    Game("hok", "Honor of Kings", "🔴", "danger"),
    Game("valorant", "Valorant", "🟣", "primary"),
    Game("codm_sgmy", "Call of Duty Mobile", "⚫", "danger"),
    Game("deltaforce", "Delta Force", "🟤", "danger"),
    Game("aove", "Arena of Valor", "🟠", "success"),
    Game("league_of_legends_my", "League of Legends MY", "🔷", "primary"),
    Game("freefire_bd", "Free Fire Bangladesh", "🟩", "success"),
]
GAME_MAP = {game.code: game for game in GAMES}

router = Router()

class TopUp(StatesGroup):
    waiting_player_id = State()
    waiting_denomination = State()
    confirming = State()

async def api_request(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"X-API-Key": G2BULK_API_KEY, "Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.request(method, f"{API_BASE}{path}", headers=headers, json=payload) as response:
            data = await response.json(content_type=None)
            if response.status >= 400:
                raise RuntimeError(data.get("message", f"G2Bulk HTTP {response.status}"))
            return data

def button(text: str, callback: str, style: str | None = None) -> InlineKeyboardButton:
    # Telegram Bot API button style: primary (blue), success (green), danger (red).
    return InlineKeyboardButton(text=text, callback_data=callback, style=style)

def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [button("🎮 GAME LIST", "games", "primary"), button("💰 BALANCE", "balance", "success")],
        [button("🔎 SEARCH", "search_help", "primary"), button("📞 SUPPORT", "support", "danger")],
    ])

def games_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for index in range(0, len(GAMES), 2):
        row = []
        for game in GAMES[index:index + 2]:
            row.append(button(f"{game.emoji} {game.name}", f"game:{game.code}", game.style))
        rows.append(row)
    rows.append([button("🔙 MAIN MENU", "home", "primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def catalogue_keyboard(items: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    rows = []
    for item in items[:24]:
        rows.append([button(f"🎟️ {item.get('name')} — {float(item.get('amount', 0)):.2f}", f"denom:{item.get('name')}", "success")])
    rows.append([button("🔙 GAME LIST", "games", "primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [button("✅ CONFIRM ORDER", "confirm", "success")],
        [button("❌ CANCEL", "cancel_order", "danger")],
    ])

@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        f"✨ <b>GAME TOP-UP STORE</b> ✨\n━━━━━━━━━━━━━━\nမင်္ဂလာပါ {message.from_user.first_name}!\n\nFast • Safe • Reliable\nGame ၁၀ ခုအတွက် top-up order တင်နိုင်ပါတယ်။",
        reply_markup=main_keyboard(),
    )

@router.message(Command("games"))
@router.callback_query(F.data == "games")
async def show_games(event: Message | CallbackQuery) -> None:
    text = "🎮 <b>GAME STORE</b>\n━━━━━━━━━━━━━━\nGame ၁၀ ခုထဲက ရွေးပါ။\n\n" + "\n".join(f"{g.emoji} {i + 1}. {g.name}" for i, g in enumerate(GAMES))
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text + "\n\n👇 အောက်က button ကိုနှိပ်ပါ။", reply_markup=games_keyboard())
    else:
        await event.answer(text + "\n\n👇 အောက်က button ကိုနှိပ်ပါ။", reply_markup=games_keyboard())

@router.callback_query(F.data == "home")
async def home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.answer("🏠 <b>MAIN MENU</b>", reply_markup=main_keyboard())

@router.callback_query(F.data == "search_help")
async def search_help(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("🔎 `/search mobile` လို့ ရိုက်ပြီး game ရှာပါ။")

@router.message(Command("search"))
async def search(message: Message) -> None:
    term = message.text.removeprefix("/search").strip().lower()
    if not term:
        await message.answer("🔎 ဥပမာ `/search mobile` လို့ ရိုက်ပါ။")
        return
    found = [g for g in GAMES if term in f"{g.name} {g.code}".lower()]
    if not found:
        await message.answer("❌ ဒီ game ၁၀ ခုထဲမှာ မတွေ့ပါ။")
        return
    await message.answer("🔎 <b>ရှာတွေ့သည်</b>\n\n" + "\n".join(f"{g.emoji} {g.name} — <code>{g.code}</code>" for g in found))

@router.callback_query(F.data == "balance")
async def balance_callback(callback: CallbackQuery) -> None:
    await callback.answer("စစ်နေပါတယ်...")
    try:
        data = await api_request("/getMe")
        await callback.message.answer(f"💰 <b>WALLET BALANCE</b>\n━━━━━━━━━━━━━━\n<code>{float(data.get('balance', 0)):.2f}</code>")
    except Exception as exc:
        await callback.message.answer(f"❌ Balance စစ်မရပါ။ {exc}")

@router.message(Command("balance"))
async def balance_command(message: Message) -> None:
    try:
        data = await api_request("/getMe")
        await message.answer(f"💰 လက်ကျန်: <code>{float(data.get('balance', 0)):.2f}</code>")
    except Exception as exc:
        await message.answer(f"❌ Balance စစ်မရပါ။ {exc}")

@router.callback_query(F.data.startswith("game:"))
async def choose_game(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    game = GAME_MAP.get(code)
    if not game:
        await callback.answer("Game မတွေ့ပါ။", show_alert=True)
        return
    try:
        catalogue = await api_request(f"/games/{code}/catalogue")
        items = catalogue.get("catalogues", [])
        if not items:
            await callback.answer("Catalogue မရှိသေးပါ။", show_alert=True)
            return
        await state.update_data(game=game.__dict__, catalogues=items)
        await state.set_state(TopUp.waiting_player_id)
        await callback.answer()
        await callback.message.answer(f"{game.emoji} <b>{game.name}</b>\n━━━━━━━━━━━━━━\nPlayer ID ကို ပို့ပါ။")
    except Exception as exc:
        await callback.answer("API error", show_alert=True)
        await callback.message.answer(f"❌ Catalogue မရပါ။ {exc}")

@router.message(TopUp.waiting_player_id)
async def receive_player_id(message: Message, state: FSMContext) -> None:
    await state.update_data(player_id=message.text.strip())
    data = await state.get_data()
    await state.set_state(TopUp.waiting_denomination)
    await message.answer("🎯 <b>DENOMINATION ရွေးပါ</b>", reply_markup=catalogue_keyboard(data["catalogues"]))

@router.callback_query(TopUp.waiting_denomination, F.data.startswith("denom:"))
async def choose_denomination(callback: CallbackQuery, state: FSMContext) -> None:
    name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    item = next((x for x in data["catalogues"] if x.get("name") == name), None)
    if not item:
        await callback.answer("Denomination မတွေ့ပါ။", show_alert=True)
        return
    await state.update_data(catalogue=item)
    await state.set_state(TopUp.confirming)
    game = data["game"]
    await callback.answer()
    await callback.message.answer(
        f"{game['emoji']} <b>ORDER SUMMARY</b>\n━━━━━━━━━━━━━━\nGame: {game['name']}\nPlayer ID: <code>{data['player_id']}</code>\nItem: {item['name']}\nPrice: <b>{float(item.get('amount', 0)):.2f}</b>\n━━━━━━━━━━━━━━\nအချက်အလက်မှန်ပါက Confirm နှိပ်ပါ။",
        reply_markup=confirm_keyboard(),
    )

@router.callback_query(TopUp.confirming, F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Cancelled")
    await callback.message.answer("❌ Order ဖျက်လိုက်ပါပြီ။", reply_markup=main_keyboard())

@router.callback_query(TopUp.confirming, F.data == "confirm")
async def confirm_order(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    game, item = data["game"], data["catalogue"]
    await callback.answer("Order တင်နေပါတယ်...")
    try:
        result = await api_request(
            f"/games/{game['code']}/order",
            method="POST",
            payload={
                "catalogue_name": item["name"],
                "player_id": data["player_id"],
                "remark": f"Telegram user {callback.from_user.id}",
            },
        )
        order = result.get("order", {})
        await callback.message.answer(
            f"✅ <b>ORDER RECEIVED</b>\n━━━━━━━━━━━━━━\nOrder ID: <code>{order.get('order_id')}</code>\nGame: {order.get('game', game['name'])}\nItem: {order.get('catalogue', item['name'])}\nStatus: <b>{order.get('status')}</b>\nPrice: {float(order.get('price', item.get('amount', 0))):.2f}",
            reply_markup=main_keyboard(),
        )
        if ADMIN_CHAT_ID:
            await bot.send_message(ADMIN_CHAT_ID, f"New order {order.get('order_id')}: {game['name']} / {item['name']} / {data['player_id']}")
    except Exception as exc:
        await callback.message.answer(f"❌ Order တင်မရပါ။ {exc}", reply_markup=main_keyboard())
    finally:
        await state.clear()

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ လုပ်ဆောင်ချက် ဖျက်လိုက်ပါပြီ။", reply_markup=main_keyboard())

async def main() -> None:
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await bot.set_my_commands([
        {"command": "start", "description": "Main menu"},
        {"command": "games", "description": "Game list"},
        {"command": "search", "description": "Search game"},
        {"command": "balance", "description": "Check balance"},
        {"command": "cancel", "description": "Cancel current order"},
    ])
    if RENDER_EXTERNAL_URL:
        path = f"/telegram/{BOT_TOKEN}"
        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=path)
        setup_application(app, dp, bot=bot)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        await bot.set_webhook(f"{RENDER_EXTERNAL_URL}{path}")
        await asyncio.Event().wait()
    else:
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
