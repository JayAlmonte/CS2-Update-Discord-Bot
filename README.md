# 🎮 CS2 Discord Update Bot

A sophisticated Discord bot that automatically monitors and posts Counter-Strike 2 updates from Steam's official RSS feed. Features beautiful embed formatting, automatic update detection, and comprehensive admin controls.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Discord.py](https://img.shields.io/badge/discord.py-2.0+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- **🔄 Automatic Update Detection** - Monitors Steam RSS feed at configurable intervals
- **🎨 Beautiful Embeds** - Professionally formatted updates with CS2 branding
- **📝 Smart Text Formatting** - Breaks down patch notes into readable sections
- **💾 Persistent Tracking** - Remembers posted updates to avoid duplicates
- **🤖 Auto-Post Mode** - Automatically posts new updates as they're detected
- **🛠️ Admin Commands** - Full control over bot behavior and posting
- **📊 Status Monitoring** - Real-time status updates and logging
- **⚡ Rate Limit Protection** - Built-in delays to prevent Discord rate limiting

## 📸 Screenshots

### Update Post Example
The bot posts updates with rich embeds featuring:
- Color-coded update types (Patch, Event, Major Update)
- CS2 logo thumbnail
- Formatted update notes with proper line breaks
- Direct links to Steam news
- Timestamp and Steam branding

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Discord Bot Token ([Get one here](https://discord.com/developers/applications))
- Discord Server with Admin permissions

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/cs2-discord-bot.git
cd cs2-discord-bot
```

2. **Install dependencies**
```bash
pip install discord.py feedparser python-dotenv
```

3. **Create a `.env` file** in the project root:
```env
DISCORD_TOKEN=your_bot_token_here
CHANNEL_ID=your_channel_id_here
LOG_CHANNEL_ID=your_log_channel_id_here
CHECK_INTERVAL=10
```

4. **Enable Discord Developer Mode** (to get Channel IDs):
   - Open Discord → User Settings → Advanced → Enable "Developer Mode"
   - Right-click any channel → Copy ID

5. **Configure Bot Intents** in Discord Developer Portal:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Select your application → Bot section
   - Enable these Privileged Gateway Intents:
     - ✅ MESSAGE CONTENT INTENT (Required!)
     - ✅ SERVER MEMBERS INTENT
     - ✅ PRESENCE INTENT

6. **Invite bot to your server**:
   - Go to OAuth2 → URL Generator
   - Select scopes: `bot`
   - Select permissions: 
     - Send Messages
     - Embed Links
     - Read Message History
   - Copy and open the generated URL

### Running the Bot

**Windows:**
```bash
# Double-click run_bot.bat
# OR
python cs2_bot.py
```

**Linux/Mac:**
```bash
python3 cs2_bot.py
```

## 📚 Commands

All commands use the `!` prefix. Admin commands require Discord Administrator permission.

### 🤖 Auto-Post Control

| Command | Description | Admin |
|---------|-------------|-------|
| `!autopost` | Show current auto-post status | ❌ |
| `!autopost on` | Enable automatic posting of new updates | ✅ |
| `!autopost off` | Disable automatic posting | ✅ |
| `!scanall` | Scan entire feed and post all unposted updates | ✅ |

### 🔍 Manual Operations

| Command | Description | Admin |
|---------|-------------|-------|
| `!checknow` | Manually trigger an update check | ✅ |
| `!fetchlatest <number>` | Fetch and post the latest N updates (1-10) | ✅ |
| `!testfeed` | Test if Steam RSS feed is accessible | ❌ |

### ⚙️ Configuration

| Command | Description | Admin |
|---------|-------------|-------|
| `!setchannel #channel` | Set the channel for posting updates | ✅ |
| `!setlogchannel #channel` | Set the channel for bot logs | ✅ |
| `!setinterval <minutes>` | Set check interval (in minutes) | ✅ |

### 📊 Monitoring

| Command | Description | Admin |
|---------|-------------|-------|
| `!status` | Show bot status, next check time, and tracking info | ❌ |
| `!cleartracking` | Clear all tracked updates (forces repost of all) | ✅ |
| `!help` | Display all available commands | ❌ |

## 🎯 Usage Examples

### Basic Setup
```
!setchannel #cs2-updates
!setlogchannel #bot-logs
!setinterval 10
!autopost on
```

### Force Post Latest Update
```
!fetchlatest 1
```

### Post All Unposted Updates
```
!scanall
```

### Check Bot Status
```
!status
```

### Disable Auto-Posting (Manual Mode)
```
!autopost off
# Now updates will be detected but not posted
# Use !fetchlatest to post manually
```

## 🔧 Configuration Details

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DISCORD_TOKEN` | Your Discord bot token | ✅ Yes | N/A |
| `CHANNEL_ID` | Channel ID for posting updates | ✅ Yes | N/A |
| `LOG_CHANNEL_ID` | Channel ID for bot logs | ❌ No | None |
| `CHECK_INTERVAL` | Minutes between update checks | ❌ No | 10 |

### Files Generated

- **`posted_updates.json`** - Tracks posted update URLs to prevent duplicates
- **`cs2_bot.log`** - Detailed logging of bot operations

## 🎨 Embed Formatting

The bot automatically formats updates with:

- **Color Coding:**
  - 🟢 Green: Small updates/patches
  - 🔵 Blue: Patch notes/hotfixes
  - 🟣 Purple: Events/operations
  - 🟠 Orange: Major updates

- **Smart Text Formatting:**
  - Automatic sentence breaks for readability
  - Bullet point detection and formatting
  - Section header highlighting
  - Code block background for easy reading

- **Information Fields:**
  - TYPE: Update category
  - POSTED: Timestamp
  - GAME: Counter-Strike 2 info
  - UPDATE NOTES: Formatted patch notes

## 🐛 Troubleshooting

### Bot doesn't respond to commands
- Verify MESSAGE CONTENT INTENT is enabled in Discord Developer Portal
- Check bot has proper permissions in your server
- Ensure bot is online (check console for connection messages)

### No updates are being posted
- Run `!testfeed` to verify Steam RSS feed is accessible
- Check `!status` to see if auto-post is enabled
- Use `!scanall` to force post all unposted updates
- Verify CHANNEL_ID is correct in `.env` file

### "Error parsing entry date" messages
- This is normal for some Steam updates with malformed dates
- The bot will still post these updates

### Updates posted multiple times
- This shouldn't happen with proper tracking
- If it does, check if `posted_updates.json` is being created/updated
- Try `!cleartracking` and let bot rebuild tracking

### Bot crashes or closes immediately
- Check all required dependencies are installed
- Verify `.env` file exists and has correct formatting
- Check `cs2_bot.log` for error messages
- Use `run_bot.bat` (Windows) to see error messages before window closes

## 🔐 Security Best Practices

- ⚠️ **Never commit your `.env` file** to version control
- ⚠️ **Keep your bot token secret** - if exposed, reset it immediately
- ✅ Add `.env` to your `.gitignore` file
- ✅ Use environment variables for sensitive data
- ✅ Limit bot permissions to only what's needed

## 📝 Development

### Project Structure
```
cs2-discord-bot/
├── cs2_bot.py              # Main bot application
├── run_bot.bat             # Windows launcher script
├── .env                    # Environment configuration (not in repo)
├── .env.example            # Example configuration file
├── posted_updates.json     # Tracking file (auto-generated)
├── cs2_bot.log            # Log file (auto-generated)
├── README.md              # This file
└── LICENSE                # MIT License
```

### Adding New Features

The bot is modular and easy to extend:

1. **Custom Embed Formatting**: Modify `create_update_embed()` function
2. **Text Processing**: Edit `format_update_notes()` function
3. **New Commands**: Add using `@bot.command()` decorator
4. **Different RSS Feeds**: Change `FEED_URL` constant

### Testing

```bash
# Test feed connectivity
!testfeed

# Test update posting
!fetchlatest 1

# Check bot status
!status
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Uses [feedparser](https://github.com/kurtmckee/feedparser) for RSS parsing
- Steam RSS feed provided by Valve Corporation
- Counter-Strike 2 is a trademark of Valve Corporation

## 📧 Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter)

Project Link: [https://github.com/yourusername/cs2-discord-bot](https://github.com/yourusername/cs2-discord-bot)

## 🗺️ Roadmap

- [ ] Web dashboard for bot management
- [ ] Support for multiple games/RSS feeds
- [ ] Custom embed templates
- [ ] Webhook support
- [ ] Database integration for better tracking
- [ ] Multi-server support with per-server configuration
- [ ] Slash commands support

## ⭐ Star History

If you find this project useful, please consider giving it a star! It helps others discover the project.

---

Made with ❤️ for the CS2 community