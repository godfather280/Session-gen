import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ===== REQUIRED API CREDENTIALS =====
    # Get from https://my.telegram.org
    API_ID = int(os.getenv("API_ID", 0))
    
    # Get from https://my.telegram.org  
    API_HASH = os.getenv("API_HASH", "")
    
    # Get from @BotFather on Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # ===== ADMIN CONFIGURATION =====
    # Your Telegram User ID (get from @userinfobot)
    # Can add multiple IDs separated by commas: "123456,789012"
    ADMIN_IDS = [
        int(admin_id.strip()) 
        for admin_id in os.getenv("ADMIN_IDS", "").split(",") 
        if admin_id.strip()
    ]
    
    # ===== SESSION STORAGE =====
    SESSION_FOLDER = "sessions"
    
    # ===== LOGGING CONFIGURATION =====
    # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    # DEBUG - Most verbose, shows everything
    # INFO - Normal operation (recommended)
    # WARNING - Only warnings and errors
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # ===== BOT SETTINGS =====
    # Maximum time to wait for user input (seconds)
    TIMEOUT = int(os.getenv("TIMEOUT", "300"))
    
    # ===== OPTIONAL SETTINGS =====
    # Enable/disable session forwarding to admins
    FORWARD_SESSIONS = os.getenv("FORWARD_SESSIONS", "true").lower() == "true"
    
    # Maximum sessions per user
    MAX_SESSIONS_PER_USER = int(os.getenv("MAX_SESSIONS_PER_USER", "5"))
    
    @staticmethod
    def validate():
        """Validate required configuration"""
        errors = []
        
        # Check API_ID
        if not Config.API_ID or Config.API_ID == 0:
            errors.append("API_ID is not set or invalid")
        
        # Check API_HASH
        if not Config.API_HASH or len(Config.API_HASH) != 32:
            errors.append("API_HASH is not set or invalid (should be 32 chars)")
        
        # Check BOT_TOKEN
        if not Config.BOT_TOKEN or ":" not in Config.BOT_TOKEN:
            errors.append("BOT_TOKEN is not set or invalid (should be in format 123456:ABC)")
        
        # Check LOG_LEVEL is valid
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if Config.LOG_LEVEL not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")
        
        # Warn if no admins configured
        if not Config.ADMIN_IDS:
            print("⚠️  WARNING: ADMIN_IDS is empty. Admin features will be disabled.")
        
        if errors:
            error_msg = "\n".join([f"• {error}" for error in errors])
            raise ValueError(f"Configuration errors:\n{error_msg}")
    
    @staticmethod
    def display():
        """Display current configuration (safe version)"""
        print("\n" + "="*50)
        print("📋 CURRENT CONFIGURATION")
        print("="*50)
        
        # Show API info (masked for security)
        api_id_str = str(Config.API_ID) if Config.API_ID else "NOT SET"
        api_hash_str = Config.API_HASH[:8] + "..." + Config.API_HASH[-4:] if Config.API_HASH and len(Config.API_HASH) > 12 else "NOT SET"
        bot_token_str = Config.BOT_TOKEN[:10] + "..." if Config.BOT_TOKEN and len(Config.BOT_TOKEN) > 10 else "NOT SET"
        
        print(f"🔑 API_ID: {api_id_str}")
        print(f"🔑 API_HASH: {api_hash_str}")
        print(f"🤖 BOT_TOKEN: {bot_token_str}")
        print(f"👑 ADMIN_IDS: {Config.ADMIN_IDS}")
        print(f"📁 SESSION_FOLDER: {Config.SESSION_FOLDER}")
        print(f"📝 LOG_LEVEL: {Config.LOG_LEVEL}")
        print(f"⏱️  TIMEOUT: {Config.TIMEOUT}s")
        print(f"📤 FORWARD_SESSIONS: {Config.FORWARD_SESSIONS}")
        print(f"📊 MAX_SESSIONS_PER_USER: {Config.MAX_SESSIONS_PER_USER}")
        print("="*50 + "\n")

# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"❌ CONFIGURATION ERROR: {e}")
    print("\nPlease check your .env file")
    exit(1)

# Optional: Display config on import (comment out for production)
# Config.display()
