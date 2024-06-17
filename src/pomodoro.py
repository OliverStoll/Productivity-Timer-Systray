# fix working directory if running from a pyinstaller executable
import src._utils.distribution.pyinstaller_fix_workdir  # noqa

# global
import threading
import pystray
import os
from pystray import Menu, MenuItem as Item
from datetime import datetime
from time import sleep
from threading import Thread
from pprint import pformat

# local
from src.systray.utils import draw_icon_text, draw_icon_circle
from src._utils.common import CONFIG, secret, load_env_file, ROOT_DIR
from src._utils.logger import create_logger
from src._utils.apis.spotify import SpotifyHandler
from src._utils.apis.firebase import FirebaseHandler
from src._utils.apis.homeassistant import HomeAssistantHandler
from src._utils.system.sound import SoundHandler
from src._utils.system.programs_windows import WindowHandler
from src._utils.apis.ticktick_habits import TicktickHabitHandler

# from src._utils.system.bluetooth import bluetooth_is_enabled


POMODORO_FEATURES = {
    "Hide Windows": {
        "class": WindowHandler,
        "kwargs": {}
    },
    "Spotify": {
        "class": SpotifyHandler,
        "kwargs": {
            "device_name": secret("SPOTIFY_DEVICE_NAME"),
            "client_id": secret("SPOTIFY_CLIENT_ID"),
            "client_secret": secret("SPOTIFY_CLIENT_SECRET"),
            "redirect_uri": CONFIG["SPOTIFY"]["redirect_uri"],
            "scope": CONFIG["SPOTIFY"]["scope"],
            "cache_path": f"{os.getenv('APPDATA')}/Pomodoro/.spotify_cache"
        }
    },
    "Home Assistant": {
        "class": HomeAssistantHandler,
        "kwargs": {"base_url": "http://homeassistant.local:8123/api/webhook/"}
    },
    "Play Sound": {
        "class": SoundHandler,
        "kwargs": {"default_volume": 1}
    },
    "Habit Tracking": {
        "class": TicktickHabitHandler,
        "kwargs": {"cookies_path": f"{os.getenv('APPDATA')}/Pomodoro/.ticktick_cookies"}
    },
}


class State:
    """ Represents state of Pomodoro Timer, while containing color and webhook from config."""
    WORK = "WORK"
    PAUSE = "PAUSE"
    READY = "READY"
    DONE = "DONE"
    STARTING = "STARTING"


class PomodoroFeatureHandler:
    """
    Class to handle the different additional features of the Pomodoro Timer.

    Implements error handling as well as a toggle function to enable/disable features.
    """
    log = create_logger("Pomodoro Features")

    def __init__(self, settings: dict, firebase=None):
        self.firebase = firebase
        self.firebase_settings_ref = CONFIG["FIREBASE_REF_SETTINGS"]
        self.features: dict[str, dict] = POMODORO_FEATURES

        for feature_name, feature_info in self.features.items():
            feature_info["active"] = settings.get(feature_name, False)
            feature_info["handler"] = None
            feature_info["kwargs"] = feature_info.get("kwargs", {})
            handler_init_thread = Thread(target=self._init_feature_handler, args=(feature_name,))
            handler_init_thread.start()

    def _init_feature_handler(self, feature_name: str):
        feature_info = self.features[feature_name]
        try:
            feature_info["handler"] = feature_info["class"](**feature_info["kwargs"])
            self.log.debug(f"Initialized {feature_name} Handler")
        except Exception as e:
            self.log.warning(f"Feature handler {feature_info} not initialized: [{e}]")
            feature_info["handler"] = None

    def call(self, feature_name: str, method: str, kwargs: dict | None = None):
        """ Call the method of a feature, if it is active and initialized. """

        kwargs = kwargs if kwargs else {}
        feature_info = self.features[feature_name]
        if not feature_info["active"]:
            self.log.debug(f"Trying {feature_name}-{method}: {feature_name} is not active")
            return

        if not feature_info["handler"]:
            self.log.debug(f"Trying {feature_name}-{method}: {feature_name} is not initialized")
            return

        try:
            getattr(feature_info["handler"], method)(**kwargs)
            self.log.debug(f"Called {feature_name} method {method} with args: {kwargs}")
        except Exception as e:
            self.log.warning(f"Failed to run {feature_name} method {method}: {e}")

    def toggle_setting(self, feature_name: str):
        feature_info = self.features[feature_name]
        self.log.info(f"Toggling feature setting: {feature_name}")
        feature_info["active"] = not feature_info["active"]
        if self.firebase:
            firebase_ref = f'{self.firebase_settings_ref}/{feature_name}'
            self.firebase.set_entry(ref=firebase_ref, data=feature_info["active"])


