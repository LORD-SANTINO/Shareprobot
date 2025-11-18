from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from datetime import datetime, timedelta
import asyncio
from config import *
from database import *
from utils import *

app = Client("ContentLockerBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Temporary storage
pending_content = {}
user_state = {}

WELCOME = f"""
🔒 *Ultimate Content Locker Bot* 🔒

Send me *any* file, photo, video, text — I'll lock it!

Features:
🔑 Password Protection
🔗 Force Join @{FORCE_JOIN.lstrip('@')}
👁️ One-Time View (self-destruct)
⏰ Custom Expiry (Premium)
💎 Premium = Refer 10 friends

Every link says: *Made by @daxbots* 🔥

Creator: {CREATOR}
"""

LOCK_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔑 Password Only", callback_data="type_password"),
     InlineKeyboardButton("🔗 Force Join Only", callback_data="type_forcejoin")],
    [InlineKeyboardButton("👁️ One-Time View", callback_data="type_onetime"),
     InlineKeyboardButton("🔒 Password + Force Join", callback_data="type_both")],
    [InlineKeyboardButton("🛡️ All Protections", callback_data="type_all"),
     InlineKeyboardButton("🔓 No Lock (Public)", callback_data="type_none")]
])

@app.on_message(filters.command("start"))
async def start(client, message):
    args = message.text.split()
    user = message.from_user

    add_user(user.id, user.username or user.first_name)

    if len(args) > 1:
        payload = args[1]

        if payload.startswith("ref_"):
            referrer = payload.replace("ref_", "")
            if str(user.id) != referrer:
                c.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (referrer,))
                if c.rowcount > 0:
                    refs = get_user(int(referrer))['referrals'] + 1
                    if refs >= REFERRALS_NEEDED:
                        make_premium(int(referrer))
                        try:
                            await client.send_message(int(referrer), "🎉 Congrats! You are now PREMIUM! All features unlocked forever!")
                        except:
                            pass
                conn.commit()

        elif payload.startswith("lock_"):
            code = payload.replace("lock_", "")
            lock = get_lock_by_code(code)
            if not lock:
                return await message.reply("❌ Link expired or invalid.")

            # Expiry check
            if lock['expiry'] and datetime.now() > lock['expiry']:
                return await message.reply("⏰ This content has expired.")

            # One-time view
            if lock['one_time']:
                delete_lock(code)
                await message.reply("👁️ This was a one-time view link. Content destroyed.")

            # Force Join
            if lock['force_join']:
                try:
                    chat = await client.get_chat(FORCE_JOIN)
                    member = await chat.get_member(user.id)
                    if member.status in ["left", "kicked"]:
                        return await message.reply(
                            f"🔒 You must join {FORCE_JOIN} to unlock!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("Join Channel", url=chat.invite_link or f"https://t.me/{FORCE_JOIN.lstrip('@')}")]
                            ]))
                except:
                    pass

            # Password
            if lock['password']:
                user_state[user.id] = {"waiting_pass": code}
                return await message.reply("🔐 Enter password to unlock:", reply_markup=ForceReply(True))

            # Show content
            await client.copy_message(user.id, lock['user_id'], lock['id' if lock['file_type'] == 'text' else 'message_id'])
            increment_views(lock['id'])
            await message.reply("🔓 Content unlocked!\n\nMade by @daxbots")

    await message.reply(WELCOME, reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("My Referral Link", callback_data="myref")]
    ]))

@app.on_message(filters.private & ~filters.command(["stats", "delete"]))
async def receive_content(client, message):
    if message.media or message.text:
        pending_content[message.from_user.id] = message
        user = get_user(message.from_user.id)
        is_prem = user['is_premium'] if user else False

        text = "🔒 How do you want to protect this content?\n\n"
        if not is_prem:
            text += "⚠️ Free: Only Password or No Lock | Links expire in 2 days\n💎 Get Premium → Refer 10 users!"

        await message.reply(text, reply_markup=LOCK_KEYBOARD)

