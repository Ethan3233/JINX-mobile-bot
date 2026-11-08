import os
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from google import genai

# --- YOUR API KEYS ---
GEMINI_API_KEY = "AQ.Ab8RN6J7q-RlRClKhMsjTZ33fzjaiaWo3cSGfT9-utwjLUhvbQ"
TELEGRAM_BOT_TOKEN = "9239146906:AAGEArnsuvV4b7n559p_xp3xK75JELJFyj8"

client = genai.Client(api_key=GEMINI_API_KEY)

# --- DATABASE SETUP (Long-term Memory, Contacts, Notes) ---
def init_db():
    conn = sqlite3.connect('jarvis_mobile.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS memory (user_id INTEGER, category TEXT, content TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS chat_history (user_id INTEGER, role TEXT, message TEXT)')
    conn.commit()
    conn.close()

init_db()

def save_memory(user_id, category, content):
    conn = sqlite3.connect('jarvis_mobile.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memory (user_id, category, content) VALUES (?, ?, ?)", (user_id, category, content))
    conn.commit()
    conn.close()

def get_memories(user_id):
    conn = sqlite3.connect('jarvis_mobile.db')
    cursor = conn.cursor()
    cursor.execute("SELECT category, content FROM memory WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def save_chat(user_id, role, message):
    conn = sqlite3.connect('jarvis_mobile.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (user_id, role, message) VALUES (?, ?, ?)", (user_id, role, message))
    conn.commit()
    conn.close()

# --- COMMANDS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **JINX Mobile Edition — Online**\n\n"
        "✨ **Active Features:**\n"
        "• AI Conversation & Chat Memory\n"
        "• Auto Translation (`/tr [lang] [text]`)\n"
        "• GED Study Assistant (`/ged [subject] [question]`)\n"
        "• Contact & Note Saving ('မှတ်ထား...' လို့ပြောပါ)\n"
        "• Image Understanding\n"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        lang = context.args[0]
        text = " ".join(context.args[1:])
        response = client.models.generate_content(
            model='gemini-3.8-flash', 
            contents=f"Translate into {lang}: {text}"
        )
        await update.message.reply_text(f"🌐 **Translation ({lang}):**\n{response.text}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("Usage: `/tr [language] [text]`", parse_mode="Markdown")

async def ged_assistant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subject = context.args[0]
        question = " ".join(context.args[1:])
        prompt = f"You are an expert GED tutor specializing in {subject}. Explain this clearly with step-by-step guidance for the user: {question}"
        response = client.models.generate_content(
            model='gemini-3.8-flash', 
            contents=prompt
        )
        await update.message.reply_text(f"📚 **GED Tutor ({subject}):**\n{response.text}", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("Usage: `/ged [Math/Science/RLA/Social] [Question]`", parse_mode="Markdown")

# --- MAIN TEXT MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    save_chat(user_id, "User", user_message)

    if "မှတ်ထား" in user_message or "save note" in user_message.lower():
        save_memory(user_id, "Note", user_message)
        await update.message.reply_text("Sir, I have securely recorded that into your long-term memory.")
        return

    user_memories = get_memories(user_id)
    
    system_instruction = f"""
    You are JINX, a sleek, highly efficient, and witty personal AI assistant running on mobile.
    User's saved long-term notes & memories: {user_memories}
    Keep responses concise, clear, and optimized for mobile reading.
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=f"{system_instruction}\n\nUser: {user_message}",
        )
        reply_text = response.text
    except Exception as e:
        reply_text = f"Sir, system hiccup: {str(e)}"

    save_chat(user_id, "JINX", reply_text)
    await update.message.reply_text(reply_text)

# --- PHOTO HANDLER (Image Understanding) ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_path = "temp_image.jpg"
    await photo_file.download_to_drive(photo_path)
    
    caption = update.message.caption or "Analyze this image and explain what's in it, Sir."

    try:
        sample_file = client.files.upload(file=photo_path)
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[sample_file, caption]
        )
        await update.message.reply_text(f"🖼 **Image Analysis:**\n{response.text}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Sir, I couldn't process the image: {str(e)}")
    finally:
        if os.path.exists(photo_path):
            os.remove(photo_path)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("tr", translate_command))
    app.add_handler(CommandHandler("ged", ged_assistant_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("JINX Mobile Edition is active, Sir...")
    app.run_polling()