@echo off
title CS2 Discord Bot
color 0A

echo ========================================
echo    CS2 Discord Bot Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

echo [INFO] Python found!
echo.

REM Check if required packages are installed
echo [INFO] Checking dependencies...
pip show discord.py >nul 2>&1
if errorlevel 1 (
    echo [WARN] discord.py not found. Installing dependencies...
    pip install discord.py feedparser python-dotenv
    echo.
)

REM Check if .env file exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo.
    echo Please create a .env file in the same folder with:
    echo DISCORD_TOKEN=your_token_here
    echo CHANNEL_ID=your_channel_id
    echo LOG_CHANNEL_ID=your_log_channel_id
    echo CHECK_INTERVAL=10
    echo.
    pause
    exit /b
)

echo [INFO] .env file found!
echo.

REM Check if bot file exists
if not exist "cs2_bot.py" (
    echo [ERROR] cs2_bot.py not found!
    echo Please make sure the bot script is in the same folder as this batch file.
    echo.
    pause
    exit /b
)

echo [INFO] Starting bot...
echo ========================================
echo.

REM Run the bot
python cs2_bot.py

REM If bot exits, pause so you can see the error
echo.
echo ========================================
echo [INFO] Bot has stopped.
echo.
pause
