from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType

async def handle_groups_in(client: Client, message: Message):
    """List all groups user is in"""
    try:
        groups_text = "**👥 Groups List:**\n\n"
        group_count = 0
        channel_count = 0
        
        async for dialog in client.get_dialogs():
            chat = dialog.chat
            
            if chat.type == ChatType.GROUP:
                groups_text += f"👥 **{chat.title}**\n"
                groups_text += f"   📝 Group\n"
                groups_text += f"   🔢 ID: `{chat.id}`\n"
                if chat.username:
                    groups_text += f"   🔗 @{chat.username}\n"
                
                group_count += 1
                
            elif chat.type == ChatType.SUPERGROUP:
                groups_text += f"🌟 **{chat.title}**\n"
                groups_text += f"   📝 Supergroup\n"
                groups_text += f"   🔢 ID: `{chat.id}`\n"
                if chat.username:
                    groups_text += f"   🔗 @{chat.username}\n"
                
                group_count += 1
                
            elif chat.type == ChatType.CHANNEL:
                channel_count += 1
                # Don't add to main list, we'll show count separately
            
            # Limit to prevent message too long
            if group_count >= 15:
                groups_text += f"\n... and more groups (showing first 15)"
                break
        
        groups_text += f"\n📊 **Summary:**\n"
        groups_text += f"• 👥 Groups/Supergroups: {group_count}\n"
        groups_text += f"• 📢 Channels: {channel_count}\n"
        groups_text += f"• 📱 Total chats: {group_count + channel_count}\n"
        
        if group_count == 0 and channel_count == 0:
            groups_text = "❌ Not in any groups or channels"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Get Group Link", callback_data="get_group_link")],
            [InlineKeyboardButton("👑 Admin Groups", callback_data="admin_in")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
        ])
        
        await message.reply(groups_text, reply_markup=keyboard)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
