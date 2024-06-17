import requests
import json
import datetime
import importlib

from src._utils.logger import create_logger


class FirebaseHandler:
    def __init__(self, realtime_db_url: str | None = None):
        """Firebase client to interact with a realtime database

        Currently only supports unauthenticated access."""
        self.log = create_logger("Firebase")
        self.headers = {"Content-Type": "application/x-www-form-urlencoded"}
        self.database_url = realtime_db_url
        if not self.database_url:
            self.log.error(
                "Could not load firebase project from environment variables. "
                "It will ignore all future interaction"
            )

    def _check_inactive(self) -> bool:
        """Check if we (this Firebase Handler) is active"""
        if not self.database_url:
            self.log.warn("Firebase client is not active. Ignoring request")
        return not self.database_url

    def get_list(self, ref: str, max_results: int = 100, convert_to_list: bool = True):
        """Get a list of child-entries from an object in firebase."""
        if self._check_inactive():
            return
        params = {"orderBy": '"$key"', "limitToFirst": str(max_results)}
        reference_url = f"{self.database_url}/{ref}.json"
        try:
            response = requests.get(url=reference_url, params=params)
            self.log.debug(f"Getting List: {response.text}")
            if convert_to_list:
                list_json = response.json()
                return [list_json[key] for key in list_json]
            else:
                return response.json()
        except Exception as e:
            self.log.error(f"Failed to get list from {ref}: {e}")
            return None

    def update_value(self, ref: str, key: str, value):
        """Update a value of a object entry in firebase"""
        if self._check_inactive():
            return
        data = json.dumps({key: value})
        try:
            response = requests.patch(
                url=f"{self.database_url}/{ref}.json", headers=self.headers, data=data
            )
            self.log.debug(f"Updating Value of {ref}: {response.text}")
        except Exception as e:
            self.log.error(f"Failed to update value of {ref}: {e}")

    def delete_entry(self, ref: str):
        """Delete an object entry from firebase"""
        if self._check_inactive():
            return
        try:
            requests.delete(url=f"{self.database_url}/{ref}.json")
            self.log.debug(f"Deleted entry {ref} from firebase")
        except Exception as e:
            self.log.error(f"Failed to delete entry {ref}: {e}")

    def get_entry(self, ref: str):
        """Get an object entry from firebase"""
        if self._check_inactive():
            return
        try:
            response = requests.get(url=f"{self.database_url}/{ref}.json").json()
            self.log.debug(f"Got entry {ref} from firebase: {response}")
            return response
        except Exception as e:
            self.log.error(f"Failed to get entry {ref}: {e}")
            return None

    def set_entry(self, ref: str, data: dict):
        """Set an object entry in firebase"""
        if self._check_inactive():
            return
        try:
            response = requests.put(
                url=f"{self.database_url}/{ref}.json", headers=self.headers, data=json.dumps(data)
            )
            self.log.debug(f"Set entry {ref} with data {data} in firebase: {response.text}")
        except Exception as e:
            self.log.error(f"Failed to set entry {ref}: {e}")

    def set_entry_df(self, ref: str, df):
        """Set a dataframe entry in firebase, by first converting it to a dictionary"""
        if self._check_inactive():
            return
        data = df.to_dict(orient="index")
        try:
            response = requests.put(
                url=f"{self.database_url}/{ref}.json", headers=self.headers, data=json.dumps(data)
            )
            self.log.debug(f"Set df entry {ref} in firebase. Response: {response.text}")
        except Exception as e:
            self.log.error(f"Failed to set df entry {ref}: {e}")

    def get_entry_df(self, ref: str) -> object | None:
        """Get a dataframe entry from firebase, by converting it from a dictionary"""
        if not importlib.find_loader("pandas"):
            self.log.info("Pandas not found. Will import it now")
            from pandas import DataFrame

        if self._check_inactive():
            return None
        try:
            data = requests.get(url=f"{self.database_url}/{ref}.json").json()
            self.log.debug(f"Got df entry {ref} from firebase")
            return DataFrame.from_dict(data, orient="index")  # noqa (pandas import)
        except Exception as e:
            self.log.error(f"Failed to get df entry {ref}: {e}")
            return None


if __name__ == "__main__":
    firebase = FirebaseHandler()
    firebase.update_value(ref="To-Do/t-18002271", key="start_datum", value="2022_01_01")