class PomodoroMenu:
    pass


class PomodoroApp:
    log = create_logger("Pomodoro App")
    thread_lock = threading.Lock()

    def __init__(self, firebase_rtdb_url: str | None = None):
        self.log.info("\n\n\n\n\t\tSTARTING POMODORO TIMER...\n\n\n")
        secrets_path = f"{os.getenv('APPDATA')}/Pomodoro/.env"
        self._load_secrets_file(secrets_path=secrets_path)

        self.firebase = FirebaseHandler(realtime_db_url=firebase_rtdb_url)
        self.firebase_settings_ref = CONFIG["FIREBASE_REF_SETTINGS"]
        self.firebase_times_worked_ref = CONFIG["FIREBASE_REF_TIME_DONE"]
        feature_settings = CONFIG["default_settings"]["features"]
        self.feature_handler = PomodoroFeatureHandler(settings=feature_settings,
                                                      firebase=self.firebase)

        # features data
        self.sound_files = {name: f"{ROOT_DIR}/{path}" for name, path in CONFIG["SOUNDS"].items()}
        self.colors = CONFIG["COLORS"]
        self.webhooks = CONFIG["WEBHOOKS"]
        self.playlists = CONFIG["PLAYLISTS"]
        self.ticktick_habit_name = CONFIG["TICKTICK_HABIT_NAME"]

        self._init_app_with_offline_data()

        # try to load real settings from firebase
        self._init_settings_from_firebase()

        # load timer values
        self.work_timer_duration = self.settings["work_timer_duration"]
        self.pause_timer_duration = self.settings["pause_timer_duration"]
        self.daily_work_goal = self.settings["daily_work_time_goal"]
        self.current_timer_value = self.work_timer_duration
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.time_worked = self._load_time_worked_from_firebase()


        # systray app
        self.current_state = State.READY
        self.stop_timer_thread_flag = False
        self.exited_flag = False
        self.timer_thread = None
        self.update_display()
        self.log.info("Pomodoro Timer initialised.")

    # INITIALIZATION METHODS
    def _init_app_with_offline_data(self):
        self.log.debug("Starting app with stub data")
        self.settings = CONFIG["default_settings"]
        self.settings_step_size = self.settings["timer_step_size"]
        self.current_state = State.STARTING
        self.systray_app = pystray.Icon("Pomodoro Timer")
        self.time_worked = 0
        self.work_timer_duration = self.settings["work_timer_duration"]
        self.pause_timer_duration = self.settings["pause_timer_duration"]
        self.update_display()
        self.systray_app.run_detached()

    def _load_secrets_file(self, secrets_path):
        if os.path.exists(secrets_path):
            load_env_file(secrets_path)
            self.log.info(f"Loaded .env file from {secrets_path}")

    def _init_settings_from_firebase(self):
        """Load settings from firebase or use default settings if not available."""
        try:
            settings = self.firebase.get_entry(ref=self.firebase_settings_ref)
            assert isinstance(settings, dict)
            self.settings = settings
            self.log.info("Loaded settings from firebase")
        except Exception as e:
            self.log.warning(f"Can't load settings from firebase: [{e}], staying with"
                             f" default settings {CONFIG['default_settings']}")
            try:
                self.firebase.set_entry(ref=self.firebase_settings_ref, data=self.settings)
            except Exception as e:
                self.log.warning(f"Could not save default settings to Firebase: {e}")

    def _load_time_worked_from_firebase(self):
        time_worked_ref = f"{self.firebase_times_worked_ref}/{self.current_date}/time_worked"
        try:
            time_worked = int(self.firebase.get_entry(ref=time_worked_ref))
            self.log.info(f"Loaded time_worked from firebase: {time_worked}")
        except Exception as e:
            self.log.info(f"Can't load {self.current_date}: time_worked from firebase, "
                          f"setting to 0 instead (most likely a new day)")
            time_worked = 0
        return time_worked

    # BUILDING THE SYSTRAY MENU
    def update_menu(self):
        self.systray_app.menu = Menu(
            Item(
                text="Start",
                action=self.menu_button_start,
                default=(self.current_state == State.READY),
                enabled=lambda item: self.current_state != State.WORK,
            ),
            Item(
                text="Stop",
                action=self.menu_button_stop,
                default=(self.current_state == State.WORK or self.current_state == State.PAUSE),
                enabled=lambda
                    item: self.current_state != State.READY and self.current_state != State.DONE,
            ),
            Item("Settings", self._get_settings_menu())
        )

    def _get_settings_menu(self):
        time_worked = self.time_worked / self.work_timer_duration
        return Menu(
            Item(text=f"Worked {time_worked:.1f} blocks", action=None),
            Menu.SEPARATOR,
            self._get_settings_menu_change_timer_item(timer_name="WORK", sign='+'),
            self._get_settings_menu_change_timer_item(timer_name="WORK", sign='-'),
            self._get_settings_menu_change_timer_item(timer_name="PAUSE", sign='+'),
            self._get_settings_menu_change_timer_item(timer_name="PAUSE", sign='-'),
            Menu.SEPARATOR,
            self._get_settings_menu_feature_item(feature_name="Hide Windows"),
            self._get_settings_menu_feature_item(feature_name="Spotify"),
            self._get_settings_menu_feature_item(feature_name="Home Assistant"),
            self._get_settings_menu_feature_item(feature_name="Play Sound"),
            self._get_settings_menu_feature_item(feature_name="Habit Tracking"),
            Menu.SEPARATOR,
            Item("Exit", self.menu_button_exit_app),
        )

    def _get_settings_menu_change_timer_item(self, timer_name, sign):
        return Item(
            text=f"{timer_name} {sign}{self.settings_step_size}",
            action=lambda: self.menu_button_change_timer(timer_name, sign),
        )

    def _get_settings_menu_feature_item(self, feature_name):
        return Item(
            text=feature_name,
            action=lambda: self.feature_handler.toggle_setting(feature_name),
            checked=lambda item: self.feature_handler.features[feature_name]["active"],
            enabled=self.feature_handler.features[feature_name]["handler"] is not None,
        )

    def update_display(self):
        with self.thread_lock:
            self.update_menu()
            if self.current_state in [State.DONE, State.STARTING]:
                self.log.debug(f"Updating icon with state: {self.current_state}")
                self.systray_app.icon = draw_icon_circle(color=self.colors[self.current_state])
            else:
                self.log.debug(f"Updating icon with value: {self.current_timer_value}")
                self.systray_app.icon = draw_icon_text(text=str(self.current_timer_value),
                                                       color=self.colors[self.current_state])

    # MENU BUTTON ACTIONS
    def menu_button_change_timer(self, changing_timer, value):
        self.log.info(f"Changing {changing_timer} timer by {value}")
        if changing_timer == "WORK":
            if self.current_state != State.PAUSE:
                self.current_timer_value += value
                self.update_display()
            self.work_timer_duration += value
            self.firebase.set_entry(
                ref=f'{self.firebase_settings_ref}/work_timer_duration',
                data=self.work_timer_duration
            )
        elif changing_timer == "PAUSE":
            if self.current_state == State.PAUSE:
                self.current_timer_value += value
                self.update_display()
            self.pause_timer_duration += value
            self.firebase.set_entry(
                ref=f'{self.firebase_settings_ref}/pause_timer_duration',
                data=self.pause_timer_duration
            )

    def menu_button_exit_app(self):
        """ Function that is called when the exit button is pressed. Sets thread stop flag """
        self.log.info("Exiting Pomodoro Timer - setting stop_timer_thread_flag and stopping app")
        self.stop_timer_thread_flag = True
        sleep(0.11)
        self.exited_flag = True
        self.systray_app.stop()

    def menu_button_start(self):
        """Function that is called when the start button is pressed"""
        self.log.info("Menu Start pressed")
        self.current_state = State.WORK
        self.current_timer_value = self.work_timer_duration
        self.update_display()
        self.feature_handler.call("Play Sound", "_play_sound",
                                  {"file_path": f'{self.sound_files[self.current_state]}'})
        self.feature_handler.call("Spotify", "play_playlist",
                                  {"playlist_uri": self.playlists[self.current_state]})
        self.feature_handler.call("Home Assistant", "trigger_webhook",
                                  {"url": self.webhooks[self.current_state]})
        self.timer_thread = Thread(target=self.run_timer)
        self.timer_thread.start()

    def menu_button_stop(self):
        """Function that is called when the stop button is pressed"""
        self.log.info("Menu Stop pressed")
        self.current_state = State.READY
        self.current_timer_value = self.work_timer_duration
        self.update_display()
        self.stop_timer_thread_flag = True
        self.feature_handler.call("Spotify", "play_playlist",
                                  {"playlist_uri": self.playlists[self.current_state]})
        self.feature_handler.call("Home Assistant", "trigger_webhook",
                                  {"url": self.webhooks[self.current_state]})
        # Thread.join(self.timer_thread)  # should terminate within 0.1s

    def _switch_to_next_state(self):
        """Switch to the next state and update the icon."""
        self.log.debug(f"Switching to next state from {self.current_state} [{self.time_worked}]")
        if self.current_state == State.WORK:
            self.log.info("Switching WORK -> PAUSE state")
            self.current_state = State.PAUSE
            self.current_timer_value = self.pause_timer_duration
            self.feature_handler.call("Play Sound", "_play_sound",
                                      {"file_path": self.sound_files[self.current_state]})
            self.feature_handler.call("Hide Windows", "minimize_open_windows")
            sleep(1)
            self.feature_handler.call("Spotify", "play_playlist",
                                      {"playlist_uri": self.playlists[self.current_state]})
        elif self.current_state == State.PAUSE and self.time_worked < self.daily_work_goal:
            self.log.info("Switching PAUSE -> WORK state")
            self.current_state = State.READY
            self.current_timer_value = self.work_timer_duration
            self.feature_handler.call(feature_name="Hide Windows", method="restore_windows")
        elif self.current_state == State.PAUSE and self.time_worked >= self.daily_work_goal:
            self.log.info("Switching PAUSE -> DONE state")
            self.current_state = State.DONE
            self.current_timer_value = self.work_timer_duration

        # reset the timer, update the icon and trigger webhook
        self.update_display()
        self.feature_handler.call(feature_name="Home Assistant", method="trigger_webhook",
                                  kwargs={"url": self.webhooks[self.current_state]})
        if self.current_state == State.PAUSE:
            self.run_timer()

    def _increase_time_worked(self):
        """Increase the time_worked counter and update it in firebase"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        if self.current_date != current_date:
            self.current_date = current_date
            self.time_worked = 1
            self.log.info(f"New day: {current_date}. Reset time_done to 1.")
        else:
            self.time_worked += 1
        time_worked_ref = f"{self.firebase_times_worked_ref}/{current_date}"
        self.firebase.update_value(ref=time_worked_ref, key="time_worked", value=self.time_worked)

    def run_timer(self):
        """Function that runs the timer of the Pomodoro App (in a separate thread).

        Every 0.1s the stop_timer_thread_flag is checked if the timer was stopped. Otherwise, every minute the time and
        the icon is updated. If the timer is done, the next state is switched to.
        """
        self.update_display()
        while self.current_timer_value > 0:
            for i in range(600):
                sleep(0.1)
                if self.stop_timer_thread_flag:
                    self.log.info("Stopping timer thread (stop_timer_thread_flag was set)")
                    self.stop_timer_thread_flag = False
                    return
            self.current_timer_value -= 1
            if self.current_state == State.WORK:
                self._increase_time_worked()
            if self.time_worked % 60 == 0:
                self.feature_handler.call(feature_name="Habit Tracking",
                                          method="post_checkin",
                                          kwargs={
                                              "habit_name": self.ticktick_habit_name,
                                              "date_stamp": datetime.now().strftime("%Y%m%d"),
                                              "value": self.time_worked / 60
                                          })
            self.update_display()
        if self.current_timer_value == 0:
            self.log.info("Timer done. Switching to next state.")
            self._switch_to_next_state()


if __name__ == "__main__":
    assert os.getenv("APPDATA", False)
    pomo_app = PomodoroApp(firebase_rtdb_url=secret("FIREBASE_DB_URL"))

    # to keep python out of interpreter shutdown (3.12)
    while pomo_app.exited_flag is False:
        sleep(10)
