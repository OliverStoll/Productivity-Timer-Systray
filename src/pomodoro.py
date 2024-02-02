# fix working directory if running from a pyinstaller executable
try:
    import os, sys
    os.chdir(sys._MEIPASS)
except AttributeError:
    pass

# global
import pystray
from pystray import Menu, MenuItem as Item
from time import sleep
from threading import Thread
# local
from src.systray.utils import draw_icon_text, draw_icon_circle, trigger_webhook
from src._utils.common import config_dict
from src._utils.common import secret
from src._utils.logger import create_logger
from src._utils.apis.spotify import SpotifyHandler
from src._utils.apis.firebase import FirebaseHandler
from src._utils.system.sound import play_sound
from src._utils.system.mouse import toggle_desktop_drawer


class State:
    """ Class to represent the current state of the timer. Loads corresponding color and webhook from config. """
    WORK = config_dict['states']['WORK']
    PAUSE = config_dict['states']['PAUSE']
    READY = config_dict['states']['READY']
    DONE = config_dict['states']['DONE']


class PomodoroApp:
    def __init__(self):
        self.log = create_logger("Pomodoro Timer")
        # settings
        self.firebase = FirebaseHandler()
        self.setting_ref = config_dict['settings_reference']
        try:
            self.settings = self.firebase.get_entry(ref=self.setting_ref)
            assert isinstance(self.settings, dict)
            self.log.info(f"Loaded settings from firebase: {self.settings}")
        except:
            self.log.warning(f"Can't load settings from firebase, using default settings {config_dict['default_settings']}.")
            self.settings = config_dict['default_settings']
            self.firebase.set_entry(ref=self.setting_ref, data=self.settings)
        # timer
        self.state = State.READY
        self.name = 'Pomodoro'
        self.time_done = 0
        self.work_timer_duration = self.settings['work_timer']
        self.total_work_duration = self.settings['number_of_timers'] * self.work_timer_duration
        self.pause_timer_duration = self.settings['pause_timer']
        self.current_time = self.work_timer_duration
        # apis
        try:
            self.spotify = SpotifyHandler(device_name=secret('SPOTIFY_DEVICE_NAME'))
        except Exception as e:
            self.log.warning(f"Can't connect to Spotify [{e}]")
            self.spotify = None
            self.settings['Spotify'] = False
        # systray
        self.stop_timer_thread_flag = False
        self.timer_thread = None
        self.systray_icon = pystray.Icon(config_dict['app_name'])
        self.update_icon()
        self.update_menu()
        # todo: add homeassistant handler


    def update_menu(self):
        def _get_feature_setting_item(feature, enabled=True):
            return Item(feature, lambda: self._toggle_feature_setting(feature), checked=lambda item: self.settings[feature], enabled=enabled)

        step_size = self.settings['step_size']
        self.systray_icon.menu = Menu(
            Item('Start', self.menu_button_start,
                 default=(self.state == State.READY),
                 enabled=lambda item: self.state != State.WORK),
            Item('Stop', self.menu_button_stop,
                 default=(self.state == State.WORK),
                 enabled=lambda item: self.state != State.READY and self.state != State.DONE),
            Item('Settings',
                 Menu(Item(f"Work +{step_size}", lambda: self._change_timer_setting('WORK', step_size)),
                      Item(f"Work -{step_size}", lambda: self._change_timer_setting('WORK', -step_size)),
                      Item(f"Pause +{step_size}", lambda: self._change_timer_setting('PAUSE', step_size)),
                      Item(f"Pause -{step_size}", lambda: self._change_timer_setting('PAUSE', -step_size)),
                      pystray.Menu.SEPARATOR,
                      _get_feature_setting_item('Hide Windows'),
                      _get_feature_setting_item('Spotify', enabled=lambda item: self.spotify is not None),
                      _get_feature_setting_item('Webhooks'),
                      )),
            Item('Exit', self.exit),
        )

    def update_icon(self):
        self.update_menu()
        if self.state == State.DONE:
            self.systray_icon.icon = draw_icon_circle(color=self.state['color'])
        else:
            self.systray_icon.icon = draw_icon_text(text=str(self.current_time), color=self.state['color'])

    def _change_timer_setting(self, timer, value):
        assert timer in ['WORK', 'PAUSE']
        if timer == 'WORK' and self.state != State.PAUSE or timer == 'PAUSE' and self.state == State.PAUSE:
            self.current_time += value
            self.update_icon()
        if timer == 'WORK':
            self.work_timer_duration += value
            self.firebase.update_value(ref=self.setting_ref, key='work_timer', value=self.work_timer_duration)
        elif timer == 'PAUSE':
            self.pause_timer_duration += value
            self.firebase.update_value(ref=self.setting_ref, key='pause_timer', value=self.pause_timer_duration)

    def _toggle_feature_setting(self, feature_name):
        self.settings[feature_name] = not self.settings[feature_name]
        self.firebase.update_value(ref=self.setting_ref, key=feature_name, value=self.settings[feature_name])

    def run(self):
        self.systray_icon.run_detached()

    def exit(self):
        """ Function that is called when the exit button is pressed. Sets the stop_timer_thread_flag for the timer thread. """
        self.stop_timer_thread_flag = True
        sleep(0.11)
        self.systray_icon.stop()

    def menu_button_start(self):
        """ Function that is called when the start button is pressed """
        self.state = State.WORK
        self.update_icon()
        play_sound(config_dict['sounds']['start'], volume=self.settings['VOLUME'])
        if self.spotify and self.settings['Spotify']:
            self.spotify.play_playlist(uri=config_dict['work_playlist'])
        if self.settings['Webhooks']:
            trigger_webhook(url=self.state['webhook'])
        self.timer_thread = Thread(target=self.run_timer)
        self.timer_thread.start()

    def menu_button_stop(self):
        """ Function that is called when the stop button is pressed """
        self.state = State.READY
        self.update_icon()
        self.stop_timer_thread_flag = True
        # features
        if self.spotify and self.settings['Spotify']:
            self.spotify.play_playlist(uri=config_dict['pause_playlist'])
        if self.settings['Webhooks']:
            trigger_webhook(url=self.state['webhook'])
        Thread.join(self.timer_thread)  # should terminate within 0.1s


    def _switch_to_next_state(self):
        """ Switch to the next state and update the icon. """
        if self.state == State.WORK:
            self.state = State.PAUSE
            self.current_time = self.pause_timer_duration
            play_sound(config_dict['sounds']['pause'])
            if self.spotify and self.settings['Spotify']:
                self.spotify.play_playlist(uri=config_dict['pause_playlist'])
            if self.settings['Hide Windows']:
                toggle_desktop_drawer()
        elif self.state == State.PAUSE and self.time_done < self.total_work_duration:
            self.state = State.READY
            self.current_time = self.work_timer_duration
            if self.settings['Hide Windows']:
                toggle_desktop_drawer()
        elif self.state == State.PAUSE and self.time_done >= self.total_work_duration:
            self.state = State.DONE
            self.current_time = self.work_timer_duration

        # reset the timer, update the icon and trigger webhook
        self.update_icon()
        if self.settings['Webhooks']:
            trigger_webhook(url=self.state['webhook'])
        if self.state == State.PAUSE:
            self.run_timer()


    def run_timer(self):
        """ Function that runs the timer of the Pomodoro App (in a separate thread).

        Every 0.1s the stop_timer_thread_flag is checked if the timer was stopped. Otherwise, every minute the time and
        the icon is updated. If the timer is done, the next state is switched to.
        """
        self.update_icon()
        while self.current_time > 0:
            # wait for a minute and continuously check if thread status changes
            for i in range(600):
                sleep(0.1)
                if self.stop_timer_thread_flag:
                    self.state = State.READY
                    self.current_time = self.work_timer_duration
                    self.update_icon()
                    self.stop_timer_thread_flag = False
                    return
            # update the time after a full minute (seconds are not recorded)
            self.current_time -= 1
            if self.state == State.WORK:
                self.time_done += 1
            self.update_icon()
        # check if the timer is done and switch to the next state
        if self.current_time == 0:
            self._switch_to_next_state()


if __name__ == '__main__':
    PomodoroApp().run()
