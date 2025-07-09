import re
import webbrowser
import smtplib
import subprocess
import logging
import asyncio
import pyttsx3
# import speech_recognition as sr  # Removed for Vosk compatibility
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import os
import requests
import json
from vosk import Model, KaldiRecognizer
import pyaudio

# Google Cloud Speech-to-Text fallback
from google.cloud import speech
import io
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import pystray
from PIL import Image, ImageDraw
import difflib
import tkinter.ttk as ttk
import queue

# Configure logging for debugging and monitoring
logging.basicConfig(filename='assistant.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables for secure credential management
load_dotenv()
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# Recognition mode: 'offline' (Vosk) or 'cloud' (Google, etc.)
RECOGNITION_MODE = os.getenv('RECOGNITION_MODE', 'offline')

# Load Vosk model (download if not present)
VOSK_MODEL_PATH = os.getenv('VOSK_MODEL_PATH', 'vosk-model-small-en-us-0.15')
if RECOGNITION_MODE == 'offline':
    if not Path(VOSK_MODEL_PATH).exists():
        speak(f"Vosk model not found at {VOSK_MODEL_PATH}. Please download and extract the model.")
        logging.error(f"Vosk model not found at {VOSK_MODEL_PATH}")
        exit(1)
    vosk_model = Model(VOSK_MODEL_PATH)

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speed of speech
engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)

# Thread-safe TTS queue and worker
_tts_queue = queue.Queue()

def _tts_worker():
    while True:
        text = _tts_queue.get()
        if text is None:
            break
        engine.say(text)
        engine.runAndWait()
        _tts_queue.task_done()

_tts_thread = threading.Thread(target=_tts_worker, daemon=True)
_tts_thread.start()

def speak(text):
    logging.info(f"Speaking: {text}")
    _tts_queue.put(text)

# Dictionary to store reminders
reminders = {}

# Listen for voice commands using Vosk (offline) or cloud fallback
async def listen():
    if RECOGNITION_MODE == 'offline':
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
            stream.start_stream()
            print('Listening (offline)...')
            rec = KaldiRecognizer(vosk_model, 16000)
            audio_data = b''
            max_seconds = 5
            chunk_size = 4000
            num_chunks = int(16000 / chunk_size * max_seconds)
            for _ in range(num_chunks):
                data = stream.read(chunk_size, exception_on_overflow=False)
                audio_data += data
                if rec.AcceptWaveform(data):
                    break
            result = json.loads(rec.FinalResult())
            command = result.get('text', '').lower()
            logging.info(f"Recognized (offline): {command}")
            print(f"You said: {command}")
            stream.stop_stream()
            stream.close()
            p.terminate()
            if command:
                return command
            else:
                speak("Sorry, I couldn't understand that (offline mode). Trying cloud...")
                logging.warning("Vosk did not recognize speech, falling back to cloud.")
                return await listen_cloud()
        except Exception as e:
            speak("Error with offline recognition. Trying cloud...")
            logging.error(f"Vosk error: {e}")
            return await listen_cloud()
    else:
        return await listen_cloud()

# Placeholder for cloud-based recognition (to be implemented)
async def listen_cloud():
    try:
        speak("Listening (cloud mode)...")
        # Record audio from microphone (5 seconds)
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
        stream.start_stream()
        frames = []
        seconds = 5
        for _ in range(0, int(16000 / 8000 * seconds)):
            data = stream.read(8000, exception_on_overflow=False)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        p.terminate()
        audio_data = b''.join(frames)

        # Google Cloud Speech client
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        response = client.recognize(config=config, audio=audio)
        command = ''
        for result in response.results:
            command += result.alternatives[0].transcript.lower() + ' '
        command = command.strip()
        logging.info(f"Recognized (cloud): {command}")
        print(f"You said (cloud): {command}")
        if command:
            return command
        else:
            speak("Sorry, I couldn't understand that (cloud mode) either.")
            logging.warning("Cloud recognition did not recognize speech.")
            return ""
        except Exception as e:
        speak("Cloud recognition failed.")
        logging.error(f"Cloud recognition error: {e}")
            return ""

