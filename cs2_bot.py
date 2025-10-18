import feedparser
import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import logging
from typing import Set, Optional
import html

# Configuration
FEED_URL = "https://store.steampowered.com/feeds/news/app/730/"
POSTED_UPDATES_FILE = "posted_updates.json"
LOG_FILE = "cs2_bot.log"

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 10))

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Global state
posted_updates: Set[str] = set()
last_check_time = datetime.now(timezone.utc) - timedelta(minutes=CHECK_INTERVAL)
update_lock = asyncio.Lock()
target_channel_id = CHANNEL_ID
log_channel_id = LOG_CHANNEL_ID
check_interval = CHECK_INTERVAL
auto_post_enabled = True  # Auto-post feature enabled by default


def load_posted_updates() -> Set[str]:
    """Load previously posted update links from file."""
    if os.path.exists(POSTED_UPDATES_FILE):
        try:
            with open(POSTED_UPDATES_FILE, "r") as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            logging.error("Failed to load posted updates file. Starting fresh.")
    return set()


def save_posted_updates():
    """Save posted update links to file."""
    try:
        with open(POSTED_UPDATES_FILE, "w") as f:
            json.dump(list(posted_updates), f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save posted updates: {e}")


def clean_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    text = html.unescape(text)
    # Remove common HTML tags
    import re
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def format_update_notes(text: str, max_length: int = 900) -> str:
    """Format update notes with proper line breaks and structure for readability."""
    if not text:
        return ""
    
    # Replace common separators with line breaks
    text = text.replace('. ', '.\n\n')  # Double line break after sentences
    text = text.replace('! ', '!\n\n')  # Double line break after exclamations
    text = text.replace('? ', '?\n\n')  # Double line break after questions
    
    # Split into lines
    lines = text.split('\n')
    formatted_lines = []
    current_length = 0
    
    for line in lines:
        line = line.strip()
        
        # Check if adding this line would exceed max length
        if current_length + len(line) + 2 > max_length:
            formatted_lines.append('')
            formatted_lines.append('...')
            break
        
        if not line:
            formatted_lines.append('')  # Keep empty lines for spacing
            current_length += 1
            continue
        
        # Detect and format list items
        if any(line.startswith(prefix) for prefix in ['-', '•', '*', '·', '+']):
            # Clean up the bullet point
            line = line.lstrip('-•*·+').strip()
            formatted_line = f"  • {line}"
            formatted_lines.append(formatted_line)
            formatted_lines.append('')  # Add space after bullet
            current_length += len(formatted_line) + 1
        # Detect section headers (short lines with colons or all caps)
        elif (line.endswith(':') and len(line) < 60) or (line.isupper() and len(line) < 50 and len(line) > 5):
            # Add spacing before and after headers
            formatted_lines.append('')
            formatted_line = f"[ {line} ]"
            formatted_lines.append(formatted_line)
            formatted_lines.append('')
            current_length += len(formatted_line) + 2
        # Detect if line looks like a title/header (short and ends with period or no punctuation)
        elif len(line) < 80 and (line[0].isupper() or line.startswith('[')):
            formatted_lines.append(line)
            formatted_lines.append('')
            current_length += len(line) + 1
        # Regular lines
        else:
            formatted_lines.append(line)
            current_length += len(line) + 1
    
    # Join lines
    result = '\n'.join(formatted_lines)
    
    # Clean up excessive line breaks (max 3 consecutive)
    while '\n\n\n\n' in result:
        result = result.replace('\n\n\n\n', '\n\n\n')
    
    return result.strip()


def create_update_embed(entry) -> discord.Embed:
    """Create a rich embed for a CS2 update."""
    title = entry.title[:256]  # Discord title limit
    raw_description = clean_html(entry.summary)
    
    # Parse published time - handle timezone awareness properly
    try:
        published_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    except Exception as e:
        logging.warning(f"Error parsing date: {e}, using current time")
        published_time = datetime.now(timezone.utc)
    
    # Format the date nicely
    date_str = published_time.strftime("%a, %B %d, %Y @ %I:%M %p EDT")
    
    # Determine update type from title
    title_lower = title.lower()
    if "update" in title_lower and any(word in title_lower for word in ["major", "big", "release"]):
        update_type = "📰 **SMALL UPDATE / PATCH NOTES**"
        color = 0x5B8C5A  # Green
    elif "patch" in title_lower or "hotfix" in title_lower:
        update_type = "🔧 **PATCH NOTES**"
        color = 0x4A90E2  # Blue
    elif "event" in title_lower or "operation" in title_lower:
        update_type = "🎉 **EVENT**"
        color = 0x9B59B6  # Purple
    else:
        update_type = "📰 **SMALL UPDATE / PATCH NOTES**"
        color = 0x5B8C5A  # Green
    
    # Create the embed with dark theme
    embed = discord.Embed(
        title=title,
        url=entry.link,
        color=color,
        timestamp=published_time
    )
    
    # Add CS2 logo thumbnail
    embed.set_thumbnail(
        url="https://cdn.cloudflare.steamstatic.com/apps/csgo/images/csgo_react/social/cs2.jpg"
    )
    
    # Add update type field (max 1024 chars)
    embed.add_field(
        name="TYPE",
        value=update_type[:1024],
        inline=True
    )
    
    # Add posted date field (max 1024 chars)
    embed.add_field(
        name="POSTED",
        value=date_str[:1024],
        inline=True
    )
    
    # Add game field (max 1024 chars)
    embed.add_field(
        name="GAME",
        value="💎 **Counter-Strike 2**\n*Free To Play*",
        inline=False
    )
    
    # Format and add description with strict length limits
    if raw_description:
        # Format the description with proper line breaks (max 900 chars to be safe)
        formatted_description = format_update_notes(raw_description, max_length=900)
        
        # Add the description in a code block for the dark background
        # Discord field value limit is 1024 characters including the code block markers
        code_block_content = formatted_description[:1014]  # Leave room for ```\n and \n```
        
        embed.add_field(
            name="📋 UPDATE NOTES",
            value=f"```\n{code_block_content}\n```",
            inline=False
        )
    
    # Set footer with Steam branding
    embed.set_footer(
        text="Steam News • Counter-Strike 2 • " + published_time.strftime("%m/%d/%Y %I:%M %p"),
        icon_url="https://cdn.cloudflare.steamstatic.com/apps/csgo/images/csgo_react//global/logo_cs_sm.png"
    )
    
    return embed


@bot.event
async def on_ready():
    """Bot startup event."""
    global posted_updates, last_check_time
    posted_updates = load_posted_updates()
    
    # Set last_check_time to 24 hours ago on first startup
    # This prevents posting ALL historical updates
    if not posted_updates:
        last_check_time = datetime.now(timezone.utc) - timedelta(hours=24)
    else:
        # If we have posted updates, set to now minus check interval
        last_check_time = datetime.now(timezone.utc) - timedelta(minutes=CHECK_INTERVAL)
    
    logging.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    logging.info(f"Loaded {len(posted_updates)} previously posted updates")
    logging.info(f"Last check time set to: {last_check_time}")
    
    # Start the update checker
    if not check_for_updates.is_running():
        check_for_updates.start()
    
    # Send startup message to log channel
    if log_channel_id:
        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(
                title="✅ CS2 Bot Online",
                description=f"Monitoring for Counter-Strike 2 updates every {check_interval} minutes",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Tracked Updates", value=f"{len(posted_updates)} posts", inline=True)
            await log_channel.send(embed=embed)
        else:
            logging.warning(f"Log channel ID {log_channel_id} not found")


@tasks.loop(minutes=CHECK_INTERVAL)
async def check_for_updates():
    """Periodically check for new CS2 updates."""
    global last_check_time
    
    async with update_lock:
        logging.info("Checking for CS2 updates...")
        
        try:
            # Parse the RSS feed
            feed = feedparser.parse(FEED_URL)
            
            if not feed.entries:
                logging.warning("No entries found in feed")
                return
            
            logging.info(f"Found {len(feed.entries)} total entries in feed")
            new_updates = []
            
            # Check each entry for new updates
            for entry in feed.entries:
                # Skip if already posted
                if entry.link in posted_updates:
                    logging.debug(f"Skipping already posted: {entry.title}")
                    continue
                
                # This is a new update that hasn't been posted
                logging.info(f"Found NEW unposted update: {entry.title}")
                new_updates.append(entry)
            
            logging.info(f"Found {len(new_updates)} new updates to post")
            
            # Auto-post new updates if enabled
            if new_updates and auto_post_enabled:
                channel = bot.get_channel(target_channel_id)
                
                if not channel:
                    logging.error(f"Target channel ID {target_channel_id} not found")
                    return
                
                # Sort by date (oldest first)
                try:
                    new_updates.sort(key=lambda x: datetime(*x.published_parsed[:6], tzinfo=timezone.utc))
                except:
                    pass  # Keep original order if sorting fails
                
                logging.info(f"Auto-posting {len(new_updates)} new update(s)...")
                
                for i, update in enumerate(new_updates, 1):
                    try:
                        embed = create_update_embed(update)
                        # Send with update counter
                        await channel.send(
                            content=f"🆕 **New CS2 Update Detected!** ({i}/{len(new_updates)})",
                            embed=embed
                        )
                        posted_updates.add(update.link)
                        logging.info(f"Successfully posted update {i}/{len(new_updates)}: {update.title}")
                        
                        # Small delay to avoid rate limits
                        await asyncio.sleep(2)
                    except Exception as e:
                        logging.error(f"Failed to post update '{update.title}': {e}")
                
                # Save updated list
                save_posted_updates()
                logging.info(f"Saved {len(posted_updates)} posted updates to file")
                
                # Log to log channel
                if log_channel_id:
                    log_channel = bot.get_channel(log_channel_id)
                    if log_channel:
                        embed = discord.Embed(
                            title="✅ Auto-Posted Updates",
                            description=f"Automatically posted {len(new_updates)} new CS2 update(s)",
                            color=discord.Color.green()
                        )
                        await log_channel.send(embed=embed)
            elif new_updates and not auto_post_enabled:
                logging.info(f"Auto-post is DISABLED. {len(new_updates)} updates pending.")
                # Notify in log channel that updates are waiting
                if log_channel_id:
                    log_channel = bot.get_channel(log_channel_id)
                    if log_channel:
                        await log_channel.send(
                            f"⚠️ {len(new_updates)} new update(s) found but auto-post is disabled. Use `!fetchlatest` to post them."
                        )
            else:
                logging.info("No new updates found")
            
            # Update last check time
            last_check_time = datetime.now(timezone.utc)
            logging.info(f"Last check time updated to: {last_check_time}")
            
        except Exception as e:
            logging.error(f"Error checking for updates: {e}", exc_info=True)


@check_for_updates.before_loop
async def before_check_updates():
    """Wait until bot is ready before starting the loop."""
    await bot.wait_until_ready()


@bot.command(name="setchannel")
@commands.has_permissions(administrator=True)
async def set_channel(ctx, channel: discord.TextChannel):
    """Set the channel where updates will be posted."""
    global target_channel_id
    target_channel_id = channel.id
    
    embed = discord.Embed(
        title="✅ Channel Updated",
        description=f"Updates will now be posted to {channel.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    logging.info(f"Update channel changed to #{channel.name} by {ctx.author}")


@bot.command(name="setlogchannel")
@commands.has_permissions(administrator=True)
async def set_log_channel(ctx, channel: discord.TextChannel):
    """Set the channel for bot logs."""
    global log_channel_id
    log_channel_id = channel.id
    
    embed = discord.Embed(
        title="✅ Log Channel Updated",
        description=f"Logs will now be posted to {channel.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    logging.info(f"Log channel changed to #{channel.name} by {ctx.author}")


@bot.command(name="setinterval")
@commands.has_permissions(administrator=True)
async def set_interval(ctx, minutes: int):
    """Set the interval for checking updates (in minutes)."""
    global check_interval
    
    if minutes < 1:
        await ctx.send("❌ Interval must be at least 1 minute")
        return
    
    if minutes > 1440:  # 24 hours
        await ctx.send("❌ Interval cannot exceed 1440 minutes (24 hours)")
        return
    
    check_interval = minutes
    check_for_updates.change_interval(minutes=check_interval)
    
    embed = discord.Embed(
        title="✅ Interval Updated",
        description=f"Now checking for updates every {minutes} minutes",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    logging.info(f"Check interval changed to {minutes} minutes by {ctx.author}")


@bot.command(name="cleartracking")
@commands.has_permissions(administrator=True)
async def clear_tracking(ctx):
    """Clear all tracked updates (use with caution!)."""
    global posted_updates
    old_count = len(posted_updates)
    posted_updates.clear()
    save_posted_updates()
    await ctx.send(f"✅ Cleared {old_count} tracked updates. Bot will now post all updates from the last 24 hours.")
    logging.info(f"Tracking cleared by {ctx.author}")


@bot.command(name="status")
async def status(ctx):
    """Show bot status and next check time."""
    next_check = last_check_time + timedelta(minutes=check_interval)
    time_until = next_check - datetime.now(timezone.utc)
    
    minutes, seconds = divmod(int(time_until.total_seconds()), 60)
    
    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="Update Channel",
        value=f"<#{target_channel_id}>",
        inline=True
    )
    
    embed.add_field(
        name="Check Interval",
        value=f"{check_interval} minutes",
        inline=True
    )
    
    embed.add_field(
        name="Auto-Post",
        value="✅ Enabled" if auto_post_enabled else "❌ Disabled",
        inline=True
    )
    
    embed.add_field(
        name="Next Check",
        value=f"In {minutes}m {seconds}s",
        inline=True
    )
    
    embed.add_field(
        name="Updates Tracked",
        value=f"{len(posted_updates)} posts",
        inline=True
    )
    
    embed.add_field(
        name="Last Check",
        value=last_check_time.strftime('%H:%M:%S UTC'),
        inline=True
    )
    
    await ctx.send(embed=embed)


@bot.command(name="checknow")
@commands.has_permissions(administrator=True)
async def check_now(ctx):
    """Manually trigger an update check."""
    await ctx.send("🔍 Checking for updates...")
    
    try:
        # Temporarily allow all updates by setting last_check_time far in the past
        global last_check_time
        old_time = last_check_time
        last_check_time = datetime.now(timezone.utc) - timedelta(days=365)
        
        await check_for_updates()
        
        # Restore the time
        last_check_time = old_time
        
        await ctx.send(f"✅ Check complete! Currently tracking {len(posted_updates)} updates.")
    except Exception as e:
        await ctx.send(f"❌ Error during check: {e}")
        logging.error(f"Manual check error: {e}", exc_info=True)


@bot.command(name="fetchlatest")
@commands.has_permissions(administrator=True)
async def fetch_latest(ctx, count: int = 1):
    """Fetch and post the latest N updates from Steam (even if already posted)."""
    if count < 1 or count > 10:
        await ctx.send("❌ Please specify a number between 1 and 10")
        return
    
    await ctx.send(f"🔍 Fetching the latest {count} update(s) from Steam...")
    
    try:
        # Parse the RSS feed
        feed = feedparser.parse(FEED_URL)
        
        if not feed.entries:
            await ctx.send("❌ No entries found in Steam feed")
            return
        
        # Get the latest entries
        latest_entries = feed.entries[:count]
        channel = bot.get_channel(target_channel_id)
        
        if not channel:
            await ctx.send(f"❌ Target channel not found (ID: {target_channel_id})")
            return
        
        posted_count = 0
        for entry in latest_entries:
            try:
                embed = create_update_embed(entry)
                await channel.send(
                    content=f"📢 **Latest CS2 Update (Manual Fetch)**",
                    embed=embed
                )
                # Add to posted updates to avoid duplicates
                posted_updates.add(entry.link)
                posted_count += 1
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Failed to post entry: {e}")
                await ctx.send(f"⚠️ Failed to post '{entry.title}': {e}")
        
        # Save updated list
        save_posted_updates()
        await ctx.send(f"✅ Posted {posted_count} update(s) and saved to tracking file!")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        logging.error(f"Fetch latest error: {e}", exc_info=True)


@bot.command(name="autopost")
@commands.has_permissions(administrator=True)
async def toggle_autopost(ctx, enabled: str = None):
    """Enable or disable automatic posting of new updates."""
    global auto_post_enabled
    
    if enabled is None:
        # Just show current status
        status = "✅ ENABLED" if auto_post_enabled else "❌ DISABLED"
        embed = discord.Embed(
            title="🤖 Auto-Post Status",
            description=f"Automatic posting is currently: **{status}**",
            color=discord.Color.green() if auto_post_enabled else discord.Color.red()
        )
        embed.add_field(
            name="Usage",
            value="• `!autopost on` - Enable auto-posting\n• `!autopost off` - Disable auto-posting",
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    if enabled.lower() in ['on', 'true', 'enable', 'yes', '1']:
        auto_post_enabled = True
        embed = discord.Embed(
            title="✅ Auto-Post Enabled",
            description="The bot will now automatically post any new CS2 updates it detects!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        logging.info(f"Auto-post enabled by {ctx.author}")
    elif enabled.lower() in ['off', 'false', 'disable', 'no', '0']:
        auto_post_enabled = False
        embed = discord.Embed(
            title="⚠️ Auto-Post Disabled",
            description="The bot will detect updates but NOT post them automatically. Use `!fetchlatest` to post manually.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        logging.info(f"Auto-post disabled by {ctx.author}")
    else:
        await ctx.send("❌ Invalid option. Use `on` or `off`")


@bot.command(name="scanall")
@commands.has_permissions(administrator=True)
async def scan_all(ctx):
    """Scan the entire RSS feed and auto-post any unposted updates."""
    await ctx.send("🔍 Scanning entire Steam RSS feed for unposted updates...")
    
    try:
        feed = feedparser.parse(FEED_URL)
        
        if not feed.entries:
            await ctx.send("❌ No entries found in feed")
            return
        
        # Find all unposted updates
        unposted = [entry for entry in feed.entries if entry.link not in posted_updates]
        
        if not unposted:
            await ctx.send(f"✅ All {len(feed.entries)} updates in the feed have already been posted!")
            return
        
        await ctx.send(f"📊 Found {len(unposted)} unposted update(s) out of {len(feed.entries)} total. Posting now...")
        
        channel = bot.get_channel(target_channel_id)
        if not channel:
            await ctx.send(f"❌ Target channel not found (ID: {target_channel_id})")
            return
        
        # Sort by date (oldest first)
        try:
            unposted.sort(key=lambda x: datetime(*x.published_parsed[:6], tzinfo=timezone.utc))
        except:
            pass
        
        posted_count = 0
        for i, entry in enumerate(unposted, 1):
            try:
                embed = create_update_embed(entry)
                await channel.send(
                    content=f"🆕 **New CS2 Update!** ({i}/{len(unposted)})",
                    embed=embed
                )
                posted_updates.add(entry.link)
                posted_count += 1
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"Failed to post entry: {e}")
                await ctx.send(f"⚠️ Failed to post update {i}: {e}")
        
        # Save updated list
        save_posted_updates()
        await ctx.send(f"✅ Successfully posted {posted_count} update(s)! Now tracking {len(posted_updates)} total updates.")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")
        logging.error(f"Scan all error: {e}", exc_info=True)


@bot.command(name="testfeed")
async def test_feed(ctx):
    """Test if the Steam RSS feed is accessible."""
    await ctx.send("🔍 Testing Steam RSS feed...")
    
    try:
        feed = feedparser.parse(FEED_URL)
        
        if not feed.entries:
            await ctx.send("❌ Feed is empty or inaccessible")
            return
        
        latest = feed.entries[0]
        
        embed = discord.Embed(
            title="✅ Feed Test Successful",
            color=discord.Color.green()
        )
        embed.add_field(name="Total Entries", value=str(len(feed.entries)), inline=True)
        embed.add_field(name="Latest Update", value=latest.title[:100], inline=False)
        embed.add_field(name="Published", value=latest.published, inline=False)
        embed.add_field(name="Link", value=latest.link, inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Feed test failed: {e}")
        logging.error(f"Feed test error: {e}", exc_info=True)


@bot.command(name="help")
async def help_command(ctx):
    """Show available commands."""
    embed = discord.Embed(
        title="🎮 CS2 Update Bot - Commands",
        description="Monitor Counter-Strike 2 updates from Steam",
        color=discord.Color.orange()
    )
    
    embed.add_field(
        name="🤖 !autopost <on/off>",
        value="Enable/disable automatic posting of new updates",
        inline=False
    )
    
    embed.add_field(
        name="🔍 !scanall",
        value="Scan entire feed and post all unposted updates (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="📢 !setchannel #channel",
        value="Set the channel for posting updates (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="📋 !setlogchannel #channel",
        value="Set the channel for bot logs (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="⏱️ !setinterval <minutes>",
        value="Set check interval in minutes (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="🔍 !checknow",
        value="Manually check for updates now (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="📥 !fetchlatest <number>",
        value="Fetch and post the latest N updates (1-10) (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="🧪 !testfeed",
        value="Test if Steam RSS feed is accessible",
        inline=False
    )
    
    embed.add_field(
        name="🗑️ !cleartracking",
        value="Clear all tracked updates (Admin)",
        inline=False
    )
    
    embed.add_field(
        name="📊 !status",
        value="Show bot status and next check time",
        inline=False
    )
    
    embed.add_field(
        name="❓ !help",
        value="Show this help message",
        inline=False
    )
    
    embed.set_footer(text="Created for CS2 community")
    
    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided")
    else:
        logging.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while executing the command")


def main():
    """Main entry point."""
    if not DISCORD_TOKEN:
        logging.error("DISCORD_TOKEN not found in environment variables")
        return
    
    if not CHANNEL_ID:
        logging.error("CHANNEL_ID not found in environment variables")
        return
    
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")


if __name__ == "__main__":
    main()