import aiohttp
import discord
import asyncio
import feedparser
import logging
from datetime import datetime, timedelta
import sys
import re
import os
import json
import difflib
import string
import time
import nltk
import heapq
import math
from dotenv import load_dotenv
from collections import defaultdict
import subprocess
from pathlib import Path
from email.utils import parsedate_to_datetime
import dateutil.parser  # Added for better date parsing

# Timezone mapping for abbreviations
TIMEZONE_MAP = {
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "GMT": "GMT",
    "UTC": "UTC",
    "AEST": "Australia/Sydney",
    "AEDT": "Australia/Sydney"
}

# Check and install missing dependencies
required_libraries = ['pytz', 'colorama', 'python-dateutil']
for lib in required_libraries:
    try:
        __import__(lib)
    except ImportError:
        print(f"Installing {lib} library...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

import pytz
from colorama import Fore, Style, init
init(autoreset=True)  # Initialize colorama

# Load environment variables
load_dotenv()

# User settings file path
USER_SETTINGS_FILE = 'user_settings.json'

# Download required NLTK data
def download_nltk_resources():
    resources = ['punkt', 'stopwords', 'punkt_tab']  # Added punkt_tab
    for resource in resources:
        try:
            nltk.data.find(resource)
        except LookupError:
            print(f"Downloading NLTK resource: {resource}")
            nltk.download(resource, quiet=False)  # Show download progress

# Call the download function immediately
download_nltk_resources()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('rss-bot')

# Only Ground News feed
RSS_FEEDS = {
    "Ground News": "https://rss.app/feeds/SGUPMZoQI5Pc0x31.xml"
}

def load_user_settings():
    """Load user settings from file"""
    if Path(USER_SETTINGS_FILE).exists():
        try:
            with open(USER_SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Convert timezone abbreviation to full name if needed
                tz = settings['timezone']
                settings['timezone'] = TIMEZONE_MAP.get(tz, tz)
                return settings
        except Exception as e:
            logger.error(f"Error loading user settings: {str(e)}")
    return None

def save_user_settings(name, timezone):
    """Save user settings to file"""
    try:
        with open(USER_SETTINGS_FILE, 'w') as f:
            json.dump({"name": name, "timezone": timezone}, f)
    except Exception as e:
        logger.error(f"Error saving user settings: {str(e)}")

def get_user_settings():
    """Prompt user for settings if not already set"""
    settings = load_user_settings()
    
    if settings:
        print(f"\nWelcome back, {settings['name']}!")
        print(f"Your current timezone is {settings['timezone']}")
        return settings
    
    print("\n" + "=" * 60)
    print("Welcome to Ground News Discord Bot!".center(60))
    print("=" * 60)
    
    name = input("Please enter your name: ").strip()
    while not name:
        print("Name cannot be empty. Please try again.")
        name = input("Please enter your name: ").strip()
    
    print("\nPlease select your time zone:")
    print("Common time zones:")
    tz_options = [
        "EST", "EDT", "CST", "CDT", "MST", "MDT", 
        "PST", "PDT", "GMT", "UTC", "AEST", "AEDT"
    ]
    
    for i, tz in enumerate(tz_options, 1):
        print(f"{i}. {tz}")
    
    print("Or enter a custom time zone (e.g. 'America/New_York')")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-12 or custom): ").strip()
            
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(tz_options):
                    timezone = TIMEZONE_MAP[tz_options[index]]
                    break
                print("Invalid number. Please try again.")
            else:
                # Validate custom time zone
                if choice in pytz.all_timezones:
                    timezone = choice
                    break
                print(f"Invalid time zone. Please enter a valid time zone.")
        except ValueError:
            print("Invalid input. Please try again.")
    
    save_user_settings(name, timezone)
    print(f"\nSettings saved! Welcome, {name}!")
    return {"name": name, "timezone": timezone}

class FreeTextSummarizer:
    """Free text summarization using TF-IDF algorithm"""
    def __init__(self):
        self.stop_words = set(nltk.corpus.stopwords.words('english'))
        self.stemmer = nltk.stem.PorterStemmer()
    
    def preprocess(self, text):
        """Tokenize and clean text"""
        # Tokenize text
        words = nltk.word_tokenize(text.lower())
        
        # Remove stopwords and punctuation
        words = [word for word in words if word.isalnum() and word not in self.stop_words]
        
        # Stem words
        words = [self.stemmer.stem(word) for word in words]
        
        return words
    
    def calculate_sentence_scores(self, sentences):
        """Calculate TF-IDF scores for sentences"""
        # Calculate word frequencies
        word_freq = defaultdict(int)
        for sentence in sentences:
            for word in sentence:
                word_freq[word] += 1
        
        # Calculate IDF values
        idf_values = {}
        total_sentences = len(sentences)
        for word, freq in word_freq.items():
            idf_values[word] = math.log(total_sentences / (1 + freq))
        
        # Calculate sentence scores
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            score = 0
            for word in sentence:
                if word in idf_values:
                    score += idf_values[word]
            sentence_scores[i] = score / len(sentence) if sentence else 0
        
        return sentence_scores
    
    def summarize(self, text, num_sentences=5):  # Increased to 5 sentences
        """Generate summary from text"""
        try:
            # Split text into sentences
            sentences = nltk.sent_tokenize(text)
            
            # Skip if too few sentences
            if len(sentences) < 2:
                return None
                
            # Preprocess each sentence
            preprocessed_sentences = [self.preprocess(sent) for sent in sentences]
            
            # Calculate sentence scores
            sentence_scores = self.calculate_sentence_scores(preprocessed_sentences)
            
            # Select top sentences
            top_sentences = heapq.nlargest(
                num_sentences, 
                sentence_scores, 
                key=sentence_scores.get
            )
            
            # Return summary in original order
            summary_sentences = [sentences[i] for i in sorted(top_sentences)]
            return " ".join(summary_sentences)
        
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            return None

class NewsBot(discord.Client):
    def __init__(self, *args, user_settings, **kwargs):
        super().__init__(*args, **kwargs)
        self.posted_articles = self.load_posted_articles()
        self.posted_titles = self.load_posted_titles()
        self.channel_id = int(os.getenv('CHANNEL_ID'))
        self.session = None
        self.next_fetch_time = datetime.now()
        self.fetch_interval = 300  # 5 minutes
        self.title_similarity_threshold = 0.85
        self.summarization_enabled = True
        self.summarizer = FreeTextSummarizer()
        self.user_settings = user_settings
        self.timezone = pytz.timezone(user_settings['timezone'])

    def load_posted_articles(self):
        """Load posted articles from file"""
        try:
            if os.path.exists('posted_articles.json'):
                with open('posted_articles.json', 'r') as f:
                    return set(json.load(f))
        except Exception as e:
            logger.error(f"Error loading posted articles: {str(e)}")
        return set()

    def save_posted_articles(self):
        """Save posted articles to file"""
        try:
            with open('posted_articles.json', 'w') as f:
                json.dump(list(self.posted_articles), f)
        except Exception as e:
            logger.error(f"Error saving posted articles: {str(e)}")
            
    def load_posted_titles(self):
        """Load posted titles from file"""
        try:
            if os.path.exists('posted_titles.json'):
                with open('posted_titles.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading posted titles: {str(e)}")
        return {}

    def save_posted_titles(self):
        """Save posted titles to file"""
        try:
            with open('posted_titles.json', 'w') as f:
                json.dump(self.posted_titles, f)
        except Exception as e:
            logger.error(f"Error saving posted titles: {str(e)}")
            
    def normalize_title(self, title):
        """Normalize title for similarity comparison"""
        # Convert to lowercase
        title = title.lower()
        # Remove punctuation
        title = title.translate(str.maketrans('', '', string.punctuation))
        # Remove extra spaces
        title = re.sub(r'\s+', ' ', title).strip()
        # Remove common words that might cause false positives
        stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "with", "and", "but", "or"}
        words = [word for word in title.split() if word not in stop_words]
        return " ".join(words)
    
    def is_similar_title(self, new_title):
        """Check if a title is similar to any previously posted titles"""
        normalized_new = self.normalize_title(new_title)
        
        # Clean up old titles (older than 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        expired_titles = [title for title, timestamp in self.posted_titles.items() 
                         if datetime.fromisoformat(timestamp) < cutoff]
        for title in expired_titles:
            del self.posted_titles[title]
        
        # Check against all active titles
        for existing_title in self.posted_titles:
            # Skip titles that are too different in length
            if abs(len(normalized_new) - len(existing_title)) > 15:
                continue
                
            # Calculate similarity ratio
            seq = difflib.SequenceMatcher(None, normalized_new, existing_title)
            ratio = seq.ratio()
            
            if ratio >= self.title_similarity_threshold:
                return True
                
        return False

    async def async_fetch_feed(self, url):
        """Fetch RSS feed asynchronously"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    xml = await response.text()
                    return feedparser.parse(xml)
        except Exception as e:
            logger.warning(f"Failed to fetch feed: {str(e)}")
        return None

    def generate_summary(self, text):
        """Generate free summary of text"""
        if not self.summarization_enabled or not text:
            return None
            
        # Skip if text is too short
        if len(text.split()) < 50:
            return None
            
        # Generate summary (now 5 sentences)
        summary = self.summarizer.summarize(text)
        
        # Ensure summary is different from original
        if summary and len(summary) < len(text) * 0.7:  # Summary should be significantly shorter
            return summary
            
        return None
    
    def normalize_url(self, url):
        """Normalize URL to prevent duplicates"""
        # Remove common tracking parameters
        url = re.sub(r'[\?&](utm_|source|fbclid|ref|igshid)=[^&#]+', '', url)
        # Remove trailing slash and fragment identifiers
        url = url.rstrip('/').split('#')[0]
        return url

    def get_description(self, entry):
        """Extract and clean description"""
        content = ""
        if 'description' in entry:
            content = entry.description
        elif 'summary' in entry:
            content = entry.summary
        elif 'content' in entry and len(entry.content) > 0:
            content = entry.content[0].value
            
        return self.clean_html(content) if content else None

    def clean_html(self, text):
        """Remove HTML tags"""
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text).strip()[:1000]  # Limit to 1000 characters
    
    def format_datetime(self, dt_str):
        """Parse and format datetime string to user's timezone"""
        try:
            # Try RSS format first
            dt = parsedate_to_datetime(dt_str)
        except (ValueError, TypeError):
            try:
                # Try ISO format
                dt = datetime.fromisoformat(dt_str)
            except (ValueError, TypeError):
                try:
                    # Use dateutil parser as fallback
                    dt = dateutil.parser.parse(dt_str)
                except Exception:
                    return dt_str  # Return original if all parsing fails
        
        # Ensure datetime is timezone-aware
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        # Convert to user's timezone
        local_dt = dt.astimezone(self.timezone)
        
        # Format with timezone abbreviation and UTC offset
        tz_abbr = local_dt.strftime('%Z')
        utc_offset = local_dt.strftime('%z')
        formatted_offset = f"{utc_offset[:3]}:{utc_offset[3:]}"
        
        return f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_abbr} (UTC{formatted_offset})"
    
    def display_intro(self):
        """Display enhanced professional ASCII art intro with color and animations"""
        intro_art = r"""
  ██████  ██████   ██████  ██    ██ ███    ██ ██████      ███    ██ ███████ ██     ██ ███████ 
 ██       ██   ██ ██    ██ ██    ██ ████   ██ ██   ██     ████   ██ ██      ██     ██ ██      
 ██   ███ ██████  ██    ██ ██    ██ ██ ██  ██ ██   ██     ██ ██  ██ █████   ██  █  ██ ███████ 
 ██    ██ ██   ██ ██    ██ ██    ██ ██  ██ ██ ██   ██     ██  ██ ██ ██      ██ ███ ██      ██ 
 ██████  ██   ██  ██████   ██████  ██   ████ ██████      ██   ████ ███████  ███ ███  ███████ 
        """
        
        # Typewriter effect for ASCII art
        print(Fore.GREEN + "\n")
        for line in intro_art.split('\n'):
            print(Fore.GREEN + line)
            time.sleep(0.05)
        
        # Animated header
        time.sleep(0.5)
        print(Fore.YELLOW + "=" * 60)
        time.sleep(0.2)
        print(Fore.CYAN + "GROUND NEWS DISCORD BOT".center(60))
        time.sleep(0.2)
        print(Fore.LIGHTBLUE_EX + "Professional News Aggregation Solution".center(60))
        time.sleep(0.2)
        print(Fore.YELLOW + "=" * 60)
        time.sleep(0.5)
        
        # Personalized welcome
        if self.user_settings:
            print(Fore.LIGHTMAGENTA_EX + f"\nWelcome back, {self.user_settings['name']}!".center(60))
            print(Fore.LIGHTMAGENTA_EX + f"Your personalized news hub is ready".center(60))
            time.sleep(0.5)
            print(Fore.LIGHTBLUE_EX + f"Timezone: {self.user_settings['timezone']}".center(60))
            time.sleep(0.3)
        else:
            print(Fore.LIGHTMAGENTA_EX + "\nWelcome to your professional news hub!".center(60))
            time.sleep(0.5)
        
        # System info
        print(Fore.LIGHTWHITE_EX + "\n" + "-" * 60)
        time.sleep(0.2)
        print(Fore.LIGHTCYAN_EX + f"Developed by: Jordan Ilaréguy".center(60))
        time.sleep(0.2)
        print(Fore.LIGHTCYAN_EX + f"Version: 2.2".center(60))
        time.sleep(0.2)
        print(Fore.LIGHTCYAN_EX + f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(60))
        time.sleep(0.2)
        print(Fore.LIGHTWHITE_EX + "-" * 60)
        time.sleep(0.5)
        
        # System status with animation
        print(Fore.LIGHTGREEN_EX + "\nInitializing news monitoring service" + Fore.WHITE, end='')
        for _ in range(3):
            print(Fore.LIGHTGREEN_EX + '.' + Fore.WHITE, end='', flush=True)
            time.sleep(0.3)
        print("\n")
        
        # Configuration details
        print(Fore.LIGHTYELLOW_EX + f"Summarization: {'ENABLED' if self.summarization_enabled else 'DISABLED'}")
        time.sleep(0.2)
        print(Fore.LIGHTYELLOW_EX + f"Duplicate Threshold: {self.title_similarity_threshold}")
        time.sleep(0.2)
        print(Fore.LIGHTYELLOW_EX + f"Check Interval: {self.fetch_interval//60} minutes")
        time.sleep(0.2)
        print(Fore.LIGHTYELLOW_EX + f"Monitoring: {len(RSS_FEEDS)} news feeds\n")
        time.sleep(0.5)

    async def setup_hook(self):
        # Create persistent HTTP session
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        timeout = aiohttp.ClientTimeout(total=20)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        self.bg_task = self.loop.create_task(self.news_checker())
        logger.info("News bot starting...")
        logger.info(f"Loaded {len(self.posted_articles)} previously posted articles")
        logger.info(f"Loaded {len(self.posted_titles)} previously posted titles")
        logger.info("Monitoring Ground News feed")
        logger.info(f"Summarization: {'ENABLED' if self.summarization_enabled else 'DISABLED'}")

    async def news_checker(self):
        await self.wait_until_ready()
        channel = self.get_channel(self.channel_id)
        if not channel:
            logger.error(f"Channel {self.channel_id} not found!")
            return
            
        await channel.send("📰 **Ground News Bot Activated!** Monitoring news feed...")
        
        while not self.is_closed():
            try:
                # Set next fetch time
                self.next_fetch_time = datetime.now() + timedelta(seconds=self.fetch_interval)
                logger.info("Starting news feed check...")
                print("\n[Status] Fetching latest news...")
                
                new_count = 0
                
                for source, url in RSS_FEEDS.items():
                    feed = await self.async_fetch_feed(url)
                    if not feed or not feed.entries:
                        logger.warning(f"⚠️ Empty feed from {source}")
                        continue
                    
                    logger.info(f"📰 Found {len(feed.entries)} articles from {source}")
                    
                    # Process from oldest to newest
                    for entry in reversed(feed.entries):
                        article_url = entry.get('link', '')
                        title = entry.get('title', 'No title')[:250]
                        
                        if not article_url:
                            logger.warning(f"⚠️ Article missing link: {title}")
                            continue
                            
                        # Normalize URL
                        article_url = self.normalize_url(article_url)
                            
                        # Skip duplicates
                        if article_url in self.posted_articles:
                            logger.info(f"⏩ Skipping duplicate URL: {title[:60]}...")
                            continue
                            
                        # Skip duplicates based on title similarity
                        if self.is_similar_title(title):
                            logger.info(f"⏩ Skipping similar title: {title[:60]}...")
                            continue
                            
                        # Add to posted articles
                        self.posted_articles.add(article_url)
                        normalized_title = self.normalize_title(title)
                        self.posted_titles[normalized_title] = datetime.utcnow().isoformat()
                        new_count += 1
                        
                        # Format the message with BREAKING NEWS header
                        message = "🚨 **BREAKING NEWS** 🚨\n\n"
                        message += f"**{title}**\n\n"
                        
                        # Add publication date with timezone conversion
                        if 'published' in entry:
                            pub_date = self.format_datetime(entry.published)
                            message += f"🗓️ *Your Local Time: {pub_date}*\n\n"
                        elif 'updated' in entry:
                            pub_date = self.format_datetime(entry.updated)
                            message += f"🗓️ *Your Local Time: {pub_date}*\n\n"
                        
                        # Get article content
                        article_content = self.get_description(entry)
                        
                        # Add expanded summary (5 sentences)
                        if article_content:
                            summary = self.generate_summary(article_content)
                            if summary:
                                message += "**📝 DETAILED SUMMARY**\n"
                                message += f"{summary}\n\n"
                            else:
                                # Fallback to truncated description
                                message += f"{article_content[:500]}...\n\n"
                        
                        # Add the article URL
                        message += f"Read more: {article_url}"
                        
                        # Send message
                        try:
                            await channel.send(message)
                            logger.info(f"✅ Posted: {title[:60]}...")
                        except discord.HTTPException as e:
                            # Handle message length issues
                            if "Must be 2000 or fewer" in str(e):
                                # Fallback to minimal message
                                minimal_msg = f"🚨 **BREAKING NEWS** 🚨\n\n**{title}**\n\nRead more: {article_url}"
                                await channel.send(minimal_msg)
                                logger.info("✅ Posted minimal version")
                            else:
                                logger.error(f"❌ Error sending article: {str(e)}")
                        
                        await asyncio.sleep(2)  # Pause between articles
                
                logger.info(f"✅ Posted {new_count} new articles total")
                self.save_posted_articles()
                self.save_posted_titles()
                
                # Print countdown to next fetch
                logger.info(f"⏱️ Next check in {self.fetch_interval//60} minutes")
                
                # Dynamic countdown timer in console
                print("\n[Status] Checking complete. Next fetch countdown:")
                for remaining in range(self.fetch_interval, 0, -1):
                    mins, secs = divmod(remaining, 60)
                    print(f"[Countdown] Next fetch in: {mins:02d}:{secs:02d}", end='\r')
                    await asyncio.sleep(1)
                print("\n" + "-" * 60)  # Clear the line after countdown
                
            except Exception as e:
                logger.error(f"⚠️ Critical error: {str(e)}", exc_info=True)
                await asyncio.sleep(60)

    async def close(self):
        """Clean up when bot closes"""
        self.save_posted_articles()
        self.save_posted_titles()
        if self.session:
            await self.session.close()
        print("\n" + "=" * 60)
        print("Ground News Bot shutting down...".center(60))
        print(f"Shutdown Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(60))
        print("=" * 60)
        await super().close()

# Run the bot
if __name__ == "__main__":
    # Get user settings first
    user_settings = get_user_settings()
    
    # Create bot instance
    intents = discord.Intents.default()
    bot = NewsBot(intents=intents, user_settings=user_settings)
    
    # Display professional intro
    bot.display_intro()
    
    try:
        print("[Status] Starting Ground News Bot...")
        bot.run(os.getenv('DISCORD_TOKEN'))
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Bot stopped by user".center(60))
        print(f"Shutdown Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(60))
        print("=" * 60)
        os._exit(0)