# Google Cloud Setup Instructions (add to README):
# 1. Go to https://console.cloud.google.com/ and create a project.
# 2. Enable the Speech-to-Text API for your project.
# 3. Create a service account and download the JSON key file.
# 4. Set the environment variable GOOGLE_APPLICATION_CREDENTIALS to the path of your JSON key.
#    (e.g., in .env: GOOGLE_APPLICATION_CREDENTIALS=path/to/your-key.json)
# ---

# Open a website based on the provided domain
def open_website(command):
    match = re.search(r'open website (.+)', command)
    if match:
        domain = match.group(1).replace(' ', '')
        url = f"https://www.{domain}"
        webbrowser.open(url)
        speak(f"Opening {domain}")
        logging.info(f"Opened website: {url}")
    else:
        speak("Please specify a website to open.")

# Open a subreddit on Reddit
def open_reddit(command):
    match = re.search(r'open reddit (.*)', command)
    url = 'https://www.reddit.com/'
    if match:
        subreddit = match.group(1).replace(' ', '')
        url += f'r/{subreddit}'
    webbrowser.open(url)
    speak(f"Opening Reddit {'subreddit ' + subreddit if match else ''}")
    logging.info(f"Opened Reddit: {url}")

# Fetch and tell a joke from the icanhazdadjoke API
def tell_joke():
    try:
        response = requests.get('https://icanhazdadjoke.com/', headers={"Accept": "application/json"})
        if response.status_code == 200:
            joke = response.json()['joke']
            speak(joke)
            logging.info(f"Told joke: {joke}")
        else:
            speak("Sorry, I couldn't fetch a joke.")
            logging.warning("Failed to fetch joke")
    except Exception as e:
        speak("Error fetching joke.")
        logging.error(f"Joke fetch error: {e}")

# Get current weather for a city using WeatherAPI
def get_weather(command):
    match = re.search(r'current weather in (.*)', command)
    if match:
        city = match.group(1)
        try:
            url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}&aqi=no"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                temp = data['current']['temp_c']
                status = data['current']['condition']['text']
                city_name = data['location']['name']
                speak(f"The current weather in {city_name} is {status} with a temperature of {temp:.1f} degrees Celsius.")
                logging.info(f"Weather for {city_name}: {status}, {temp}°C")
            else:
                speak(f"Sorry, I couldn't fetch the weather for {city}.")
                logging.warning(f"Weather API error: {response.status_code}")
        except Exception as e:
            speak(f"Sorry, I couldn't fetch the weather for {city}.")
            logging.error(f"Weather fetch error: {e}")
    else:
        speak("Please specify a city for the weather.")

# Get weather forecast for a city using WeatherAPI
def get_forecast(command):
    match = re.search(r'weather forecast in (.*)', command)
    if match:
        city = match.group(1)
        try:
            url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days=3&aqi=no&alerts=no"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                city_name = data['location']['name']
                for day in data['forecast']['forecastday'][:3]:  # Next 3 days
                    date = day['date']
                    temp_max = day['day']['maxtemp_c']
                    temp_min = day['day']['mintemp_c']
                    status = day['day']['condition']['text']
                    speak(f"On {date}, {city_name} will have {status}. The high will be {temp_max:.1f} degrees Celsius, and the low will be {temp_min:.1f} degrees Celsius.")
                    logging.info(f"Forecast for {city_name} on {date}: {status}, {temp_max}°C/{temp_min}°C")
            else:
                speak(f"Sorry, I couldn't fetch the forecast for {city}.")
                logging.warning(f"Forecast API error: {response.status_code}")
        except Exception as e:
            speak(f"Sorry, I couldn't fetch the forecast for {city}.")
            logging.error(f"Forecast fetch error: {e}")
    else:
        speak("Please specify a city for the forecast.")

# Send an email using Gmail SMTP
def send_email(command):
    try:
        speak("Who is the recipient?")
        recipient = asyncio.run(listen())
        if 'john' in recipient.lower():
            speak("What should I say?")
            content = asyncio.run(listen())
            mail = smtplib.SMTP('smtp.gmail.com', 587)
            mail.ehlo()
            mail.starttls()
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.sendmail(EMAIL_USER, 'recipient@example.com', content)  # Update recipient email
            mail.close()
            speak("Email sent.")
            logging.info("Email sent successfully")
        else:
            speak("I only know how to send emails to John.")
    except Exception as e:
        speak("Failed to send email.")
        logging.error(f"Email error: {e}")

