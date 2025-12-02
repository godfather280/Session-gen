from pyrogram import Client
from pyrogram.types import Message, ChatMember

async def handle_admin_in(client: Client, message: Message):
    try:
        admin_chats = "**👑 Admin in Groups/Channels:**\n\n"
        count = 0
        
        async for dialog in client.get_dialogs():
            chat = dialog.chat
            
            # Skip private chats
            if chat.type not in ["group", "supergroup", "channel"]:
                continue
            
            try:
                # Get chat member info
                member = await client.get_chat_member(chat.id, "me")
                
                if member.status in ["creator", "administrator"]:
                    chat_type = "📢" if chat.type == "channel" else "👥"
                    admin_chats += f"{chat_type} **{chat.title}**\n"
                    admin_chats += f"   🔢 ID: `{chat.id}`\n"
                    
                    if member.status == "creator":
                        admin_chats += f"   👑 Owner\n"
                    else:
                        admin_chats += f"   ⚡ Admin\n"
                    
                    if chat.username:
                        admin_chats += f"   🔗 @{chat.username}\n"
                    
                    admin_chats += "━━━━━━━━━━━━━━\n"
                    count += 1
                    
            except Exception:
                continue
        
        if count == 0:
            admin_chats = "❌ Not admin in any groups/channels"
        
        # Split if too long
        if len(admin_chats) > 4000:
            for i in range(0, len(admin_chats), 4000):
                await message.reply(admin_chats[i:i+4000])
        else:
            await message.reply(admin_chats)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
