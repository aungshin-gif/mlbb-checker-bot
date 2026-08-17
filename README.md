






# G2Bulk Telegram Bot — Aiogram

G2Bulk API ကိုချိတ်ဆက်ထားသော Python **Aiogram 3** Telegram bot ဖြစ်သည်။ လက်ရှိ MVP တွင် game ၁၅ ခု၊ inline keyboard menu၊ button style၊ player ID လက်ခံခြင်း၊ catalogue ရွေးခြင်း၊ MMK customer pricing နှင့် order confirm flow ပါဝင်သည်။

## Pricing နှင့် recharge

G2Bulk catalogue မှာ ပြန်လာသော amount ကို API unit အရ USD အဖြစ်ယူပြီး `USD_TO_MMK_RATE` ဖြင့် MMK ပြောင်းကာ `STORE_MARKUP_PERCENT` ဖြင့် customer price တွက်သည်။ Default rate သည် 1 USD = 4500 MMK ဖြစ်သော်လည်း live exchange rate အဖြစ် အာမခံမထားပါ။ သင်ကိုယ်တိုင် သတ်မှတ်ထားသော rate ကို Render Environment Variables ထဲတွင် ပြောင်းပါ။

Recharge သည် local manual flow ဖြစ်သည်။ User က MMK amount ထည့်ပြီး payment receipt screenshot ပို့သည်။ Bot က receipt ကို `ADMIN_CHAT_ID` သို့ ပို့ပြီး admin က ကိုယ်တိုင်စစ်ဆေး၍ G2Bulk wallet နှင့် customer balance စာရင်းကို update လုပ်ရမည်။ G2Bulk API documentation တွင် public customer recharge endpoint မတွေ့ရသဖြင့် bot က user money ကို အလိုအလျောက် G2Bulk wallet ထဲ မပို့ပါ။

## Telegram button style

Aiogram `InlineKeyboardButton` တွင် Telegram Bot API ၏ `style` field ကို အသုံးပြုထားသည်။ လက်ခံသော style သုံးမျိုးမှာ `primary` (အပြာ), `success` (အစိမ်း) နှင့် `danger` (အနီ) ဖြစ်သည်။ Client version သို့မဟုတ် Telegram app အဟောင်းများတွင် style မပေါ်ပါက button သည် default style သို့ fallback ဖြစ်နိုင်သည်။

```python
InlineKeyboardButton(
    text="✅ CONFIRM ORDER",
    callback_data="confirm",
    style="success",
)
```

Telegram မှာ arbitrary hex color သတ်မှတ်၍ မရပါ။ `primary`, `success`, `danger` သုံးမျိုးနှင့် emoji/icon ကိုသာ အသုံးပြုနိုင်သည်။

## Bot commands

| Command | လုပ်ဆောင်ချက် |
| --- | --- |
| `/start` | Main menu ဖွင့်ရန် |
| `/games` | Game ၁၅ ခု ပြရန် |
| `/search mobile` | Game ရှာရန် |
| `/balance` | G2Bulk wallet balance စစ်ရန် |
| `/cancel` | လက်ရှိ flow ဖျက်ရန် |
| `/recharge` | MMK recharge request တင်ရန် |

## Game flow

User သည် game button ကိုနှိပ်ပြီး player ID ပို့သည်။ ထို့နောက် API မှ live catalogue ရယူကာ denomination buttons ပြသည်။ User က denomination ရွေးပြီး `CONFIRM ORDER` ကိုနှိပ်သောအခါ G2Bulk API သို့ order တင်သည်။

## Local run

Python 3.11 သို့မဟုတ် အထက်ဖြင့် run ပါ။

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

`RENDER_EXTERNAL_URL` မထည့်ထားလျှင် polling mode သုံးမည်။ Render URL ထည့်ထားလျှင် webhook mode သို့ ပြောင်းမည်။

## Supabase database setup

`schema.sql` ဖိုင်ကို Supabase Dashboard ရှိ **SQL Editor** ထဲ paste လုပ်ပြီး Run နှိပ်ပါ။ ထို့နောက် Render Environment Variables ထဲတွင် `DATABASE_URL` ကို Supabase Connection string အပြည့်ဖြင့်ထည့်ပါ။ Password ကို GitHub သို့မဟုတ် chat ထဲ မတင်ပါနှင့်။

Database ထဲတွင် users, wallet transactions, recharge requests နှင့် orders များကို persistent အဖြစ် သိမ်းထားသည်။ Recharge approve နှင့် order debit များသည် transaction ဖြင့် လုပ်ဆောင်ပြီး Render restart/redeploy ဖြစ်လည်း data မပျောက်ပါ။

Order Confirm မလုပ်မီ G2Bulk catalogue ကို တစ်ကြိမ်ထပ်ဖတ်သည်။ Supplier price သို့မဟုတ် stock ပြောင်းသွားလျှင် old price ဖြင့် order မတင်ဘဲ အသစ်စျေးကို ပြန်အတည်ပြုခိုင်းသည်။

## Render deployment

GitHub repository ထဲသို့ ဖိုင်များတင်ပြီး Render တွင် **New Web Service** ကိုရွေးပါ။ `render.yaml` ကို အသုံးပြုပါက setting အများစု အလိုအလျောက်ရမည်။ Manual setup ပြုလုပ်ပါက Build Command သည် `pip install -r requirements.txt` ဖြစ်ပြီး Start Command သည် `python bot.py` ဖြစ်သည်။

Render Environment Variables တွင် အောက်ပါအတိုင်းထည့်ပါ။

```
TELEGRAM_BOT_TOKEN=BotFather token
G2BULK_API_KEY=G2Bulk API key
RENDER_EXTERNAL_URL=https://your-service.onrender.com
ADMIN_CHAT_ID=admin chat id
DATABASE_URL=Supabase PostgreSQL connection string
USD_TO_MMK_RATE=4500
STORE_MARKUP_PERCENT=10
PAYMENT_INSTRUCTIONS=your payment instructions
ADMIN_USERNAME=@your_admin_username
```

Token နှစ်ခုကို GitHub code ထဲ မရေးပါနှင့်။ `.env` ကို commit မလုပ်ပါနှင့်။ Render free service sleep ဖြစ်ပါက webhook bot response ပထမဆုံး request တွင် အနည်းငယ်နှေးနိုင်သည်။

## References

[1]: https://core.telegram.org/api/bots/buttons "Telegram Bot buttons and Button styles"

[2]: https://docs.aiogram.dev/en/latest/api/types/inline_keyboard_button.html "Aiogram InlineKeyboardButton documentation"

