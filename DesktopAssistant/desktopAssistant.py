import re
import webbrowser
import smtplib
import subprocess
import logging
import asyncio
import pyttsx3
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import os
import requests
import json
from vosk import Model, KaldiRecognizer
import pyaudio
from google.cloud import speech
import io
import threading
import customtkinter as ctk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw
import difflib
import queue
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Configure logging and load environment variables
logging.basicConfig(filename='assistant.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check for first run and setup if needed
if not os.path.exists('.env'):
    try:
        from setup_first_run import check_first_run
        check_first_run()
    except Exception as e:
        logging.error(f"First run setup failed: {e}")

load_dotenv()
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
LLM_MODEL_PATH = os.getenv('LLM_MODEL_PATH', 'llm-model')

# Initialize LLM
try:
    tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(LLM_MODEL_PATH)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    logging.info(f"Transformers model loaded: {LLM_MODEL_PATH}")
except Exception as e:
    tokenizer = None
    model = None
    logging.error(f"Failed to load transformers model: {e}")

# Initialize TTS
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 0.9)
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

reminders = {}

# Voice recognition (offline/online)
async def listen():
    RECOGNITION_MODE = os.getenv('RECOGNITION_MODE', 'offline')
    VOSK_MODEL_PATH = os.getenv('VOSK_MODEL_PATH', 'vosk-model-small-en-us-0.15')
    if RECOGNITION_MODE == 'offline':
        try:
            if not Path(VOSK_MODEL_PATH).exists():
                speak(f"Vosk model not found at {VOSK_MODEL_PATH}. Please download and extract the model.")
                logging.error(f"Vosk model not found at {VOSK_MODEL_PATH}")
                exit(1)
            vosk_model = Model(VOSK_MODEL_PATH)
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
            stream.start_stream()
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

async def listen_cloud():
    try:
        speak("Listening (cloud mode)...")
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

# Utility and command functions

def tell_time():
    now = datetime.now()
    current_time = now.strftime('%I:%M %p')
    speak(f"The current time is {current_time}.")
    logging.info(f"Told time: {current_time}")

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
                for day in data['forecast']['forecastday'][:3]:
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

async def check_reminders():
    while True:
        now = datetime.now()
        for remind_time in list(reminders.keys()):
            if now >= remind_time:
                speak(f"Reminder: {reminders[remind_time]}")
                logging.info(f"Reminder triggered: {reminders[remind_time]}")
                del reminders[remind_time]
        await asyncio.sleep(60)

def ask_llm_sync(command):
    global tokenizer, model
    if not model or not tokenizer:
        speak("Transformers model not loaded. Please set LLM_MODEL_PATH in your .env file.")
        return
    try:
        prompt = command.strip()
        if not prompt:
            speak("Please provide a question or message.")
            return
        inputs = tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_length=inputs.shape[1] + 100,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer = response[len(prompt):].strip()
        if not answer:
            answer = "I'm not sure how to respond to that."
        speak(answer)
        logging.info(f"LLM answer: {answer}")
    except Exception as e:
        speak("Sorry, there was an error with the AI model.")
        logging.error(f"LLM error: {e}")

def match_command(command):
    command = command.lower()
    if "weather" in command:
        import re
        match = re.search(r'weather(?: in)? ([a-zA-Z ]+)', command)
        if match:
            city = match.group(1).strip()
            return lambda c: get_weather(f"current weather in {city}")
        elif "in" in command:
            return lambda c: speak("Please specify a city for the weather.")
        else:
            return lambda c: speak("Please specify a city for the weather.")
    if any(kw in command for kw in ["time", "what time", "current time", "tell me the time"]):
        return lambda c: tell_time()
    if any(kw in command for kw in ["news", "headlines"]):
        return lambda c: get_news()
    if any(kw in command for kw in ["remind", "reminder"]):
        return set_reminder
    if "joke" in command:
        return lambda c: speak("Here's a joke: Why did the chicken join a band? Because it had the drumsticks!")
    if "email" in command or "send mail" in command:
        return lambda c: speak("Email functionality is not available in this demo.")
    if "open" in command:
        if "reddit" in command:
            return lambda c: speak("Opening Reddit...")
        elif "website" in command:
            return lambda c: speak("Opening website...")
        else:
            return lambda c: speak("Opening app...")
    if any(kw in command for kw in ["what's up", "hello", "hi", "hey"]):
        return lambda c: speak("Just chilling, ready to assist!")
    if any(kw in command for kw in ["exit", "quit", "close"]):
        return lambda c: (speak("Goodbye!"), exit(0))
    return ask_llm_sync

