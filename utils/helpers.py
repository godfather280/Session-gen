# utils/helpers.py

def safe_int(value, default=0):
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def split_message(text, max_length=4000):
    """Split long text into chunks"""
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

# Remove the create_back_keyboard function entirely
