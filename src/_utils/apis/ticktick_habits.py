import requests
import json
import datetime
from datetime import datetime
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By

from src._utils.common import secret
from src._utils.logger import create_logger


class TicktickHabitHandler:
    """Class that accesses the TickTick habits API. Used to post habit checkins."""

    def __init__(self, cookies_path: str | None = None):
        self.log = create_logger("Ticktick Habits")
        self.cookies_path = cookies_path
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9;de-DE;q=0.8;de;q=0.7",
            "Content-Type": "application/json;charset=UTF-8",
            "Dnt": "1",
            "Hl": "en_US",
            "Origin": "https://www.ticktick.com",
            "Referer": "https://www.ticktick.com/",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "Windows",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "X-Device": '{"platform":"web","os":"Windows 10","device":"Chrome 121.0.0.0","name":"","version":5070,"id":"64f085936fc6ff0ae4a815dc","channel":"website","campaign":"","websocket":"65d2d554073cb37cda076c69"}',
            "X-Tz": "Europe/Berlin",
        }
        self.cookies = self._get_cookies()
        self.headers["Cookie"] = self.cookies
        self.habits = self._get_habits_metadata()
        # check if the cookies are valid
        if "errorId" in self.habits:
            self.log.error(f"Error loading habits: {self.habits}")
            raise ValueError(f"Error loading habits {self.habits}")
        self.habit_ids = {habit["name"]: habit["id"] for habit in self.habits}
        self.habits = {habit["id"]: habit for habit in self.habits}
        self.status_codes = {0: "Not completed", 1: "Failed", 2: "Completed"}

    def _get_cookies(self):
        """Opens the browser and opens the ticktick website to get the cookies."""
        if self.cookies_path:
            cookies = self._get_cookies_from_file()
            if cookies and self._test_cookies(cookies):
                self.log.debug(f"Loaded cookies from file: {self.cookies_path}")
                return cookies
        self.log.debug("No cookies from file, trying to load cookies via Login (Selenium)")
        cookies = self._get_cookies_from_browser()
        self.log.info(f"Loaded cookies via Selenium: {cookies}")
        self._save_cookies_to_path(cookies=cookies)
        return cookies

    def _get_cookies_from_file(self):
        try:
            with open(self.cookies_path, "r") as file:
                cookies = file.read().strip()
                return cookies
        except Exception as e:
            self.log.error(f"Error loading cookies from file: {e}")
        return None

    def _get_cookies_from_browser(self):
        url = "https://www.ticktick.com/signin"
        username = secret("TICKTICK_USERNAME")
        password = secret("TICKTICK_PASSWORD")
        username_selector = "#emailOrPhone"
        password_selector = "#password"
        login_button_selector = "section:nth-child(1) > button"
        assert username and password, "TICKTICK_USERNAME or _PASSWORD not found in env variables."

        options = webdriver.ChromeOptions()
        # options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        driver.find_element(By.CSS_SELECTOR, username_selector).send_keys(username)
        driver.find_element(By.CSS_SELECTOR, password_selector).send_keys(password)
        driver.find_element(By.CSS_SELECTOR, login_button_selector).click()
        sleep(3)
        cookies_dict = driver.get_cookies()
        driver.quit()
        assert len(cookies_dict) >= 5, "Less than 5 cookies found. Something went wrong."
        cookies = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_dict])
        return cookies

    def _save_cookies_to_path(self, cookies: str):
        if self.cookies_path:
            with open(self.cookies_path, "w") as file:
                file.write(cookies)
            self.log.debug("Saved cookies to file")

    def _test_cookies(self, cookies: str):
        """Return True if the cookies are valid, False if not."""
        url = "https://api.ticktick.com/api/v2/habits"
        headers = self.headers
        headers["Cookie"] = cookies
        data = requests.get(url, headers=headers).json()
        if "errorCode" in data and data["errorCode"] == "user_not_sign_on":
            self.log.warning("Cookies are invalid")
            return False
        else:
            self.log.debug("Cookies are valid")
            return True

    def _get_habits_metadata(self):
        url = "https://api.ticktick.com/api/v2/habits"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def query_single_checkin(self, habit_id, date_stamp):
        url = "https://api.ticktick.com/api/v2/habitCheckins/query"
        date = datetime.datetime.strptime(date_stamp, "%Y%m%d")
        after_stamp = (date - datetime.timedelta(days=1)).strftime("%Y%m%d")
        payload = {"habitIds": [habit_id], "afterStamp": after_stamp}
        response = requests.post(url, data=json.dumps(payload), headers=self.headers).json()
        habit_entries = response["checkins"][habit_id]
        for entry in habit_entries:
            if entry["checkinStamp"] == int(date_stamp):
                return entry
        return None

    def update_habit_metadata(self, habit_id):
        # todo: update a single habit metadata, to update checkins quickly
        pass

    def post_checkin(
        self, habit_name: str, date_stamp: str, status: int | None = None, value: int | None = None
    ):
        """Post a simple habit checkin to the TickTick API.

        Args:
            habit_name: Name of the habit to check-in
            date_stamp: Date of the check-in, in the format YYYYMMDD
            status: Status of the check-in. 0: Not completed, 1: Failed, 2: Completed
            value: The value amount to check in. for habits who require multiple units
        """
        assert not status and value, "You can only provide status or value, not both"
        assert habit_name in self.habit_ids, f"Habit {habit_name} not found in habits"

        url = "https://api.ticktick.com/api/v2/habitCheckins/batch"
        current_utc_time = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + ".000+0000"
        habit_id = self.habit_ids[habit_name]
        habit_goal = int(self.habits[habit_id]["goal"])
        if status is not None:
            value = habit_goal if status == 2 else 0
        elif value is not None:
            status = 2 if value >= habit_goal else 0
        else:
            raise ValueError("You need to provide either status or value")

        self.log.info(f"Checking {habit_name} on {date_stamp} as {status}: {value}/{habit_goal}")

        checkin_data = {
            "checkinStamp": date_stamp,
            "checkinTime": current_utc_time,
            "goal": habit_goal,
            "habitId": habit_id,
            "opTime": current_utc_time,
            "status": status,
            "value": value,
        }

        existing_checkin_entry = self.query_single_checkin(habit_id, date_stamp)
        if not existing_checkin_entry:
            payload = {"add": [checkin_data], "update": [], "delete": []}
        else:
            checkin_data["id"] = existing_checkin_entry["id"]
            payload = {"add": [], "update": [checkin_data], "delete": []}

        try:
            response = requests.post(url=url, data=json.dumps(payload), headers=self.headers).json()
            self.log.info(f"Posted Habit checkin with response: {response}")
        except Exception as e:
            self.log.error(f"Error posting habit checking: {e}")

    def get_all_habit_data(self, after_stamp: str):
        import pandas as pd
        habit_ids = list(self.habit_ids.values())
        url = "https://api.ticktick.com/api/v2/habitCheckins/query"
        payload = {"habitIds": habit_ids, "afterStamp": after_stamp}
        response = requests.post(url, data=json.dumps(payload), headers=self.headers).json()
        habit_entries = response["checkins"]
        # from the dict of habits containing lists of entries, add the habit name to each entry and then flatten the list
        habit_entries_list = [
            {**entry, "habitName": self.habits[habit_id]["name"]}
            for habit_id, entries in habit_entries.items()
            for entry in entries
        ]
        habit_entries_df = pd.DataFrame(habit_entries_list)
        habit_entries_df["checkinStamp"] = pd.to_datetime(
            habit_entries_df["checkinStamp"], format="%Y%m%d"
        )
        return habit_entries_df


