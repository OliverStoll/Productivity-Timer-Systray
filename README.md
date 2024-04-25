# Pomodoro Timer
A Pomodoro Timer with Spotify & Home Assistant Integration.

### Features
- Start/Stop Timer
- Increase/Decrease Timer Duration
---
### Optional Features
- Cloud Storage for Work/Pause Duration
- Auto-Play Spotify Playlist on beginning of work/pause
- Hide all windows on beginning of pause and show them again on beginning of work
- Call a Home Assistant Service (via Webhook) on beginning of work/pause

# How to install

## Add Secrets File to use additional Features

To play spotify playlists on start of work and pause, and changing the timer duration while it's running) , this package needs an `.env` file in the root directory with the following content:
- `FIREBASE_DB_URL`: Link to your Firebase Realtime Database (needs to be unlocked for outside access)
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_DEVICE_NAME`: Friendly name of the Spotify Device to play music on while working. (Kept in secrets instead of config, to not be shared between different workstations by accident)
- `TICKTICK_USERNAME`: Email of the TickTick Account to use for increasing the "Arbeiten" habit count
- `TICKTICK_PASSWORD`: 

You can optain these by creating a Spotify Developer Account and a Firebase Project:
- Firebase Realtime Database (*free version*): https://firebase.google.com/
- Spotify Developer Account: https://developer.spotify.com/dashboard


When parts of the secrets are missing, the app will still work, but without the features mentioned above.

## Build App
After cloning the repository and creating the secrets file & virtual environment, run to install the dependencies and build the executable:
```shell
# Codeblock is reversed due to Pycharm bug
poetry install --no-root
pip install poetry
```
```shell
pyinstaller -i ../res/pomodoro.ico -n Pomo --onefile --noconsole --add-data "../config.yml;." --add-data "../.env;." --add-data "../res/*;res/" --specpath build/ .\src\pomodoro.py
```
```shell
pyinstaller -n Close_Spotify_On_Startup --onefile --noconsole --specpath build/ .\src\close_spotify_startup.py
```

## Setup Easy Access (*Windows*)
- Run the app once
- Display the `Pomo.exe` app in "*Taskbar-Settings -> Other system tray icons*" in the Taskbar settings
- Pin the Pomo app to the Start Menu
- Create a shortcut to the app and place it in the Startup folder (`shell:startup` path)