# Open a desktop application
def open_app(command):
    match = re.search(r'open (notepad|calculator|app (.+))', command)
    if match:
        app = match.group(1).replace('app ', '') if match.group(2) else match.group(1)
        try:
            if app == 'notepad':
                subprocess.run(['notepad'] if os.name == 'nt' else ['gedit'])
            elif app == 'calculator':
                subprocess.run(['calc'] if os.name == 'nt' else ['gnome-calculator'])
            else:
                speak(f"Sorry, I don't know how to open {app}.")
                return
            speak(f"Opening {app}")
            logging.info(f"Opened application: {app}")
        except Exception as e:
            speak(f"Failed to open {app}.")
            logging.error(f"App open error: {e}")
    else:
        speak("Please specify an application to open.")

# Fetch top news headlines using NewsAPI
def get_news():
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            articles = response.json()['articles'][:3]
            for i, article in enumerate(articles, 1):
                speak(f"News {i}: {article['title']}")
                logging.info(f"News: {article['title']}")
        else:
            speak("Sorry, I couldn't fetch the news.")
            logging.warning("Failed to fetch news")
    except Exception as e:
        speak("Error fetching news.")
        logging.error(f"News fetch error: {e}")

# Set a reminder with a specified time
def set_reminder(command):
    match = re.search(r'set reminder (.*) in (\d+) minutes', command)
    if match:
        reminder_text = match.group(1)
        minutes = int(match.group(2))
        remind_time = datetime.now() + timedelta(minutes=minutes)
        reminders[remind_time] = reminder_text
        speak(f"Reminder set for {reminder_text} at {remind_time.strftime('%H:%M')}.")
        logging.info(f"Reminder set: {reminder_text} at {remind_time}")
    else:
        speak("Please specify a reminder and time in minutes.")

# Check and announce reminders
async def check_reminders():
    while True:
        now = datetime.now()
        for remind_time in list(reminders.keys()):
            if now >= remind_time:
                speak(f"Reminder: {reminders[remind_time]}")
                logging.info(f"Reminder triggered: {reminders[remind_time]}")
                del reminders[remind_time]
        await asyncio.sleep(60)  # Check every minute

# --- Flexible weather command matching ---
def match_command(command):
    command = command.lower()
    # Weather
    if "weather" in command:
        # Try to extract city after 'in'
        import re
        match = re.search(r'weather(?: in)? ([a-zA-Z ]+)', command)
        if match:
            city = match.group(1).strip()
            return lambda c: get_weather(f"current weather in {city}")
        elif "in" in command:
            # fallback: ask for city
            return lambda c: speak("Please specify a city for the weather.")
        else:
            return lambda c: speak("Please specify a city for the weather.")
    # News
    if any(kw in command for kw in ["news", "headlines"]):
        return lambda c: get_news()
    # Reminders
    if any(kw in command for kw in ["remind", "reminder"]):
        return set_reminder
    # Jokes
    if "joke" in command:
        return lambda c: tell_joke()
    # Email
    if "email" in command or "send mail" in command:
        return send_email
    # Open website/app
    if "open" in command:
        if "reddit" in command:
            return open_reddit
        elif "website" in command:
            return open_website
        else:
            return open_app
    # Greetings
    if any(kw in command for kw in ["what's up", "hello", "hi", "hey"]):
        return lambda c: speak("Just chilling, ready to assist!")
    # Exit
    if any(kw in command for kw in ["exit", "quit", "close"]):
        return lambda c: (speak("Goodbye!"), exit(0))
    return None

# --- GUI and Tray Icon ---
class ChatBubble(tk.Frame):
    def __init__(self, parent, text, is_user=False, **kwargs):
        super().__init__(parent, **kwargs)
        bg = '#4e8cff' if is_user else '#44475a'
        fg = '#fff' if is_user else '#f8f8f2'
        anchor = 'e' if is_user else 'w'
        padx = (40, 10) if is_user else (10, 40)
        bubble = tk.Label(self, text=text, bg=bg, fg=fg, font=("Segoe UI", 11), wraplength=400, justify='left', padx=10, pady=6, bd=0, relief='flat')
        bubble.pack(anchor=anchor, padx=padx, pady=2)