def show_habit_heatmap():
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    api = TicktickHabitHandler(cookies_path="../.ticktick_cookies")
    df = api.get_all_habit_data("20220101")
    df = df[df["habitName"] == "Sport"]

    # Filter the DataFrame for the last 30 days
    end_date = pd.Timestamp.now()
    start_date = end_date - pd.Timedelta(days=30)
    df_filtered = df[(df["checkinStamp"] >= start_date) & (df["checkinStamp"] <= end_date)]

    # Create a pivot table for the heatmap with only one column for 'status'
    pivot_table = df_filtered.pivot_table(
        index=pd.Grouper(key="checkinStamp", freq="D"),
        values="status",
        aggfunc="first",
        dropna=False,
    ).fillna(0)

    # Plot the heatmap
    plt.figure(figsize=(3, 10))  # Adjusted the figure size for a single-column heatmap
    sns.heatmap(pivot_table, annot=False, cbar=False, cmap="Blues", fmt="d", yticklabels=True)
    plt.title("Habit Status for the Last 30 Days")
    plt.xlabel("Status")
    plt.ylabel("Date")

    # Format the y-axis to show only dates
    ax = plt.gca()
    ax.yaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.yaxis.set_major_locator(mdates.DayLocator())

    plt.xticks([])
    plt.yticks(rotation=0)
    plt.show()


if __name__ == "__main__":
    pass
