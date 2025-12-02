from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

async def handle_two_factor(client: Client, message: Message):
    try:
        # Check if 2FA is enabled
        result = await client.invoke(
            Raw(functions.account.GetPassword())
        )
        
        has_password = result.has_password
        
        if has_password:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Disable 2FA", callback_data="disable_2fa")
            ]])
            text = "🔐 **2FA Status:** Enabled\n\nClick below to disable 2FA:"
        else:
            text = "🔓 **2FA Status:** Disabled"
            keyboard = None
            
        await message.reply(text, reply_markup=keyboard)
        
    except Exception as e:
        await message.reply(f"❌ Error checking 2FA: {str(e)}")

async def disable_two_factor(client: Client, callback_query):
    from pyrogram.raw import functions
    
    try:
        # First, check current password
        password_info = await client.invoke(
            functions.account.GetPassword()
        )
        
        if not password_info.has_password:
            await callback_query.answer("2FA is already disabled!")
            return
        
        # Ask for password to disable
        await callback_query.message.reply(
            "Please enter your current 2FA password to disable it:\n"
            "Use: `/disable2fa your_password`"
        )
        
    except Exception as e:
        await callback_query.message.reply(f"❌ Error: {str(e)}")
