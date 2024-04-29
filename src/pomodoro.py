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
from src._utils.system.bluetooth import bluetooth_is_enabled


class State:
    """Class to represent the current state of the timer. Loads corresponding color and webhook from config."""
    WORK = CONFIG["states"]["WORK"]
    PAUSE = CONFIG["states"]["PAUSE"]
    READY = CONFIG["states"]["READY"]
    DONE = CONFIG["states"]["DONE"]
    STARTING = CONFIG["states"]["STARTING"]


class PomodoroFeatures:
    def __init__(self, settings: dict, firebase=None):
        self.log = create_logger("Pomodoro Features")
        self.firebase = firebase
        self.handlers: dict[str, any] = {
            "Hide Windows": {"class": WindowHandler},
            "Spotify": {
                "class": SpotifyHandler,
                "kwargs": {
                    "device_name": secret("SPOTIFY_DEVICE_NAME"),
                    "client_id": secret("SPOTIFY_CLIENT_ID"),
                    "client_secret": secret("SPOTIFY_CLIENT_SECRET"),
                    "redirect_uri": CONFIG["SPOTIFY"]["redirect_uri"],
                    "scope": CONFIG["SPOTIFY"]["scope"],
                    "cache_path": f"{os.getenv('APPDATA')}/{os.getenv('APPDATA_DIR')}/.spotify_cache",
                }
            },
            # "Spotify Bluetooth-Only": False,  TODO
            "Home Assistant": {"class": HomeAssistantHandler, "kwargs": {
                "base_url": "http://homeassistant.local:8123/api/webhook/"}},
            "Play Sound": {"class": SoundHandler, "kwargs": {"default_volume": 1}},
            "Habit Tracking": {"class": TicktickHabitHandler, "kwargs": {
                "cookies_path": f"{os.getenv('APPDATA')}/{os.getenv('APPDATA_DIR')}/.ticktick_cookies"}},
        }
        self.init_handlers()
        self.init_settings(settings)

    def init_handlers(self):
        for name, feature in self.handlers.items():
            try:
                if "kwargs" in feature:
                    feature["handler"] = feature["class"](**feature["kwargs"])
                else:
                    feature["handler"] = feature["class"]()
                self.log.info(f"Initialized {name} Handler")
            except Exception as e:
                self.log.warning(f"infos Handler {feature} not initialized: [{e}]")
                feature["handler"] = None

    def init_settings(self, settings: dict):
        for name, feature in self.handlers.items():
            feature["active"] = settings.get(name, False)

    def call(self, feature: str, function: str, kwargs: dict | None = None):
        """Call a function of a feature if it is active and initialized."""
        if self.handlers[feature]["active"] and self.handlers[feature]["handler"] is not None:
            try:
                if kwargs:
                    self.handlers[feature]["handler"].__getattribute__(function)(**kwargs)
                else:
                    self.handlers[feature]["handler"].__getattribute__(function)()
                self.log.debug(f"Called {feature} function {function} with args: {kwargs}")
            except Exception as e:
                self.log.warning(f"Failed to run {feature} function {function}: {e}")
        elif not self.handlers[feature]["active"]:
            self.log.debug(f"Trying {feature}-{function}: {feature} is not active.")
        elif self.handlers[feature]["handler"] is None:
            self.log.debug(f"Trying {feature}-{function}: {feature} had an error initializing.")

    def toggle(self, feature: str):
        """ Toggle the active state of a feature. """
        self.log.info(f"Toggling feature setting: {feature}")
        self.handlers[feature]["active"] = not self.handlers[feature]["active"]
        if self.firebase:
            self.firebase.set_entry(ref=f'{CONFIG["FIREBASE_REF_SETTINGS"]}/{feature}',
                                    data=self.handlers[feature]["active"])


