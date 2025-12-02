from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

async def show_admin_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 2FA Status", callback_data="2fa_status")],
        [InlineKeyboardButton("💬 First 10 Chats", callback_data="get_chats")],
        [InlineKeyboardButton("👻 Vanish from Groups", callback_data="vanish")],
        [InlineKeyboardButton("👑 Admin in Groups", callback_data="admin_in")],
        [InlineKeyboardButton("⚡ Admin Powers", callback_data="admin_powers")],
        [InlineKeyboardButton("👥 All Groups", callback_data="groups_in")],
        [InlineKeyboardButton("🔗 Get Group Link", callback_data="get_group_link")]
    ])
    
    await message.reply(
        "**Admin Panel**\n\n"
        "Select an option:",
        reply_markup=keyboard
    )
