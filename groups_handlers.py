from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatType

async def handle_groups_in(client: Client, message: Message):
    try:
        groups_text = "**👥 Groups List:**\n\n"
        count = 0
        
        async for dialog in client.get_dialogs():
            chat = dialog.chat
            
            if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                group_type = "👥 Group" if chat.type == ChatType.GROUP else "🌟 Supergroup"
                groups_text += f"**{chat.title}**\n"
                groups_text += f"   📝 {group_type}\n"
                groups_text += f"   🔢 ID: `{chat.id}`\n"
                if chat.username:
                    groups_text += f"   🔗 @{chat.username}\n"
                
                # Get member count
                try:
                    chat_info = await client.get_chat(chat.id)
                    groups_text += f"   👤 Members: {chat_info.members_count}\n"
                except:
                    pass
                
                groups_text += "━━━━━━━━━━━━━━\n"
                count += 1
        
        if count == 0:
            groups_text = "❌ Not in any groups"
        
        # Split if too long
        if len(groups_text) > 4000:
            for i in range(0, len(groups_text), 4000):
                await message.reply(groups_text[i:i+4000])
        else:
            await message.reply(groups_text)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