class PomodoroApp:
    def __init__(self, firebase_rdb_url: str | None = None):
        self.log = create_logger("Pomodoro Timer")
        self.log.info("\n\n\n\n\t\tSTARTING POMODORO TIMER...\n\n\n")
        self._load_secrets_file()
        self.thread_lock = threading.Lock()
        self.firebase = FirebaseHandler(firebase_rdb_url)
        self.features = PomodoroFeatures(settings=CONFIG["default_settings"]["features"],
                                         firebase=self.firebase)
        self._init_app_with_offline_data()

        # try to load real settings from firebase
        self._init_settings_from_fb()
        self.features.init_settings(self.settings["features"])

        # load timer values
        self.work_timer_duration = self.settings["work_timer_duration"]
        self.pause_timer_duration = self.settings["pause_timer_duration"]
        self.daily_work_goal = self.settings["daily_work_time_goal"]
        self.current_timer_value = self.work_timer_duration
        self.date_of_time_worked = datetime.now().strftime("%Y-%m-%d")
        self.time_worked = self._load_time_worked_from_fb()

        # systray app
        self.state = State.READY
        self.stop_timer_thread_flag = False
        self.timer_thread = None
        self.update_display()
        self.log.info("Pomodoro Timer initialised.")

    def _init_app_with_offline_data(self):
        self.log.debug("Starting app with stub data")
        self.settings = CONFIG["default_settings"]
        self.state = State.STARTING
        self.systray_app = pystray.Icon("Pomodoro Timer")
        self.time_worked = 0
        self.work_timer_duration = self.settings["work_timer_duration"]
        self.pause_timer_duration = self.settings["pause_timer_duration"]
        self.update_display()
        self.systray_app.run_detached()

    def _load_secrets_file(self):
        secrets_path = f"{os.getenv('APPDATA')}/{os.getenv('APPDATA_DIR')}/.env"
        if os.path.exists(secrets_path):
            self.log.info(f"Loading .env file from {secrets_path}")
            load_env_file(secrets_path)

    def _init_settings_from_fb(self):
        """Load settings from firebase or use default settings if not available."""
        try:
            settings = self.firebase.get_entry(ref=CONFIG["FIREBASE_REF_SETTINGS"])
            assert isinstance(settings, dict)
            self.settings = settings
            self.log.info("Loaded settings from firebase")
        except Exception as e:
            self.log.warning(f"Can't load settings from firebase: [{e}], staying with"
                             f" default settings {CONFIG['default_settings']}")
            try:
                self.firebase.set_entry(ref=CONFIG["FIREBASE_REF_SETTINGS"], data=self.settings)
            except Exception as e:
                self.log.warning(f"Could not save default settings to Firebase: {e}")

    def _load_time_worked_from_fb(self):
        time_worked_ref = f"{CONFIG["FIREBASE_REF_TIME_DONE"]}/{self.date_of_time_worked}/time_worked"
        try:
            time_worked = int(self.firebase.get_entry(ref=time_worked_ref))
            self.log.info(f"Loaded time_worked from firebase: {time_worked}")
        except Exception as e:
            self.log.info(f"Can't load {self.date_of_time_worked}: time_worked from firebase, "
                          f"setting to 0 instead (most likely a new day)")
            time_worked = 0
        return time_worked

    def update_menu(self):
        def _get_feature_setting_item(feature_name):
            return Item(
                feature_name,
                lambda: self.features.toggle(feature_name),
                checked=lambda item: self.features.handlers[feature_name]["active"],
                enabled=self.features.handlers[feature_name]["handler"] is not None,
            )

        step_size = self.settings["timer_step_size"]
        self.systray_app.menu = Menu(
            Item(
                "Start",
                self.menu_button_start,
                default=(self.state == State.READY),
                enabled=lambda item: self.state != State.WORK,
            ),
            Item(
                "Stop",
                self.menu_button_stop,
                default=(self.state == State.WORK),
                enabled=lambda item: self.state != State.READY and self.state != State.DONE,
            ),
            Item(
                "Settings",
                Menu(
                    Item(
                        f"Worked {self.time_worked / self.work_timer_duration:.1f} blocks",
                        action=None,
                    ),
                    Menu.SEPARATOR,
                    Item(
                        f"Work +{step_size}",
                        lambda: self._change_timer_setting("WORK", step_size)
                    ),
                    Item(
                        f"Work -{step_size}",
                        lambda: self._change_timer_setting("WORK", -step_size)
                    ),
                    Item(
                        f"Pause +{step_size}",
                        lambda: self._change_timer_setting("PAUSE", step_size),
                    ),
                    Item(
                        f"Pause -{step_size}",
                        lambda: self._change_timer_setting("PAUSE", -step_size),
                    ),
                    Menu.SEPARATOR,
                    _get_feature_setting_item("Hide Windows"),
                    _get_feature_setting_item("Spotify"),
                    _get_feature_setting_item("Home Assistant"),
                    _get_feature_setting_item("Play Sound"),
                    _get_feature_setting_item("Habit Tracking"),
                    Menu.SEPARATOR,
                    Item("Exit", self.exit_app),
                ),
            ),
        )

    def update_display(self):
        with self.thread_lock:
            self.update_menu()
            if self.state in [State.DONE, State.STARTING]:
                self.log.debug(f"Updating icon with state: {self.state}")
                self.systray_app.icon = draw_icon_circle(color=self.state["color"])
            else:
                self.log.debug(f"Updating icon with value: {self.current_timer_value}")
                self.systray_app.icon = draw_icon_text(
                    text=str(self.current_timer_value), color=self.state["color"]
                )

    def _change_timer_setting(self, changing_timer, value):
        self.log.info(f"Changing {changing_timer} timer by {value}")
        if changing_timer == "WORK":
            if self.state != State.PAUSE:
                self.current_timer_value += value
                self.update_display()
            self.work_timer_duration += value
            self.firebase.set_entry(
                ref=f'{CONFIG["FIREBASE_REF_SETTINGS"]}/work_timer', data=self.work_timer_duration
            )
        elif changing_timer == "PAUSE":
            if self.state == State.PAUSE:
                self.current_timer_value += value
                self.update_display()
            self.pause_timer_duration += value
            self.firebase.set_entry(
                ref=f'{CONFIG["FIREBASE_REF_SETTINGS"]}/pause_timer', data=self.pause_timer_duration
            )

    def exit_app(self):
        """Function that is called when the exit button is pressed. Sets the stop_timer_thread_flag for the timer thread."""
        self.log.info("Exiting Pomodoro Timer - setting stop_timer_thread_flag and stopping app")
        self.stop_timer_thread_flag = True
        sleep(0.11)
        self.systray_app.stop()

    def menu_button_start(self):
        """Function that is called when the start button is pressed"""
        self.log.info("Menu Start pressed")
        self.state = State.WORK
        self.current_timer_value = self.work_timer_duration
        self.update_display()
        self.features.call("Play Sound", "_play_sound",
                           {"file_path": f'{ROOT_DIR}{CONFIG["sounds"]["start"]}'})
        self.features.call("Spotify", "play_playlist", {"playlist_uri": CONFIG["work_playlist"]})
        self.features.call("Home Assistant", "trigger_webhook", {"url": self.state["webhook"]})
        self.timer_thread = Thread(target=self.run_timer)
        self.timer_thread.start()
        self.update_display()

    def menu_button_stop(self):
        """Function that is called when the stop button is pressed"""
        self.log.info("Menu Stop pressed")
        self.state = State.READY
        self.update_display()
        self.stop_timer_thread_flag = True
        self.features.call("Spotify", "play_playlist", {"playlist_uri": CONFIG["pause_playlist"]})
        self.features.call("Home Assistant", "trigger_webhook", {"url": self.state["webhook"]})
        self.update_display()
        # Thread.join(self.timer_thread)  # should terminate within 0.1s

    def _switch_to_next_state(self):
        """Switch to the next state and update the icon."""
        self.log.debug(f"Switching to next state from {self.state} with worked: {self.time_worked}")
        if self.state == State.WORK:
            self.log.info("Switching WORK -> PAUSE state")
            self.state = State.PAUSE
            self.current_timer_value = self.pause_timer_duration
            self.features.call("Play Sound", "_play_sound",
                               {"file_path": f'{ROOT_DIR}{CONFIG["sounds"]["pause"]}'})
            self.features.call("Hide Windows", "minimize_open_windows")
            sleep(1)
            self.features.call("Spotify", "play_playlist",
                               {"playlist_uri": CONFIG["pause_playlist"]})
        elif self.state == State.PAUSE and self.time_worked < self.daily_work_goal:
            self.log.info("Switching PAUSE -> WORK state")
            self.state = State.READY
            self.current_timer_value = self.work_timer_duration
            self.features.call(feature="Hide Windows", function="restore_windows")
        elif self.state == State.PAUSE and self.time_worked >= self.daily_work_goal:
            self.log.info("Switching PAUSE -> DONE state")
            self.state = State.DONE
            self.current_timer_value = self.work_timer_duration

        # reset the timer, update the icon and trigger webhook
        self.update_display()
        self.features.call(feature="Home Assistant", function="trigger_webhook",
                           kwargs={"url": self.state["webhook"]})
        if self.state == State.PAUSE:
            self.run_timer()

    def _increase_time_worked(self):
        """Increase the time_worked counter and update it in firebase"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        if self.date_of_time_worked != current_date:
            self.date_of_time_worked = current_date
            self.time_worked = 1
            self.log.info(f"New day: {current_date}. Reset time_done to 1.")
        else:
            self.time_worked += 1
        ref = f"{CONFIG["FIREBASE_REF_TIME_DONE"]}/{current_date}"
        self.firebase.update_value(ref=ref, key="time_worked", value=self.time_worked)

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
                    self.state = State.READY
                    self.current_timer_value = self.work_timer_duration
                    self.update_display()
                    self.stop_timer_thread_flag = False
                    return
            self.current_timer_value -= 1
            if self.state == State.WORK:
                self._increase_time_worked()
            if self.time_worked % 60 == 0:
                self.features.call("Habit Tracking", "post_checkin",
                                   {"habit_name": CONFIG["HABIT_NAME"],
                                    "date_stamp": datetime.now().strftime("%Y%m%d"),
                                    "value": self.time_worked / 60})
            self.update_display()
        if self.current_timer_value == 0:
            self.log.info("Timer done. Switching to next state.")
            self._switch_to_next_state()


if __name__ == "__main__":
    assert os.getenv("APPDATA", False), "APPDATA env-var not set, probably not running on windows"
    os.environ["APPDATA_DIR"] = "Pomo"
    pomo_app = PomodoroApp(firebase_rdb_url=secret("FIREBASE_DB_URL"))
    while True:
        # to keep python out of interpreter shutdown (3.12)
        sleep(100000000)
