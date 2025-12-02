from pyrogram import Client
from pyrogram.types import Message, Dialog
from pyrogram.enums import ChatType

async def handle_chats(client: Client, message: Message):
    try:
        chats_text = "**First 10 Chats:**\n\n"
        count = 0
        
        async for dialog in client.get_dialogs():
            if count >= 10:
                break
                
            if dialog.chat.type in [ChatType.PRIVATE, ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
                chat_type = "👤" if dialog.chat.type == ChatType.PRIVATE else "👥"
                chats_text += f"{chat_type} **{dialog.chat.title or dialog.chat.first_name}**\n"
                chats_text += f"   📝 Type: {dialog.chat.type}\n"
                chats_text += f"   🔢 ID: `{dialog.chat.id}`\n"
                if dialog.chat.username:
                    chats_text += f"   🔗 @{dialog.chat.username}\n"
                chats_text += "━━━━━━━━━━━━━━\n"
                count += 1
        
        if count == 0:
            chats_text = "❌ No chats found!"
            
        await message.reply(chats_text)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
