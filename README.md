# 🎤 Desktop Voice Assistant

A powerful, feature-rich desktop voice assistant built with Python that responds to voice commands and performs various tasks automatically.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

## ✨ Features

### 🗣️ Voice Recognition & Speech
- **Real-time voice recognition** using Google Speech Recognition API
- **Text-to-speech** output with customizable speed and volume
- **Ambient noise adjustment** for better recognition accuracy

### 🌐 Web & Application Control
- **Website navigation** - Open any website with voice commands
- **Reddit integration** - Browse subreddits hands-free
- **Desktop applications** - Launch common apps like Notepad and Calculator

### 📧 Communication
- **Email functionality** - Send emails using Gmail SMTP
- **Voice-to-text** for email composition

### 🌤️ Weather & Information
- **Current weather** - Get real-time weather for any city
- **Weather forecasts** - 3-day weather predictions
- **News headlines** - Latest news from NewsAPI
- **Jokes** - Random dad jokes from icanhazdadjoke API

### ⏰ Productivity Tools
- **Reminder system** - Set voice-activated reminders
- **Automatic reminder checking** - Background monitoring
- **Logging system** - Comprehensive activity tracking

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Microphone and speakers
- Internet connection

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/desktop-assistant.git
   cd desktop-assistant
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASS=your_app_password
   WEATHER_API_KEY=your_weather_api_key
   NEWS_API_KEY=your_news_api_key
   ```

### API Keys Setup

#### Weather API
1. Visit [WeatherAPI.com](https://www.weatherapi.com/)
2. Sign up for a free account
3. Copy your API key to `WEATHER_API_KEY`

#### News API
1. Visit [NewsAPI.org](https://newsapi.org/)
2. Register for a free account
3. Copy your API key to `NEWS_API_KEY`

#### Gmail Setup
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password
3. Use the App Password in `EMAIL_PASS`

## 🎯 Usage

### Starting the Assistant
```bash
python desktopAssistant.py
```

### Voice Commands

| Command | Description | Example |
|---------|-------------|---------|
| `"open website [domain]"` | Opens a website | `"open website google.com"` |
| `"open reddit [subreddit]"` | Opens Reddit or specific subreddit | `"open reddit programming"` |
| `"current weather in [city]"` | Gets current weather | `"current weather in New York"` |
| `"weather forecast in [city]"` | Gets 3-day forecast | `"weather forecast in London"` |
| `"tell me a joke"` | Fetches a random joke | `"tell me a joke"` |
| `"get news"` | Fetches latest headlines | `"get news"` |
| `"send email"` | Initiates email sending | `"send email"` |
| `"open [app]"` | Opens desktop applications | `"open notepad"` |
| `"set reminder"` | Sets a voice reminder | `"set reminder"` |
| `"exit"` or `"quit"` | Exits the assistant | `"exit"` |

## 🛠️ Technical Details

### Dependencies
- **pyttsx3** - Text-to-speech engine
- **SpeechRecognition** - Voice recognition
- **requests** - HTTP requests for APIs
- **python-dotenv** - Environment variable management

### Architecture
- **Asynchronous operations** for non-blocking voice recognition
- **Modular design** with separate functions for each feature
- **Comprehensive logging** for debugging and monitoring
- **Error handling** with graceful fallbacks

### File Structure
```
desktop-assistant/
├── desktopAssistant.py    # Main application file
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (create this)
├── assistant.log         # Application logs (auto-generated)
└── README.md            # This file
```

## 🔧 Configuration

### Speech Settings
You can customize speech settings in the code:
```python
engine.setProperty('rate', 150)    # Speech speed (words per minute)
engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
```

### Logging
Logs are automatically saved to `assistant.log` with timestamps and log levels.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

### Common Issues

**Speech Recognition Not Working**
- Ensure your microphone is properly connected and working
- Check that you have an active internet connection
- Try adjusting the ambient noise settings

**API Errors**
- Verify your API keys are correct in the `.env` file
- Check that you haven't exceeded API rate limits
- Ensure all required environment variables are set

**Email Sending Issues**
- Verify your Gmail credentials
- Ensure 2-factor authentication is enabled
- Use an App Password instead of your regular password

## 📞 Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check the logs in `assistant.log`
- Review the troubleshooting section above

---

*Transform your desktop experience with voice commands!*

## 🖥️ Windows EXE & Releases

### Downloading the EXE
- Go to the [Releases](https://github.com/yourusername/desktop-assistant/releases) page.
- Download the latest `desktopAssistant.exe`.
- The Vosk model (`vosk-model-small-en-us-0.15`) is bundled with the EXE. If you want to update or replace the model, download it from [Vosk Models](https://alphacephei.com/vosk/models) and extract it in the same folder as the EXE.

### Running the EXE
- Double-click `desktopAssistant.exe`.
- The assistant will launch with a modern chat UI, chat bubbles, and a sound wave animation for voice input.

### What to include in a Release
- `desktopAssistant.exe`
- `vosk-model-small-en-us-0.15` folder (bundled)
- README.md

### Security
- **Never** include your `.env` or Google Cloud key in the release or repo.

---

## 🆕 Features (Update)
- Modern chat UI with chat bubbles for all messages
- Sound wave animation when listening
- Flexible weather/news/reminder command matching
- System tray icon and window controls

---

## 🛠️ Updated Dependencies

Add to your dependencies list:
- `vosk`
- `pyaudio`
- `pystray`
- `pillow`
- `google-cloud-speech`
- (and keep the existing ones)

---
