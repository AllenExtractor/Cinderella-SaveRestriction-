# Copyright (c) 2025 devgagan : https://github.com/devgaganin.
# Licensed under the GNU General Public License v3.0.
# See LICENSE file in the repository root for full license text.

import secrets
import aiohttp
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from shared_client import app
from config import VPLINK_API, BOT_USERNAME, TOKEN_VALIDITY_HOURS
from utils.func import (
    save_token,
    verify_token,
    is_premium_user,
    users_collection
)
from plugins.start import subscribe


# ── /token command ──────────────────────────────────────────────────────────────
@app.on_message(filters.command("token") & filters.private)
async def send_token_link(client, message):
    """User /token bheje → VPLink se shortened URL do"""
    join = await subscribe(client, message)
    if join == 1:
        return

    uid = message.from_user.id

    # Premium users ko token ki zaroorat nahi
    if await is_premium_user(uid):
        await message.reply_text(
            "✅ **Aap already Premium Member ho!**\n"
            "Token ki koi zaroorat nahi. Seedha use karo bot ko."
        )
        return

    # Unique token generate karo
    token = secrets.token_urlsafe(16)

    # Token DB mein save karo (unverified)
    await save_token(uid, token)

    # Deep link banao: t.me/BOT?start=token_VALUE
    deep_link = f"https://t.me/{BOT_USERNAME}?start=token_{token}"

    # VPLink se shorten karo
    short_url = await shorten_vplink(deep_link)
    if not short_url:
        await message.reply_text(
            "❌ Link generate karne mein error aayi. Thodi der baad try karo."
        )
        return

    validity_text = f"{TOKEN_VALIDITY_HOURS} ghante"

    await message.reply_text(
        f"🎟️ **Free Access Token**\n\n"
        f"Niche diye link pe click karo, ek chhota sa ad dekho aur "
        f"**{validity_text}** ka free access pao!\n\n"
        f"🔗 **Link:** {short_url}\n\n"
        f"⚠️ _Ek token sirf ek baar use ho sakta hai._\n"
        f"💎 Unlimited access ke liye /pay se premium lo.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Token Lene Ke Liye Click Karo", url=short_url)],
            [InlineKeyboardButton("💎 Premium Lo", callback_data="see_plan")]
        ]),
        disable_web_page_preview=True
    )


async def shorten_vplink(long_url: str) -> str | None:
    """VPLink API se URL shorten karo"""
    api_url = f"https://vplink.in/api?api={VPLINK_API}&url={long_url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if data.get("status") == "success":
                    return data.get("shortenedUrl") or data.get("short_url")
    except Exception as e:
        print(f"VPLink error: {e}")
    return None


# ── Start handler with token deep-link ─────────────────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def start_with_token(client, message):
    """
    /start ke saath token_ prefix aaye to verify karo.
    Normal /start premium.py mein handle hota hai — yahan sirf token wala case.
    """
    args = message.command
    if len(args) < 2 or not args[1].startswith("token_"):
        # Normal start — premium.py ka start_handler chalega
        return

    uid = message.from_user.id
    token_value = args[1][len("token_"):]  # "token_" ke baad ka hissa

    success, msg = await verify_token(uid, token_value)

    if success:
        expiry = datetime.now() + timedelta(hours=TOKEN_VALIDITY_HOURS)
        expiry_str = (expiry + timedelta(hours=5, minutes=30)).strftime('%d-%b-%Y %I:%M %p')
        await message.reply_text(
            f"✅ **Token Verified!**\n\n"
            f"🎉 {TOKEN_VALIDITY_HOURS} ghante ka free access mil gaya!\n"
            f"⏰ **Valid Till:** {expiry_str} (IST)\n\n"
            f"Ab bot use karo. Dobara access ke liye /token command use karo.\n"
            f"💎 Unlimited ke liye /pay se premium lo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Premium Lo", callback_data="see_plan")]
            ])
        )
    else:
        await message.reply_text(
            f"❌ **Token Invalid ya Expire Ho Gaya**\n\n"
            f"{msg}\n\n"
            f"Naya token lene ke liye /token command use karo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎟️ Naya Token Lo", callback_data="get_token")],
                [InlineKeyboardButton("💎 Premium Lo", callback_data="see_plan")]
            ])
        )


@app.on_callback_query(filters.regex("get_token"))
async def cb_get_token(client, callback_query):
    await callback_query.answer()
    await send_token_link(client, callback_query.message)
