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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix Unicode logging for Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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

class NewsBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.posted_articles = self.load_posted_articles()
        self.posted_titles = self.load_posted_titles()
        self.channel_id = int(os.getenv('CHANNEL_ID'))
        self.session = None
        self.next_fetch_time = datetime.now()
        self.fetch_interval = 300  # 5 minutes
        self.title_similarity_threshold = 0.85  # 85% similarity blocks duplicate
        
    async def setup_hook(self):
        # Create a persistent HTTP session
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

    def display_intro(self):
        """Display professional ASCII art intro"""
        intro = r"""
  ██████  ██████   ██████  ██    ██ ███    ██ ██████      ███    ██ ███████ ██     ██ ███████ 
 ██       ██   ██ ██    ██ ██    ██ ████   ██ ██   ██     ████   ██ ██      ██     ██ ██      
 ██   ███ ██████  ██    ██ ██    ██ ██ ██  ██ ██   ██     ██ ██  ██ █████   ██  █  ██ ███████ 
 ██    ██ ██   ██ ██    ██ ██    ██ ██  ██ ██ ██   ██     ██  ██ ██ ██      ██ ███ ██      ██ 
 ██████  ██   ██  ██████   ██████  ██   ████ ██████      ██   ████ ███████  ███ ███  ███████ 
        """
        print(intro)
        print("\n" + "=" * 60)
        print("GROUND NEWS DISCORD BOT".center(60))
        print("Professional News Aggregation Solution".center(60))
        print("=" * 60)
        print(f"Developed by: Jordan Ilaréguy".center(60))
        print(f"Version: 2.0".center(60))
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(60))
        print("=" * 60 + "\n")
        print("Initializing news monitoring service...\n")

    def print_next_fetch(self):
        """Print next fetch time to console"""
        now = datetime.now()
        if now < self.next_fetch_time:
            seconds_left = (self.next_fetch_time - now).seconds
            minutes, seconds = divmod(seconds_left, 60)
            print(f"[Status] Next fetch in: {minutes:02d}:{seconds:02d}", end='\r')
        else:
            print("\n[Status] Fetching now...")

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

    async def news_checker(self):
        await self.wait_until_ready()
        channel = self.get_channel(self.channel_id)
        if not channel:
            logger.error(f"Channel {self.channel_id} not found!")
            return
            
        await channel.send("📰 **Ground News Bot Activated!** Monitoring news feed...")
        
        while not self.is_closed():
            try:
                # Set next fetch time and print status
                self.next_fetch_time = datetime.now() + timedelta(seconds=self.fetch_interval)
                logger.info("Starting news feed check...")
                
                # Display fetching status
                print("\n[Status] Fetching latest news...")
                
                new_count = 0
                
                for source, url in RSS_FEEDS.items():
                    feed = await self.async_fetch_feed(url)
                    if not feed or not feed.entries:
                        logger.warning(f"⚠️ Empty feed from {source}")
                        continue
                    
                    logger.info(f"📰 Found {len(feed.entries)} articles from {source}")
                    
                    # Process from oldest to newest to get latest articles last
                    for entry in reversed(feed.entries):
                        article_url = entry.get('link', '')
                        title = entry.get('title', 'No title')[:250]
                        
                        if not article_url:
                            logger.warning(f"⚠️ Article missing link: {title}")
                            continue
                            
                        # Normalize URL
                        article_url = self.normalize_url(article_url)
                            
                        # Skip duplicates based on URL
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
                        
                        # Format the message with URL embedded
                        message = f"**🚨 {source.upper()} • BREAKING NEWS**\n"
                        message += f"**{title}**\n\n"
                        
                        # Add publication date if available
                        if 'published' in entry:
                            message += f"*Published: {entry.published}*\n\n"
                        elif 'updated' in entry:
                            message += f"*Updated: {entry.updated}*\n\n"
                        
                        # Add description
                        description = self.get_description(entry)
                        if description:
                            message += f"{description[:1500]}\n\n"
                        
                        # Add the article URL at the end to trigger preview
                        message += f"Read more: {article_url}"
                        
                        # Send as a single message
                        try:
                            await channel.send(message)
                            logger.info(f"✅ Posted: {title[:60]}...")
                        except discord.HTTPException as e:
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
    # Create bot instance
    intents = discord.Intents.default()
    bot = NewsBot(intents=intents)
    
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