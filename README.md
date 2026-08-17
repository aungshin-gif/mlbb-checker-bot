# G2Bulk Telegram Bot — Aiogram

G2Bulk API ကိုချိတ်ဆက်ထားသော Python **Aiogram 3** Telegram bot ဖြစ်သည်။ လက်ရှိ MVP တွင် game ၁၀ ခု၊ inline keyboard menu၊ game-specific color style၊ player ID လက်ခံခြင်း၊ catalogue ရွေးခြင်းနှင့် order confirm flow ပါဝင်သည်။

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
| `/games` | Game ၁၀ ခု ပြရန် |
| `/search mobile` | Game ရှာရန် |
| `/balance` | G2Bulk wallet balance စစ်ရန် |
| `/cancel` | လက်ရှိ flow ဖျက်ရန် |

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

## Render deployment

GitHub repository ထဲသို့ ဖိုင်များတင်ပြီး Render တွင် **New Web Service** ကိုရွေးပါ။ `render.yaml` ကို အသုံးပြုပါက setting အများစု အလိုအလျောက်ရမည်။ Manual setup ပြုလုပ်ပါက Build Command သည် `pip install -r requirements.txt` ဖြစ်ပြီး Start Command သည် `python bot.py` ဖြစ်သည်။

Render Environment Variables တွင် အောက်ပါအတိုင်းထည့်ပါ။

```
TELEGRAM_BOT_TOKEN=BotFather token
G2BULK_API_KEY=G2Bulk API key
RENDER_EXTERNAL_URL=https://your-service.onrender.com
ADMIN_CHAT_ID=optional admin chat id
```

Token နှစ်ခုကို GitHub code ထဲ မရေးပါနှင့်။ `.env` ကို commit မလုပ်ပါနှင့်။ Render free service sleep ဖြစ်ပါက webhook bot response ပထမဆုံး request တွင် အနည်းငယ်နှေးနိုင်သည်။

## References

[1]: https://core.telegram.org/api/bots/buttons "Telegram Bot buttons and Button styles"

[2]: https://docs.aiogram.dev/en/latest/api/types/inline_keyboard_button.html "Aiogram InlineKeyboardButton documentation"
