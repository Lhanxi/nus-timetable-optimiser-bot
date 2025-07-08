from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    InlineQueryHandler,
    filters,
    ConversationHandler
)
from fetcher import NUSModsAPI
from process_data import preprocess_module
from scheduler_new import SchedulerMIP
import uuid
from dotenv import load_dotenv

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

api = NUSModsAPI()

# States
ASK_N, ASK_COMPULSORY, ASK_OPTIONAL, ASK_SEMESTER = range(4)

user_inputs = {
    "compulsory": [],
    "optional": []
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[str(i)] for i in range(1, 11)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("👋 Welcome! How many modules do you want to take?", reply_markup=reply_markup)
    return ASK_N

async def ask_compulsory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_inputs["N"] = int(update.message.text)
    user_inputs["compulsory"] = []
    keyboard = [["Done ✅"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "✅ Send *compulsory* modules one by one using inline search.\n"
        "🔍 In any chat, type: `@nus_mod_bot INSERT_MODULE_CODE` and tap a module to send.\n"
        "✅ When you're done, tap 'Done ✅'.",
        reply_markup=reply_markup
    )
    return ASK_COMPULSORY

async def add_compulsory_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mod = update.message.text.strip().upper()
    if mod not in user_inputs["compulsory"]:
        user_inputs["compulsory"].append(mod)
        keyboard = [["Done ✅"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(f"✅ Added: {mod}", reply_markup=reply_markup)
    return ASK_COMPULSORY

async def done_compulsory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Done ✅"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "✅ Now send *optional* modules using inline search.\n"
        "🔍 Type: `@YourBot GE`, tap a result to send.\n"
        "✅ Tap 'Done ✅' when finished.",
        reply_markup=reply_markup
    )
    return ASK_OPTIONAL

async def add_optional_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mod = update.message.text.strip().upper()
    if mod not in user_inputs["optional"]:
        user_inputs["optional"].append(mod)
        keyboard = [["Done ✅"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(f"✅ Added: {mod}", reply_markup=reply_markup)
    return ASK_OPTIONAL

async def done_optional(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["1"], ["2"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("🗓️ Choose the semester:", reply_markup=reply_markup)
    return ASK_SEMESTER

async def ask_semester(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_inputs["semester"] = int(update.message.text)
    await update.message.reply_text("⏳ Optimizing schedule...")

    all_codes = user_inputs['compulsory'] + user_inputs['optional']
    raw_data = api.fetch_bulk_module_data(all_codes, user_inputs['semester'])

    preprocessed = {}
    for code in all_codes:
        if "error" in raw_data[code]:
            await update.message.reply_text(f"⚠️ Error fetching {code}: {raw_data[code]['error']}")
            return ConversationHandler.END
        processed = preprocess_module(code, raw_data[code], user_inputs['semester'])
        preprocessed[code] = processed[code]

    scheduler = SchedulerMIP(preprocessed, user_inputs['compulsory'], user_inputs['optional'], user_inputs['N'])
    best_schedule, selected = scheduler.find_best_schedule()

    if not best_schedule:
        await update.message.reply_text("❌ Could not find a valid timetable with your inputs.")
    else:
        result = f"✅ Selected Modules: {', '.join(selected)}\n\n📅 Optimized Timetable:"
        for entry in best_schedule:
            result += f"\n\n📘 {entry['module']}"
            for l in entry["lessons"]:
                result += f"\n  [{l['lessonType']}] {l['day']} {l['startTime']}-{l['endTime']} @ {l['venue']}"
        await update.message.reply_text(result)

    return ConversationHandler.END

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip().lower()
    results = []

    if not query:
        await update.inline_query.answer([])
        return

    all_modules = api.fetch_module_list()
    matches = [m for m in all_modules if query in m["moduleCode"].lower()]
    matches = matches[:10]

    for m in matches:
        module_code = m["moduleCode"]
        title = f"{module_code} – {m['title']}"
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=title,
                input_message_content=InputTextMessageContent(f"{module_code}"),
                description=m["title"]
            )
        )

    await update.inline_query.answer(results, cache_time=1)

# Build app
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_N: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compulsory)],
        ASK_COMPULSORY: [
            MessageHandler(filters.TEXT & filters.Regex("^Done ✅$"), done_compulsory),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_compulsory_module)
        ],
        ASK_OPTIONAL: [
            MessageHandler(filters.TEXT & filters.Regex("^Done ✅$"), done_optional),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_optional_module)
        ],
        ASK_SEMESTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_semester)],
    },
    fallbacks=[]
)

# Add handlers
app.add_handler(conv_handler)
app.add_handler(InlineQueryHandler(handle_inline_query))

print("✅ Bot is running. Try typing @YourBot CS in any chat.")
app.run_polling()
