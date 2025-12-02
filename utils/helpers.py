import os
import json
from typing import Optional, Dict, Any, List

def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def get_session_info(session_string: str) -> Optional[Dict]:
    """Extract basic info from session string"""
    try:
        # Note: Session strings are encrypted
        return {
            "type": "telegram_session",
            "length": len(session_string)
        }
    except:
        return None

def format_number(number: int) -> str:
    """Format large numbers with commas"""
    return f"{number:,}"

def split_message(text: str, max_length: int = 4000) -> List[str]:
    """Split long text into chunks"""
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

def create_back_keyboard():
    """Create a standard back button keyboard"""
    # Import inside function to avoid circular imports
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
    ]])
