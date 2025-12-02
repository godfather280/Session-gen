import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API credentials (REQUIRED)
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Admin configuration
    ADMIN_IDS = [
        int(admin_id.strip()) 
        for admin_id in os.getenv("ADMIN_IDS", "").split(",") 
        if admin_id.strip()
    ]
    
    # Session storage
    SESSION_FOLDER = "sessions"
    
    # Logging - ADD THIS LINE
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @staticmethod
    def validate():
        """Validate required configuration"""
        errors = []
        
        if not Config.API_ID:
            errors.append("API_ID is not set")
        
        if not Config.API_HASH:
            errors.append("API_HASH is not set")
        
        if not Config.BOT_TOKEN:
            errors.append("BOT_TOKEN is not set")
        
        if not Config.ADMIN_IDS:
            print("⚠️  Warning: ADMIN_IDS is empty. Admin features will be disabled.")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