@app.on_callback_query(filters.regex("^type_"))
async def lock_type(client, cb):
    user_id = cb.from_user.id
    if user_id not in pending_content:
        return await cb.answer("❌ Send content again!", show_alert=True)

    user = get_user(user_id)
    is_premium = user['is_premium']

    choice = cb.data.split("_")[1]

    restricted = ["onetime", "both", "all", "forcejoin"]
    if choice in restricted and not is_premium:
        return await cb.answer("🔒 Premium Feature! Refer 10 users to unlock.", show_alert=True)

    msg = pending_content.pop(user_id)

    file_id = None
    file_type = "text"
    if msg.photo:
        file_id = msg.photo.file_id
        file_type = "photo"
    elif msg.video:
        file_id = msg.video.file_id
        file_type = "video"
    elif msg.document:
        file_id = msg.document.file_id
        file_type = "document"
    elif msg.audio:
        file_id = msg.audio.file_id
        file_type = "audio"
    elif msg.text:
        file_id = msg.text
        file_type = "text"

    # Default settings
    password = ""
    force_join = 0
    one_time = 0
    expiry = datetime.now() + timedelta(days=2)  # default free

    if choice == "password":
        user_state[user_id] = {"stage": "set_pass", "data": {"file_id": file_id, "file_type": file_type}}
        return await cb.message.reply("🔑 Send the password you want:")

    elif choice == "forcejoin":
        force_join = 1
    elif choice == "onetime":
        one_time = 1
        expiry = None if is_premium else datetime.now() + timedelta(days=2)
    elif choice == "both":
        password = "temp"
        force_join = 1
        user_state[user_id] = {"stage": "set_pass_both", "data": {"file_id": file_id, "file_type": file_type}}
        return await cb.message.reply("🔑 Set password for Password + Force Join:")
    elif choice == "all":
        one_time = 1
        force_join = 1
        user_state[user_id] = {"stage": "set_pass_all", "data": {"file_id": file_id, "file_type": file_type}}
        return await cb.message.reply("🔑 Set password for MAX Protection:")
    elif choice == "none":
        expiry = None if is_premium else datetime.now() + timedelta(days=2)

    # Create lock
    code = create_lock(
        user_id=user_id,
        file_id=file_id,
        file_type=file_type,
        password=password,
        force_join=force_join,
        one_time=one_time,
        expiry=expiry if not (is_premium and expiry is None) else None,
        premium=is_premium
    )

    link = generate_share_link(code)
    await cb.message.reply(f"""
🔒 Content Locked Successfully!

Share this link:
{link}

Delete Code: `{code}` (use /delete {code})

Made by @daxbots 🚀
    """, disable_web_page_preview=True)

@app.on_message(filters.regex("^/delete"))
async def delete_cmd(client, message):
    try:
        code = message.text.split()[1]
        lock = get_lock_by_code(code)
        if not lock or lock['user_id'] != message.from_user.id:
            return await message.reply("❌ Invalid or not yours.")
        delete_lock(code)
        await message.reply("🗑️ Link permanently deleted!")
    except:
        await message.reply("Usage: /delete <code>")

@app.on_message(filters.command("stats"))
async def stats(client, message):
    users, prem, locks = get_stats()
    await message.reply(f"""
📊 Bot Stats

👥 Total Users: {users}
💎 Premium Users: {prem}
🔒 Total Locks: {locks}

Made by @daxbots
    """)

@app.on_callback_query(filters.regex("^myref$"))
async def myref(client, cb):
    link = generate_referral_link(cb.from_user.id)
    user = get_user(cb.from_user.id)
    await cb.message.reply(f"""
Your Referral Link:\n{link}\n\nYou have {user['referrals']}/{REFERRALS_NEEDED} referrals")

# Handle password input
@app.on_message(filters.private & filters.text & ~filters.command)
async def handle_text(client, message):
    user_id = message.from_user.id
    if user_id in user_state:
        state = user_state[user_state]

        if state["stage"] in ["set_pass", "set_pass_both", "set_pass_all"]:
            password = message.text
            data = state["data"]
            is_premium = get_user(user_id)['is_premium']

            force_join = 1 if "both" in state["stage"] or "all" in state["stage"] else 0
            one_t = 1 if "all" in state["stage"] else 0

            code = create_lock(
                user_id=user_id,
                file_id=data["file_id"],
                file_type=data["file_type"],
                password=password,
                force_join=force_join,
                one_time=one_t,
                expiry=None if is_premium else datetime.now() + timedelta(days=2),
                premium=is_premium
            )

            link = generate_share_link(code)
            await message.reply(f"""
🔐 Locked with password!

Share: {link}

Delete code: `{code}`

Made by @daxbots
            """)
            del user_state[user_id]

        elif "waiting_pass" in state:
            code = state["waiting_pass"]
            lock = get_lock_by_code(code)
            if lock['password'] == message.text:
                await client.copy_message(user_id, lock['user_id'], lock['id' if lock['file_type']=='text' else 'message_id'])
                await message.reply("✅ Unlocked!\nMade by @daxbots")
                if lock['one_time']:
                    delete_lock(code)
            else:
                await message.reply("❌ Wrong password!")
            del user_state[user_id]

app.run()