class SoundWaveWidget(tk.Canvas):
    def __init__(self, parent, bar_count=5, **kwargs):
        super().__init__(parent, width=120, height=30, bg='#23272e', highlightthickness=0, **kwargs)
        self.bar_count = bar_count
        self.bars = [self.create_rectangle(10 + i*20, 25, 25 + i*20, 25, fill='#4e8cff', width=0) for i in range(bar_count)]
        self.animating = False
    def start(self):
        self.animating = True
        self._animate()
    def stop(self):
        self.animating = False
    def _animate(self):
        import random
        if not self.animating:
            for i, bar in enumerate(self.bars):
                self.coords(bar, 10 + i*20, 25, 25 + i*20, 25)
            return
        for i, bar in enumerate(self.bars):
            h = random.randint(5, 25)
            self.coords(bar, 10 + i*20, 30-h, 25 + i*20, 25)
        self.after(100, self._animate)

class AssistantGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Desktop Assistant")
        self.root.geometry("700x450")
        self.theme = 'dark'
        self.status_var = tk.StringVar(value="Status: Idle")
        self.recognized_var = tk.StringVar(value="Recognized: ")
        self.setup_styles()
        self.create_widgets()
        self.tray_icon = None
        self.setup_tray_icon()
        self.assistant_thread = None
        self.running = False

    def setup_styles(self):
        style = ttk.Style(self.root)
        if self.theme == 'dark':
            self.root.configure(bg="#23272e")
            style.theme_use('clam')
            style.configure('.', background="#23272e", foreground="#f8f8f2", font=("Segoe UI", 11))
            style.configure('TButton', background="#44475a", foreground="#f8f8f2", font=("Segoe UI", 11), padding=6)
            style.configure('TLabel', background="#23272e", foreground="#f8f8f2", font=("Segoe UI", 12))
            style.configure('Sidebar.TFrame', background="#282a36")
            style.configure('Sidebar.TButton', background="#282a36", foreground="#f8f8f2", font=("Segoe UI", 11), padding=8)
        else:
            self.root.configure(bg="#f8f8f2")
            style.theme_use('clam')
            style.configure('.', background="#f8f8f2", foreground="#23272e", font=("Segoe UI", 11))
            style.configure('TButton', background="#e0e0e0", foreground="#23272e", font=("Segoe UI", 11), padding=6)
            style.configure('TLabel', background="#f8f8f2", foreground="#23272e", font=("Segoe UI", 12))
            style.configure('Sidebar.TFrame', background="#e0e0e0")
            style.configure('Sidebar.TButton', background="#e0e0e0", foreground="#23272e", font=("Segoe UI", 11), padding=8)

    def create_widgets(self):
        tk.Label(self.root, textvariable=self.status_var, font=("Arial", 12)).pack(pady=5)
        tk.Label(self.root, textvariable=self.recognized_var, font=("Arial", 10)).pack(pady=5)
        # Sound wave widget
        self.sound_wave = SoundWaveWidget(self.root)
        self.sound_wave.pack(pady=(0, 5))
        self.sound_wave.lower()  # Hide initially
        # Log area as a frame for chat bubbles
        self.log_area = tk.Canvas(self.root, width=600, height=250, bg="#23272e", highlightthickness=0)
        self.log_frame = tk.Frame(self.log_area, bg="#23272e")
        self.log_scroll = ttk.Scrollbar(self.root, orient="vertical", command=self.log_area.yview)
        self.log_area.create_window((0, 0), window=self.log_frame, anchor="nw")
        self.log_area.configure(yscrollcommand=self.log_scroll.set)
        self.log_area.pack(pady=5, side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_frame.bind("<Configure>", lambda e: self.log_area.configure(scrollregion=self.log_area.bbox("all")))
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Start Assistant", command=self.start_assistant).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Stop Assistant", command=self.stop_assistant).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Show Logs", command=self.show_logs).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Quit", command=self.quit_app).pack(side=tk.LEFT, padx=5)

    def show_home(self):
        self.status_var.set("Status: Idle" if not self.running else "Status: Listening...")

    def show_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("300x150")
        ttk.Label(settings_win, text="Theme:").pack(pady=10)
        theme_btn = ttk.Button(settings_win, text="Toggle Dark/Light", command=self.toggle_theme)
        theme_btn.pack(pady=10)

    def toggle_theme(self):
        self.theme = 'light' if self.theme == 'dark' else 'dark'
        self.setup_styles()
        for widget in self.root.winfo_children():
            widget.destroy()
        self.create_widgets()

    def clear_log(self):
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')

    def setup_tray_icon(self):
        # Create a simple icon
        icon_img = Image.new('RGB', (64, 64), color='blue')
        d = ImageDraw.Draw(icon_img)
        d.ellipse((8, 8, 56, 56), fill='white')
        self.tray_icon = pystray.Icon("desktop_assistant", icon_img, "Desktop Assistant", menu=pystray.Menu(
            pystray.MenuItem("Show/Hide Window", self.toggle_window),
            pystray.MenuItem("Quit", self.quit_app)
        ))
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def toggle_window(self, icon, item):
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
        else:
            self.root.withdraw()

    def start_assistant(self):
        if not self.running:
            self.running = True
            self.status_var.set("Status: Listening...")
            self.assistant_thread = threading.Thread(target=self.run_assistant, daemon=True)
            self.assistant_thread.start()

    def stop_assistant(self):
        self.running = False
        self.status_var.set("Status: Stopped")

    def run_assistant(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.assistant_loop())

    # Show/hide sound wave during listening
    async def assistant_loop(self):
        self.add_message("Assistant started.", is_user=False)
    speak("I am ready for your command")
        asyncio.create_task(check_reminders())
        while self.running:
            try:
                self.sound_wave.lift()
                self.sound_wave.start()
                command = await asyncio.wait_for(listen(), timeout=300)
                self.sound_wave.stop()
                self.sound_wave.lower()
        if command:
                    self.recognized_var.set(f"Recognized: {command}")
                    self.add_message(f"You: {command}", is_user=True)
                    handler = match_command(command)
                    if handler:
                        self.add_message("Processing...", is_user=False)
                        def run_handler():
                            try:
                                handler(command)
                            except Exception as e:
                                self.add_message(f"Error: {e}", is_user=False)
                        threading.Thread(target=run_handler, daemon=True).start()
                    else:
                        self.add_message("I don't understand that command.", is_user=False)
            except asyncio.TimeoutError:
                self.sound_wave.stop()
                self.sound_wave.lower()
                self.add_message("Listening timed out. Please try again.", is_user=False)
        self.add_message("Assistant stopped.", is_user=False)

    def add_message(self, text, is_user=False):
        bubble = ChatBubble(self.log_frame, text, is_user)
        bubble.pack(anchor='e' if is_user else 'w', pady=2, fill=tk.X, expand=True)
        self.log_area.update_idletasks()
        self.log_area.yview_moveto(1.0)

    def on_user_input(self, event=None):
        user_text = self.input_var.get().strip()
        if user_text:
            self.add_message(user_text, is_user=True)
            self.input_var.set("")
            self.handle_user_command(user_text)

    def handle_user_command(self, command):
        # Use the same matching logic as voice
        handler = match_command(command)
        if handler:
            self.add_message("Processing...", is_user=False)
            def run_handler():
                try:
                    handler(command)
                except Exception as e:
                    self.add_message(f"Error: {e}", is_user=False)
            threading.Thread(target=run_handler, daemon=True).start()
        else:
            self.add_message("I don't understand that command.", is_user=False)

    def show_logs(self):
        try:
            with open('assistant.log', 'r') as f:
                logs = f.read()
            log_win = tk.Toplevel(self.root)
            log_win.title("Assistant Logs")
            txt = scrolledtext.ScrolledText(log_win, width=80, height=30)
            txt.pack()
            txt.insert(tk.END, logs)
            txt.config(state='disabled')
        except Exception as e:
            messagebox.showerror("Error", f"Could not open log file: {e}")

    def log(self, msg):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, msg + '\n')
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def quit_app(self, *args):
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
        _tts_queue.put(None) # Stop the TTS worker
        self.root.quit()

# --- Main entry point for GUI ---
def main():
    root = tk.Tk()
    app = AssistantGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()

if __name__ == "__main__":
    main()