# Modern Assistant GUI using customtkinter
class AssistantGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ovo")
        self.root.geometry("800x500")
        try:
            self.root.iconbitmap("ovo.ico")
        except:
            pass
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.status_var = ctk.StringVar(value="Status: Idle")
        self.recognized_var = ctk.StringVar(value="Recognized: ")
        self.create_widgets()
        self.assistant_thread = None
        self.running = False

    def create_widgets(self):
        self.status_label = ctk.CTkLabel(self.root, textvariable=self.status_var, font=("Segoe UI", 16))
        self.status_label.pack(pady=(20, 5))
        self.recognized_label = ctk.CTkLabel(self.root, textvariable=self.recognized_var, font=("Segoe UI", 12))
        self.recognized_label.pack(pady=(0, 10))
        self.chat_frame = ctk.CTkFrame(self.root, width=700, height=300, corner_radius=15)
        self.chat_frame.pack(pady=10, padx=20, fill="both", expand=True)
        self.chat_log = ctk.CTkTextbox(self.chat_frame, font=("Segoe UI", 13), wrap="word")
        self.chat_log.pack(fill="both", expand=True, padx=10, pady=10)
        self.input_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.input_frame.pack(side="bottom", fill="x", padx=20, pady=10)
        self.input_var = ctk.StringVar()
        self.input_entry = ctk.CTkEntry(self.input_frame, textvariable=self.input_var, font=("Segoe UI", 13), width=500)
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_entry.bind("<Return>", self.on_user_input)
        self.send_button = ctk.CTkButton(self.input_frame, text="Send", command=self.on_user_input, width=80)
        self.send_button.pack(side="left")
        self.start_button = ctk.CTkButton(self.root, text="Start Assistant", command=self.start_assistant)
        self.start_button.pack(side="left", padx=10, pady=10)
        self.stop_button = ctk.CTkButton(self.root, text="Stop Assistant", command=self.stop_assistant)
        self.stop_button.pack(side="left", padx=10, pady=10)
        self.quit_button = ctk.CTkButton(self.root, text="Quit", command=self.quit_app)
        self.quit_button.pack(side="right", padx=10, pady=10)

    def add_message(self, text, is_user=False):
        tag = "user" if is_user else "assistant"
        self.chat_log.insert("end", ("You: " if is_user else "Ovo: ") + text + "\n")
        self.chat_log.see("end")

    def on_user_input(self, event=None):
        user_text = self.input_var.get().strip()
        if user_text:
            self.add_message(user_text, is_user=True)
            self.input_var.set("")
            self.handle_user_command(user_text)

    def handle_user_command(self, command):
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

    async def assistant_loop(self):
        self.add_message("Ovo started.", is_user=False)
        speak("Ovo is ready for your command")
        asyncio.create_task(check_reminders())
        while self.running:
            try:
                command = await asyncio.wait_for(listen(), timeout=300)
                if command:
                    self.recognized_var.set(f"Recognized: {command}")
                    self.add_message(command, is_user=True)
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
                self.add_message("Listening timed out. Please try again.", is_user=False)
        self.add_message("Ovo stopped.", is_user=False)

    def quit_app(self, *args):
        self.running = False
        self.root.quit()

# Main entry point
def main():
    root = ctk.CTk()
    app = AssistantGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()

if __name__ == "__main__":
    main()