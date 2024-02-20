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
from src.systray.utils import draw_icon_text, draw_icon_circle, trigger_webhook
from src._utils.common import config
from src._utils.common import secret, ROOT_DIR
from src._utils.logger import create_logger
from src._utils.apis.spotify import SpotifyHandler
from src._utils.apis.firebase import FirebaseHandler
from src._utils.system.sound import play_sound
from src._utils.system.programs_windows import WindowHandler
from src._utils.apis.ticktick_habits import TicktickHabitApi


class State:
    """Class to represent the current state of the timer. Loads corresponding color and webhook from config."""

    WORK = config["states"]["WORK"]
    PAUSE = config["states"]["PAUSE"]
    READY = config["states"]["READY"]
    DONE = config["states"]["DONE"]
    STARTING = config["states"]["STARTING"]


class PomodoroApp:
    def __init__(
        self, firebase_rdb_url: str | None = None, spotify_info: dict[str, str] | None = None
    ):
        self.name = "Pomodoro Timer"
        self.log = create_logger(self.name)
        self.log.info("\n\n\n\n\t\tSTARTING POMODORO TIMER...\n\n\n")
        self._update_icon_thread_lock = threading.Lock()
        self._start_app_with_stub_data()
        # try to load real settings from firebase
        self.firebase = FirebaseHandler(realtime_db_url=firebase_rdb_url)
        self.setting_ref = config["settings_reference"]
        self.firebase_time_done_ref = config["FIREBASE_TIME_DONE_REF"]
        self._load_settings_from_firebase()
        # handlers
        self.habit_handler = TicktickHabitApi(cookies_path=f"{ROOT_DIR}/.ticktick_cookies")
        self.window_handler = WindowHandler()
        self.spotify_handler = self._init_spotify(spotify_info)
        # todo: add homeassistant handler
        # load timer values
        self.state = State.READY
        self.time_worked_date = datetime.now().strftime("%Y-%m-%d")
        self.time_worked = self._load_time_worked_from_firebase()
        self.work_timer_duration = self.settings["work_timer"]
        self.daily_work_goal = self.settings["daily_work_time_goal"]
        self.pause_timer_duration = self.settings["pause_timer"]
        self.current_timer_value = self.work_timer_duration
        # systray app
        self.stop_timer_thread_flag = False
        self.timer_thread = None
        self.update_display()
        self.log.info("Pomodoro Timer initialised.")

    def _start_app_with_stub_data(self):
        self.log.debug("Initialising and starting app with stub data")
        self.settings = config["default_settings"]
        self.state = State.STARTING
        self.systray_app = pystray.Icon(self.name)
        self.time_worked = 0
        self.work_timer_duration = self.settings["work_timer"]
        self.spotify_handler = None
        self.update_display()
        self.systray_app.run_detached()

    def _load_settings_from_firebase(self):
        try:
            self.settings = self.firebase.get_entry(ref=self.setting_ref)
            assert isinstance(self.settings, dict)
            self.log.info(f"Loaded settings from firebase: \n{pformat(self.settings)}")
        except Exception as e:
            self.log.warning(
                f"Can't load settings from firebase: [{e}], "
                f"using default settings {pformat(config['default_settings'])}."
            )
            self.settings = config["default_settings"]
            try:
                self.firebase.set_entry(ref=self.setting_ref, data=self.settings)
            except Exception as e:
                self.log.warn(f"Could not save default settings to Firebase: {e}")

    def _load_time_worked_from_firebase(self):
        time_worked_ref = f"{self.firebase_time_done_ref}/{self.time_worked_date}/time_worked"
        try:
            time_worked = int(self.firebase.get_entry(ref=time_worked_ref))
            self.log.info(f"Loaded time_worked from firebase: {time_worked}")
        except Exception as e:
            self.log.warning(
                f"Can't load {self.time_worked_date}: time_worked from firebase"
                f", setting to 0 instead (most likely a new day) [{e}]"
            )
            time_worked = 0
        return time_worked

    def _init_spotify(self, spotify_info):
        try:
            return SpotifyHandler(**spotify_info)
        except Exception as e:
            self.log.warning(f"Can't connect to Spotify [{e}]")
            self.settings["Spotify"] = False
            return None

    def update_menu(self):
        def _get_feature_setting_item(feature, enabled=True):
            return Item(
                feature,
                lambda: self._toggle_feature_setting(feature),
                checked=lambda item: self.settings[feature],
                enabled=enabled,
            )

        step_size = self.settings["step_size"]
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
                    pystray.Menu.SEPARATOR,
                    Item(
                        f"Work +{step_size}", lambda: self._change_timer_setting("WORK", step_size)
                    ),
                    Item(
                        f"Work -{step_size}", lambda: self._change_timer_setting("WORK", -step_size)
                    ),
                    Item(
                        f"Pause +{step_size}",
                        lambda: self._change_timer_setting("PAUSE", step_size),
                    ),
                    Item(
                        f"Pause -{step_size}",
                        lambda: self._change_timer_setting("PAUSE", -step_size),
                    ),
                    pystray.Menu.SEPARATOR,
                    _get_feature_setting_item("Hide Windows"),
                    _get_feature_setting_item(
                        "Spotify", enabled=lambda item: self.spotify_handler is not None
                    ),
                    _get_feature_setting_item("Home Assistant"),
                    pystray.Menu.SEPARATOR,
                    Item("Exit", self.exit_app, enabled=True),
                ),
            ),
        )

    def update_display(self):
        with self._update_icon_thread_lock:
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
        assert changing_timer in ["WORK", "PAUSE"]
        self.log.info(f"Changing {changing_timer} timer by {value}")
        if (changing_timer == "WORK" and self.state != State.PAUSE) or (
            changing_timer == "PAUSE" and self.state == State.PAUSE
        ):
            self.current_timer_value += value
            self.update_display()
        if changing_timer == "WORK":
            self.work_timer_duration += value
            self.firebase.update_value(
                ref=self.setting_ref, key="work_timer", value=self.work_timer_duration
            )
        elif changing_timer == "PAUSE":
            self.pause_timer_duration += value
            self.firebase.update_value(
                ref=self.setting_ref, key="pause_timer", value=self.pause_timer_duration
            )

    def _toggle_feature_setting(self, feature_name):
        self.log.info(f"Toggling feature setting: {feature_name}")
        self.settings[feature_name] = not self.settings[feature_name]
        self.firebase.update_value(
            ref=self.setting_ref, key=feature_name, value=self.settings[feature_name]
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
        play_sound(config["sounds"]["start"], volume=self.settings["VOLUME"])
        if self.spotify_handler and self.settings["Spotify"]:
            self.spotify_handler.play_playlist(playlist_uri=config["work_playlist"])
        if self.settings["Home Assistant"]:
            trigger_webhook(url=self.state["webhook"])
        self.timer_thread = Thread(target=self.run_timer)
        self.timer_thread.start()
        self.update_display()

    def menu_button_stop(self):
        """Function that is called when the stop button is pressed"""
        self.log.info("Menu Stop pressed")
        self.state = State.READY
        self.update_display()
        self.stop_timer_thread_flag = True
        # features
        if self.spotify_handler and self.settings["Spotify"]:
            self.spotify_handler.play_playlist(playlist_uri=config["pause_playlist"])
        if self.settings["Home Assistant"]:
            trigger_webhook(url=self.state["webhook"])
        self.update_display()
        # Thread.join(self.timer_thread)  # should terminate within 0.1s

    def _switch_to_next_state(self):
        """Switch to the next state and update the icon."""
        self.log.debug(f"Switching to next state from {self.state} with worked: {self.time_worked}")
        if self.state == State.WORK:
            self.log.info("Switching WORK -> PAUSE state")
            self.state = State.PAUSE
            self.current_timer_value = self.pause_timer_duration
            play_sound(config["sounds"]["pause"])
            if self.settings["Hide Windows"]:
                sleep(0.5)
                self.window_handler.minimize_open_windows()
            if self.spotify_handler and self.settings["Spotify"]:
                sleep(1)
                self.spotify_handler.play_playlist(playlist_uri=config["pause_playlist"])
        elif self.state == State.PAUSE and self.time_worked < self.daily_work_goal:
            self.log.info("Switching PAUSE -> WORK state")
            self.state = State.READY
            self.current_timer_value = self.work_timer_duration
            if self.settings["Hide Windows"]:
                self.window_handler.restore_windows()
        elif self.state == State.PAUSE and self.time_worked >= self.daily_work_goal:
            self.log.info("Switching PAUSE -> DONE state")
            self.state = State.DONE
            self.current_timer_value = self.work_timer_duration

        # reset the timer, update the icon and trigger webhook
        self.update_display()
        if self.settings["Home Assistant"]:
            trigger_webhook(url=self.state["webhook"])
        if self.state == State.PAUSE:
            self.run_timer()

    def _increase_time_worked(self):
        """Increase the time_worked counter and update it in firebase"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        if self.time_worked_date != current_date:
            self.time_worked_date = current_date
            self.time_worked = 1
            self.log.info(f"New day: {current_date}. Reset time_done to 1.")
        else:
            self.time_worked += 1
        ref = f"{self.firebase_time_done_ref}/{current_date}"
        self.firebase.update_value(ref=ref, key="time_worked", value=self.time_worked)

    def _increase_habit_value(self):
        hours_worked = int(self.time_worked / 60)
        self.log.info(
            f"Increasing Habit by one hour to {hours_worked} "
            f"(worked {self.time_worked} minutes)"
        )
        self.habit_handler.checkin_simple(
            habit_name=config["HABIT_NAME"],
            date_stamp=datetime.now().strftime("%Y%m%d"),
            value=hours_worked,
        )

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
            self.log.debug(f"One minute passed. New timer value: {self.current_timer_value}")
            if self.state == State.WORK:
                self._increase_time_worked()
            if self.time_worked % 60 == 0:
                self._increase_habit_value()
            self.update_display()
        if self.current_timer_value == 0:
            self.log.info("Timer done. Switching to next state.")
            self._switch_to_next_state()


if __name__ == "__main__":
    os.environ["APPDATA_DIR"] = "Pomo"
    _firebase_db_url = secret("FIREBASE_DB_URL")
    _spotify_info = {
        "device_name": secret("SPOTIFY_DEVICE_NAME"),
        "client_id": secret("SPOTIFY_CLIENT_ID"),
        "client_secret": secret("SPOTIFY_CLIENT_SECRET"),
        "redirect_uri": config["SPOTIFY"]["redirect_uri"],
        "scope": config["SPOTIFY"]["scope"],
    }
    pomo_app = PomodoroApp(firebase_rdb_url=_firebase_db_url, spotify_info=_spotify_info)
