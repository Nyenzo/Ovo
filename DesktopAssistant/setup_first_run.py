import os
import tkinter as tk
from tkinter import messagebox, simpledialog
from pathlib import Path

def create_env_file():
    """Create .env file with user-provided API keys"""
    env_content = []
    
    # Weather API Key
    weather_key = simpledialog.askstring("Setup", 
        "Enter your WeatherAPI key (optional - get free key from weatherapi.com):\n\n" +
        "Leave blank to skip weather features.", 
        show='*')
    if weather_key:
        env_content.append(f"WEATHER_API_KEY={weather_key}")
    else:
        env_content.append("WEATHER_API_KEY=")
    
    # News API Key
    news_key = simpledialog.askstring("Setup", 
        "Enter your NewsAPI key (optional - get free key from newsapi.org):\n\n" +
        "Leave blank to skip news features.", 
        show='*')
    if news_key:
        env_content.append(f"NEWS_API_KEY={news_key}")
    else:
        env_content.append("NEWS_API_KEY=")
    
    # Email settings (optional)
    email_user = simpledialog.askstring("Setup", 
        "Enter your Gmail address (optional - for email features):\n\n" +
        "Leave blank to skip email features.")
    if email_user:
        env_content.append(f"EMAIL_USER={email_user}")
        email_pass = simpledialog.askstring("Setup", 
            "Enter your Gmail app password (not regular password):\n\n" +
            "Get this from Google Account > Security > 2-Step Verification > App passwords", 
            show='*')
        if email_pass:
            env_content.append(f"EMAIL_PASS={email_pass}")
        else:
            env_content.append("EMAIL_PASS=")
    else:
        env_content.append("EMAIL_USER=")
        env_content.append("EMAIL_PASS=")
    
    # Voice recognition mode
    recognition_mode = simpledialog.askstring("Setup", 
        "Voice recognition mode:\n\n" +
        "Enter 'offline' for local recognition (recommended)\n" +
        "Enter 'cloud' for Google Cloud recognition\n\n" +
        "Default: offline", 
        initialvalue="offline")
    env_content.append(f"RECOGNITION_MODE={recognition_mode or 'offline'}")
    
    # Write .env file
    with open('.env', 'w') as f:
        f.write('\n'.join(env_content))
    
    messagebox.showinfo("Setup Complete", 
        "Configuration saved!\n\n" +
        "Ovo is ready to use. You can edit the .env file anytime to change settings.")

def check_first_run():
    """Check if this is the first run and setup if needed"""
    if not os.path.exists('.env'):
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        result = messagebox.askyesno("Welcome to Ovo!", 
            "Welcome to Ovo - Your AI Assistant!\n\n" +
            "This appears to be your first run. Would you like to configure API keys for enhanced features?\n\n" +
            "• Weather API (free) - Get weather information\n" +
            "• News API (free) - Get latest news\n" +
            "• Gmail (optional) - Send emails\n\n" +
            "You can skip this and configure later by editing the .env file.")
        
        if result:
            create_env_file()
        else:
            # Create minimal .env file
            with open('.env', 'w') as f:
                f.write("WEATHER_API_KEY=\nNEWS_API_KEY=\nEMAIL_USER=\nEMAIL_PASS=\nRECOGNITION_MODE=offline")
        
        root.destroy()

if __name__ == "__main__":
    check_first_run() 