from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChatAdminRequired

async def handle_get_group_link(client: Client, message: Message):
    await message.reply(
        "**🔗 Get Group Link**\n\n"
        "Please send the Group ID or Group Username to get the invite link.\n\n"
        "Format: `/get_group_link group_id`\n"
        "Example: `/get_group_link -1001234567890`"
    )

async def get_invite_link(client: Client, message: Message, chat_id: int):
    try:
        # Check if user is in the group
        try:
            await client.get_chat_member(chat_id, "me")
        except:
            await message.reply("❌ Account is not in this group!")
            return
        
        # Get or create invite link
        try:
            # Try to get existing links first
            links = await client.get_chat_invite_links(chat_id, limit=1)
            if links:
                invite_link = links[0].invite_link
            else:
                # Create new invite link
                invite = await client.create_chat_invite_link(
                    chat_id,
                    name="Admin Panel Link"
                )
                invite_link = invite.invite_link
                
            await message.reply(
                f"**🔗 Invite Link:**\n{invite_link}\n\n"
                f"**Note:** This link may expire or be revoked."
            )
            
        except ChatAdminRequired:
            await message.reply("❌ Need admin rights to create invite link!")
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
