from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserAdminInvalid

async def show_admin_powers_menu(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Select Group", callback_data="select_group_powers")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ])
    
    await message.reply(
        "**⚡ Admin Powers Panel**\n\n"
        "You can use admin powers in groups where you're admin.\n"
        "Select a group to manage:",
        reply_markup=keyboard
    )

async def show_group_admin_actions(client: Client, chat_id: int, message: Message):
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Ban User", callback_data=f"ban_user_{chat_id}")],
            [InlineKeyboardButton("👤 Mute User", callback_data=f"mute_user_{chat_id}")],
            [InlineKeyboardButton("👤 Unban User", callback_data=f"unban_user_{chat_id}")],
            [InlineKeyboardButton("📢 Pin Message", callback_data=f"pin_message_{chat_id}")],
            [InlineKeyboardButton("📢 Delete Message", callback_data=f"delete_msg_{chat_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_powers")]
        ])
        
        chat = await client.get_chat(chat_id)
        await message.reply(
            f"**⚡ Admin Powers for:** {chat.title}\n"
            f"Select an action:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

async def ban_user(client: Client, chat_id: int, user_id: int, message: Message):
    try:
        await client.ban_chat_member(chat_id, user_id)
        await message.reply(f"✅ User banned successfully!")
    except UserAdminInvalid:
        await message.reply("❌ You don't have permission to ban this user!")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

async def mute_user(client: Client, chat_id: int, user_id: int, message: Message):
    try:
        await client.restrict_chat_member(
            chat_id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
        )
        await message.reply(f"✅ User muted successfully!")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
