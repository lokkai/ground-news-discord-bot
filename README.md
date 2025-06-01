# 🚀 GROUND NEWS DISCORD BOT
**Automated News Aggregation from Ground News to Discord Channels**  
*Version 2.2 | Developed by Jordan Ilaréguy*

---

## 🔥 ENHANCED FEATURES
- **Personalized User Experience**: Saves name/timezone preferences between sessions
- **Professional Console Interface**: Enhanced ASCII art intro with animations
- **Real-time RSS Monitoring**: Checks Ground News feed every 5 minutes
- **Advanced Summarization**: 5-sentence summaries using TF-IDF algorithm
- **Smart Duplicate Detection**: URL normalization + title similarity (85% threshold)
- **Time Zone Conversion**: Automatic date conversion to user's local time
- **Persistent History**: Remembers posted articles between sessions
- **Self-Healing System**: Automatic dependency installation
- **Professional Logging**: Detailed console output + `bot.log` file
- **Automatic Cleanup**: Removes old titles after 24 hours
- **Optimized Formatting**: Clean Discord messages with publication dates
- **Error-Resistant Design**: Graceful handling of API failures
- **Dynamic Countdown Timer**: Real-time fetch countdown in console

---

## 💻 SYSTEM REQUIREMENTS
- **Python 3.7 or newer** - [Download Python](https://www.python.org/downloads/)
- **Discord Developer Account** - To create your bot
   
---

## 🛠 COMPLETE SETUP GUIDE

### STEP 1: INSTALL PYTHON PACKAGES
Open Command Prompt or PowerShell and run:
- pip install discord.py feedparser python-dotenv aiohttp nltk

### STEP 2: CREATE DISCORD BOT
- Go to Discord Developer Portal.
- Click "New Application" → Name it "Ground News Bot" → Create
- Navigate to "Bot" in left sidebar → Click "Add Bot" → Confirm
- Under "TOKEN", click "Reset Token" → Copy the token (THIS IS YOUR BOT PASSWORD!)

### STEP 3: GET CHANNEL ID
- Open Discord app.
- Go to User Settings → Advanced → Enable "Developer Mode".
- Right-click your target text channel → "Copy ID".

### STEP 4: CREATE .ENV FILE
- Create a new file named .env in your project folder.
- Add these exact lines (replace placeholder values with your own):
- DISCORD_TOKEN=your_bot_token_here
- CHANNEL_ID=your_channel_id_here

### STEP 5: DOWNLOAD BOT FILES
- Download the repository files.
- Extract all files to a new folder on your computer.
- Place the .env file you created in this same folder.

---

# 🚀 RUNNING THE BOT

WINDOWS INSTRUCTIONS
- Open the folder containing the bot files
- Hold SHIFT and right-click in the folder → Select "Open PowerShell window here"

RUN THE BOT:
- python ground-news-discord-bot.py

FIRST RUN EXPECTATIONS

- Professional ASCII art intro with animations
- Personalized welcome prompt (name/timezone)
- Automatic NLTK resource download
- Dependency auto-installation (if missing)
- Persistent settings creation
- Real-time status dashboard
- Countdown timer to next fetch

---

# ⚙️ CONFIGURATION OPTIONS

HOW OFTEN TO CHECK FOR NEWS (SECONDS)
- self.fetch_interval = 300  # 5 minutes (default)

TITLE SIMILARITY THRESHOLD (0.80-0.95 RECOMMENDED)
- self.title_similarity_threshold = 0.85  # 85% similarity blocks duplicates

SUMMARIZATION SETTING
- self.summarization_enabled = True  # Enable/disable auto-summarization
- num_sentences=5  # Number of sentences in summary (configurable in code)

MESSAGE FORMAT
- Article title as main header
- Publication date
- Detailed 5-sentence summary
- Direct article link

---

# 🐛 TROUBLESHOOTING GUIDE

SYMPTOMS:

"CHANNEL NOT FOUND" ERROR
1. Verify CHANNEL_ID in .env
2. Ensure bot has permissions.
3. Check Developer Mode is enabled in Discord.
   
NO NEWS ARTICLES APPEARING
1. Check RSS feed URL in code.
2. Verify internet connection.
3. Wait for next fetch cycle.
   
DUPLICATE POSTS GETTING THROUGH
- Increase title_similarity_threshold to 0.90 in code.

BOT WON'T START
1. Check .env file exists.
2. Verify Python packages installed (especially nltk).
3. Look for errors in console.
   
TOKEN NOT WORKING
1. Regenerate token in Discord Developer Portal.
2. Update .env file with new token.

NLTK DOWNLOAD ISSUES
1. Ensure internet connection
2. Manually download resources:
   - import nltk
   - nltk.download('punkt')
   - nltk.download('stopwords')

DETAILED ERROR CHECKING
- Examine bot.log file in project folder.

---

🔒 SECURITY BEST PRACTICES

- NEVER SHARE YOUR .ENV FILE - Contains your bot token (equivalent to password).
- REGENERATE COMPROMISED TOKENS - Immediately if token is accidentally exposed.
- USE GITIGNORE - Ensure .env and log files aren't committed to version control.
- STORE SENSITIVE FILES SECURELY - Keep .env file only on your local machine.

---

❓ FREQUENTLY ASKED QUESTIONS

Q: How does summarization work?
A: Uses TF-IDF algorithm to extract 5 key sentences while preserving meaning.

Q: How often does the bot check for new articles?
A: Every 5 minutes by default (configurable in code).

Q: Why are some articles not appearing?
A: They might be blocked as duplicates or feed might have no new content.

Q: Can I run this 24/7?
A: Yes! For continuous operation:
- Windows: Run in background using Task Scheduler.
- Linux: Use nohup python3 ground-news-discord-bot.py
- Cloud: Host on AWS/Azure free tier.

Q: How do I change the RSS feed?
A: Edit the RSS_FEEDS dictionary in the Python script.

---

NOTE: This bot is designed for personal/educational use. Commercial use may require permission from Ground News.
