import re
import webbrowser
import smtplib
import subprocess
import logging
import asyncio
import pyttsx3
import speech_recognition as sr
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import os
import requests

# Configure logging for debugging and monitoring
logging.basicConfig(filename='assistant.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables for secure credential management
load_dotenv()
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speed of speech
engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)

# Dictionary to store reminders
reminders = {}

# Speak the provided text using pyttsx3
def speak(text):
    logging.info(f"Speaking: {text}")
    engine.say(text)
    engine.runAndWait()

# Listen for voice commands using speech recognition
async def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print('Listening...')
        recognizer.pause_threshold = 1
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=5)
            command = recognizer.recognize_google(audio).lower()
            logging.info(f"Recognized command: {command}")
            print(f"You said: {command}")
            return command
        except sr.UnknownValueError:
            speak("Sorry, I couldn't understand that.")
            logging.warning("Speech recognition failed: UnknownValueError")
            return ""
        except sr.RequestError as e:
            speak("Speech recognition service is unavailable.")
            logging.error(f"Speech recognition error: {e}")
            return ""
        except Exception as e:
            logging.error(f"Unexpected error in listen: {e}")
            return ""

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

# Process commands using a dictionary for modularity
command_handlers = {
    'open reddit': open_reddit,
    'open website': open_website,
    'what\'s up': lambda _: speak("Just chilling, ready to assist!"),
    'joke': lambda _: tell_joke(),
    'current weather in': get_weather,
    'weather forecast in': get_forecast,
    'email': send_email,
    'open': open_app,
    'news': lambda _: get_news(),
    'set reminder': set_reminder,
    'exit|quit': lambda _: (speak("Goodbye!"), exit(0))
}

# Main assistant logic to process commands
async def assistant():
    speak("I am ready for your command")
    asyncio.create_task(check_reminders())  # Run reminder checks in background
    while True:
        command = await listen()
        if command:
            handled = False
            for key, handler in command_handlers.items():
                if key in command or any(k in command for k in key.split('|')):
                    handler(command)
                    handled = True
                    break
            if not handled:
                speak("I don't understand that command.")
                logging.warning(f"Unrecognized command: {command}")

# Run the assistant
if __name__ == "__main__":
    asyncio.run(assistant())