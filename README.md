# 🕒 Pomodoro Timer
A lightweight Pomodoro timer for Windows with optional Spotify and Home Assistant integrations.

## ✅ Core Features
- Start and stop a Pomodoro timer directly from the system tray.
- Adjust timer duration on the fly.

## 🔧 Optional Integrations
These features require additional configuration via a `.env` secrets file:
- 🔁 Sync work and pause durations via Firebase Realtime Database.
- 🎵 Auto-play a Spotify playlist at the start of work or break periods.
- 🪟 Hide all windows on break and restore them when resuming work.
- 🏠 Trigger Home Assistant services through webhooks.
- ✅ Update your “Arbeiten” habit on TickTick.


## 📦 Installation

### 1. Clone the Repository

git clone https://github.com/OliverStoll/Productivity-Timer-Systray.git
cd Productivity-Timer-Systray

### 2. Create a `.env` File for Optional Features

To enable Spotify, Firebase, or TickTick integrations, create a `.env` file in the root directory with the following keys:

```
FIREBASE_DB_URL=your_firebase_url  
SPOTIFY_CLIENT_ID=your_spotify_client_id  
SPOTIFY_CLIENT_SECRET=your_spotify_secret  
SPOTIFY_DEVICE_NAME=name_of_spotify_device  
TICKTICK_USERNAME=your_ticktick_email  
TICKTICK_PASSWORD=your_ticktick_password
```

#### 🔗 Resources for Credentials
- [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- [Firebase Console](https://firebase.google.com/)  
  Use the Realtime Database (free tier is sufficient)

The app will still function without this file but without the enhanced features.


## 🛠️ Build the Executables

### Set Up the Environment

pip install poetry  
poetry install --no-root

### Build the Pomodoro App

```
pyinstaller -i ../res/pomodoro.ico -n Pomo --onefile --noconsole \
--add-data "../config.yml;." --add-data "../.env;." \
--add-data "../res/*;res/" --specpath build/ ./src/pomodoro.py
```

### Optional: Build Spotify Cleaner Script

```
pyinstaller -n Close_Spotify_On_Startup --onefile --noconsole \
--specpath build/ ./src/close_spotify_startup.py
```


## 🚀 Windows Setup (Recommended)
1. Run `Pomo.exe` once to register the system tray icon.
2. Enable the icon under  
   `Settings → Personalization → Taskbar → Other system tray icons`.
3. Pin the app to the Start menu for quick access.
4. To auto-start at boot, create a shortcut and place it in the Startup folder:  
   Press `Win + R`, enter `shell:startup`, and drop the shortcut there.
