from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType

async def handle_vanish(client: Message, message: Message):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚠️ Confirm Leave All", callback_data="confirm_vanish"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel_vanish")
    ]])
    
    await message.reply(
        "**⚠️ WARNING: Vanish Mode**\n\n"
        "This will make the account leave ALL groups and channels.\n"
        "Are you sure you want to continue?",
        reply_markup=keyboard
    )

async def confirm_vanish(client: Client, callback_query):
    await callback_query.message.edit_text("🚀 Starting to leave groups...")
    
    try:
        left_count = 0
        failed_count = 0
        
        async for dialog in client.get_dialogs():
            chat = dialog.chat
            
            if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
                try:
                    await client.leave_chat(chat.id)
                    left_count += 1
                except Exception:
                    failed_count += 1
                
                # Small delay to avoid flood
                await asyncio.sleep(1)
        
        await callback_query.message.edit_text(
            f"✅ **Vanish Complete!**\n\n"
            f"✅ Left: {left_count} chats\n"
            f"❌ Failed: {failed_count} chats"
        )
        
    except Exception as e:
        await callback_query.message.edit_text(f"❌ Error: {str(e)}")
