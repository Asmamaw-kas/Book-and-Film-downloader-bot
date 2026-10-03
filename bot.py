"""
YoungMovies Premium Access Control Bot
Features:
  - Welcome video preview with Continue button
  - Two subscription plans: Basic (499 birr) & VIP (999 birr)
  - Payment via Telebirr / CBE with copyable account numbers
  - "I Paid" button → sends private channel join link to user
  - Notifies admin with username + Telegram ID + plan chosen
  - Admin approves the user from the private channel
"""

import os
import sqlite3
import logging
from datetime import datetime

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
load_dotenv()

BOT_TOKEN           = os.getenv("BOT_TOKEN")
ADMIN_ID            = int(os.getenv("ADMIN_ID", "0"))

TELEBIRR_NAME       = os.getenv("TELEBIRR_NAME", "Account Holder")
TELEBIRR_ACCOUNT    = os.getenv("TELEBIRR_ACCOUNT", "0912345678")
CBE_NAME            = os.getenv("CBE_NAME", "Account Holder")
CBE_ACCOUNT         = os.getenv("CBE_ACCOUNT", "1000000000000")

BASIC_CHANNEL_LINK  = os.getenv("BASIC_CHANNEL_LINK", "https://t.me/+XXXXXXXXXXXXXXXXXX")
VIP_CHANNEL_LINK    = os.getenv("VIP_CHANNEL_LINK",   "https://t.me/+YYYYYYYYYYYYYYYYYY")

WELCOME_VIDEO_FILE_ID = os.getenv("WELCOME_VIDEO_FILE_ID", "")   # set after first upload

DB_PATH             = os.getenv("DB_PATH", "bot.sqlite3")

BASIC_PRICE         = 499
VIP_PRICE           = 999

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            username    TEXT,
            full_name   TEXT,
            plan        TEXT NOT NULL,          -- 'basic' or 'vip'
            status      TEXT NOT NULL DEFAULT 'pending',  -- pending / approved
            created_at  TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()


