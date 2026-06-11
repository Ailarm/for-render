import os
import sqlite3
import datetime
import matplotlib.pyplot as plt

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from openai import OpenAI
import anthropic

# =========================
# ENV
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")
CLAUDE_KEY = os.getenv("CLAUDE_KEY")

gpt = OpenAI(api_key=OPENAI_KEY)
claude = anthropic.Anthropic(api_key=CLAUDE_KEY)

# =========================
# DB
# =========================
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    user_id INTEGER,
    date TEXT,
    plan TEXT,
    report TEXT,
    score INTEGER
)
""")
conn.commit()

# =========================
# MEMORY
# =========================
memory = {}

# =========================
# AI EVALUATION
# =========================
def evaluate(plan, report):
    try:
        res = claude.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""
تو یک مربی سخت‌گیر واقعی هستی.

برنامه:
{plan}

گزارش:
{report}

خروجی:
- درصد انجام (0 تا 100)
- ایراد اصلی
- یک جمله تشویقی واقعی
- امتیاز نهایی 0 تا 100
"""
            }]
        )
        return res.content[0].text
    except:
        return "50|خطا|ادامه بده|50"

def coach(text):
    res = gpt.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "تو یک کوچ سخت‌گیر و کاملاً واقع‌بین هستی."},
            {"role": "user", "content": text}
        ]
    )
    return res.choices[0].message.content

# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋 برنامه امروزتو بنویس.")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    today = str(datetime.date.today())

    if user_id not in memory:
        memory[user_id] = {"plan": None}

    if memory[user_id]["plan"] is None:
        memory[user_id]["plan"] = text
        await update.message.reply_text("ثبت شد 👌 شب گزارش بده.")
        return

    plan = memory[user_id]["plan"]
    report = text

    analysis = evaluate(plan, report)

    try:
        score = int([x for x in analysis.split() if x.isdigit()][-1])
    except:
        score = 60

    final_reply = coach(analysis)

    cursor.execute(
        "INSERT INTO logs VALUES (?, ?, ?, ?, ?)",
        (user_id, today, plan, report, score)
    )
    conn.commit()

    memory[user_id] = {"plan": None}

    await update.message.reply_text(f"📊 امتیاز: {score}/100\n\n{final_reply}")

# =========================
# CHARTS
# =========================
def get_scores(user_id, mode="week"):
    cursor.execute(
        "SELECT date, score FROM logs WHERE user_id=? ORDER BY date DESC",
        (user_id,)
    )
    data = cursor.fetchall()

    if mode == "week":
        data = data[:7]
    elif mode == "month":
        data = data[:30]

    return data[::-1]

def make_chart(user_id, mode):
    data = get_scores(user_id, mode)

    if not data:
        return None

    dates = [d[0] for d in data]
    scores = [d[1] for d in data]

    plt.figure()
    plt.plot(dates, scores)
    plt.title(f"{mode} progress")
    plt.xticks(rotation=45)
    plt.tight_layout()

    path = f"{user_id}_{mode}.png"
    plt.savefig(path)
    plt.close()

    return path

# =========================
# COMMANDS
# =========================
async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = make_chart(update.effective_user.id, "week")
    if path:
        await update.message.reply_photo(photo=open(path, "rb"))
    else:
        await update.message.reply_text("داده کافی نداریم.")

async def monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = make_chart(update.effective_user.id, "month")
    if path:
        await update.message.reply_photo(photo=open(path, "rb"))
    else:
        await update.message.reply_text("داده کافی نداریم.")

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("weekly", weekly))
    app.add_handler(CommandHandler("monthly", monthly))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