def save_payment(user_id: int, username: str, full_name: str, plan: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # upsert: update plan if user already exists with pending status
    cur.execute("""
        INSERT INTO payments (user_id, username, full_name, plan, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
    """, (user_id, username or "", full_name or "", plan, datetime.utcnow().isoformat()))
    con.commit()
    con.close()


def get_pending_payment(user_id: int):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT id, plan, status FROM payments
        WHERE user_id = ? AND status = 'pending'
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    con.close()
    return row   # (id, plan, status) or None


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def get_user_display(user) -> str:
    name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
    uname = f"@{user.username}" if user.username else "no username"
    return f"{name.strip()} ({uname})"


def channel_link_for_plan(plan: str) -> str:
    return BASIC_CHANNEL_LINK if plan == "basic" else VIP_CHANNEL_LINK


# ──────────────────────────────────────────────
# /start  — welcome video + Continue button
# ──────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log.info("User %s started the bot", user.id)

    kb = [[InlineKeyboardButton("▶️ Continue", callback_data="show_plans")]]
    markup = InlineKeyboardMarkup(kb)

    caption = (
        "🎬 *ወደ YoungMovies እንኳን በደህና መጡ!*\n\n"
        "በጣም አሪፍ ወጣት ፊልሞች እና ልዩ የፍቅር ቤት።\n\n"
        "ከላይ ያለውን አጭር እይታ ይመልከቱ, ከዛ 500 በላይ የሃበሻ እና የውጭ ለማግኘት *Continue* ይጫኑ! 👇"
    )

    if WELCOME_VIDEO_FILE_ID:
        await update.message.reply_video(
            video=WELCOME_VIDEO_FILE_ID,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=markup,
        )
    else:
        # Fallback: no video uploaded yet — just send text
        await update.message.reply_text(
            "🎬 *ወደ YoungMovies እንኳን በደህና መጡ!*\n\n"
            "በጣም አሪፍ ወጣት ፊልሞች እና ልዩ የፍቅር ቤት።\n\n"
            "ከላይ ያለውን አጭር እይታ ይመልከቱ, ከዛ 500 በላይ የሃበሻ እና የውጭ ለማግኘት *Continue* ይጫኑ! 👇",
            parse_mode="Markdown",
            reply_markup=markup,
        )


# ──────────────────────────────────────────────
# Show Plans
# ──────────────────────────────────────────────
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "🌟 *Choose Your Premium Plan*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔵 *BASIC — 499 Birr*\n"
        "  ✅ ልዩ ወጣት ፊልሞች\n"
        "  ✅ አዲስ ቪዲዎ በየጊዜው ይጨመራል\n\n"
        "  ✅ ለአባላት ብቻ የሆነ ልዩ ቻናል\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 *VIP — 999 Birr*\n"
        "  ✅ BASIC ሁሉንም ነገር\n"
        "  ✅ ልዩ የቪአይፒ ብቻ ፕሪሚየም ቪዲዮዎች\n"
        "  ✅ 🔥 Dating  App — chat, የፈለጉትን ማውራት & መገናኘት\n"
        "  ✅ Priority support\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "ከታች ያለውን ዕቅድ ይምረጡና ክፍያ ይቀጥሉ እንደከፈሉ ወዲያውኑ ይቀላቀላሉ 👇"
    )

    kb = [
        [
            InlineKeyboardButton("🔵 Basic — 499 Birr", callback_data="plan_basic"),
            InlineKeyboardButton("👑 VIP — 999 Birr",   callback_data="plan_vip"),
        ]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


# ──────────────────────────────────────────────
# Plan selected → show payment details
# ──────────────────────────────────────────────
async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan  = "basic" if query.data == "plan_basic" else "vip"
    price = BASIC_PRICE if plan == "basic" else VIP_PRICE
    label = "🔵 Basic" if plan == "basic" else "👑 VIP"

    # Store chosen plan in user_data for the "I Paid" step
    context.user_data["pending_plan"] = plan

    text = (
        f"💳 *Payment — {label} Plan ({price} Birr)*\n\n"
        f"በትክክል  *{price} Birr* ከታች ካሉ መለያዎች ውስጥ አንዱ ይላኩ፣ ከዚያም ማስተላለፉን ካጠናቀቁ በኋላ *✅ I Paid* ይጫኑ.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📱 *ቴሌብር*\n"
        f"  ስም: `{TELEBIRR_NAME}`\n"
        f"  ቁጥር: `{TELEBIRR_ACCOUNT}`\n\n"
        "🏦 *CBE (Commercial Bank of Ethiopia)*\n"
        f"  ስም: `{CBE_NAME}`\n"
        f"  ቁጥር: `{CBE_ACCOUNT}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 ከላይ ያለ ቁጥር copy ለማድርግ ይጫኑ።\n\n"
        "ከከፈሉ በኋላ ከታች ያለውን ቁልፍ ይጫኑ 👇"
    )

    kb = [
        [InlineKeyboardButton("✅ ክፍያ ጨርሻለሁ", callback_data=f"ipaid_{plan}")],
        [InlineKeyboardButton("⬅️ Back to Plans", callback_data="show_plans")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


# ──────────────────────────────────────────────
# "I Paid" — send join link + notify admin
# ──────────────────────────────────────────────
async def i_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Processing your request…", show_alert=False)

    user  = query.from_user
    plan  = query.data.replace("ipaid_", "")   # 'basic' or 'vip'
    price = BASIC_PRICE if plan == "basic" else VIP_PRICE
    label = "🔵 Basic" if plan == "basic" else "👑 VIP"
    link  = channel_link_for_plan(plan)

    # Save to DB
    save_payment(
        user_id=user.id,
        username=user.username,
        full_name=(user.first_name or "") + (" " + user.last_name if user.last_name else ""),
        plan=plan,
    )

    # ── Tell the user ──────────────────────────────────────────────────────────
    user_msg = (
        f"🎉 *እናመሰግናለን! የክፍያ ጥያቄዎ ተቀብሏል።*\n\n"
        f"*ዕቅድ፡* {label}\n"
        f"*መጠን፡* {price} ብር\n\n"
        f"ወደ ልዩ ቻናሉ ለመቀላቀል ከታች ያለውን link ይጠቀሙ እና *ጥያቄ* ያቅርቡ።\n"
        f"admin ክፍያዎን ካረጋገጡ በኋላ join እና ሙሉ መዳረሻ ያገኛሉ።\n\n"
        f"🔗 *የመቀላቀል link*\n{link}\n\n"
        f"⏳ ጥቂት ደቂቃዎች ይወስዳል። እባክዎን ተገቢውን ትዕግስት ያሳዩ።"
    )
    await query.edit_message_text(user_msg, parse_mode="Markdown")

    # ── Notify admin ───────────────────────────────────────────────────────────
    uname_display = f"@{user.username}" if user.username else "*(no username)*"
    full_name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")

    admin_msg = (
        "🔔 *New Premium Payment Request*\n\n"
        f"👤 *Name:* {full_name.strip()}\n"
        f"🆔 *Telegram ID:* `{user.id}`\n"
        f"✉️ *Username:* {uname_display}\n"
        f"📦 *Plan:* {label} — {price} Birr\n"
        f"🕐 *Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"If payment is confirmed, approve them in the private channel:\n{link}"
    )

    kb_admin = [
        [InlineKeyboardButton("✅ Approved — Notify User", callback_data=f"admin_approve_{user.id}_{plan}")]
    ]

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb_admin),
        )
    except Exception as e:
        log.error("Failed to notify admin: %s", e)


# ──────────────────────────────────────────────
# Admin approves — sends confirmation to user
# ──────────────────────────────────────────────
async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Only the admin can use this
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ You are not authorized.", show_alert=True)
        return

    await query.answer("User notified ✅")

    # Parse callback data: admin_approve_{user_id}_{plan}
    parts   = query.data.split("_")
    # parts = ['admin', 'approve', user_id, plan]
    user_id = int(parts[2])
    plan    = parts[3]
    label   = "🔵 Basic" if plan == "basic" else "👑 VIP"
    link    = channel_link_for_plan(plan)

    # Update admin message
    await query.edit_message_text(
        query.message.text + "\n\n✅ *Approval notification sent to user.*",
        parse_mode="Markdown",
    )

    # Message to user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎊 *Your payment has been confirmed!*\n\n"
                f"*Plan:* {label}\n\n"
                f"You now have full access. Use the link below to join the channel:\n"
                f"🔗 {link}\n\n"
                f"Welcome to YoungMovies Premium! 🎬✨"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        log.error("Could not message user %s: %s", user_id, e)


# ──────────────────────────────────────────────
# /upload_video — helper for admin to get file_id
# ──────────────────────────────────────────────
async def cmd_upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin sends any video as a reply to this command to get its file_id."""
    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.reply_to_message and update.message.reply_to_message.video:
        fid = update.message.reply_to_message.video.file_id
        await update.message.reply_text(
            f"✅ Video file_id:\n`{fid}`\n\nCopy this into your .env as:\n`WELCOME_VIDEO_FILE_ID={fid}`",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "Reply to a video message with /upload_video to get its file_id."
        )


# ──────────────────────────────────────────────
# /stats — admin only
# ──────────────────────────────────────────────
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")
    pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM payments WHERE status='approved'")
    approved = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM payments WHERE plan='basic'")
    basic_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM payments WHERE plan='vip'")
    vip_count = cur.fetchone()[0]
    con.close()

    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"⏳ Pending approvals: *{pending}*\n"
        f"✅ Approved users: *{approved}*\n\n"
        f"🔵 Basic subscribers: *{basic_count}*\n"
        f"👑 VIP subscribers: *{vip_count}*",
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────────
# /pending — list pending payments (admin)
# ──────────────────────────────────────────────
async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT user_id, username, full_name, plan, created_at
        FROM payments WHERE status='pending'
        ORDER BY id DESC LIMIT 20
    """)
    rows = cur.fetchall()
    con.close()

    if not rows:
        await update.message.reply_text("✅ No pending payments.")
        return

    lines = ["⏳ *Pending Payments (latest 20)*\n"]
    for uid, uname, fname, plan, ts in rows:
        uname_str = f"@{uname}" if uname else "—"
        label = "Basic" if plan == "basic" else "VIP"
        lines.append(f"• {fname} | {uname_str} | ID: `{uid}` | {label} | {ts[:16]}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ──────────────────────────────────────────────
# Unhandled messages
# ──────────────────────────────────────────────
async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Use /start to begin or tap a button in the menu.",
    )


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    init_db()
    log.info("Database initialized at %s", DB_PATH)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("upload_video", cmd_upload_video))
    app.add_handler(CommandHandler("stats",        cmd_stats))
    app.add_handler(CommandHandler("pending",      cmd_pending))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(show_plans,    pattern="^show_plans$"))
    app.add_handler(CallbackQueryHandler(plan_selected, pattern="^plan_(basic|vip)$"))
    app.add_handler(CallbackQueryHandler(i_paid,        pattern="^ipaid_(basic|vip)$"))
    app.add_handler(CallbackQueryHandler(admin_approve, pattern="^admin_approve_\\d+_(basic|vip)$"))

    # Fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))

    log.info("Bot is running…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
