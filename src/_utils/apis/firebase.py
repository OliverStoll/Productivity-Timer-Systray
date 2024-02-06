import requests
import json
from pandas import DataFrame

from src._utils.logger import create_logger


class FirebaseHandler:
    def __init__(self, realtime_db_url: str | None = None):
        """Firebase client to interact with a realtime database

        Currently only supports unauthenticated access."""
        self.log = create_logger("Firebase")
        self.headers = {"Content-Type": "application/x-www-form-urlencoded"}
        self.database_url = realtime_db_url
        if not self.database_url:
            self.log.warn(
                "Could not load firebase project from environment variables. "
                "It will ignore all future interaction"
            )

    def _check_inactive(self) -> bool:
        """Check if we (this Firebase Handler) is active"""
        if not self.database_url:
            self.log.debug("Firebase client is not active. Ignoring request")
        return not self.database_url

    def get_list(self, ref: str, max_results: int = 100, convert_to_list: bool = True):
        """Get a list of child-entries from an object in firebase."""
        if self._check_inactive():
            return
        params = {"orderBy": '"$key"', "limitToFirst": str(max_results)}
        reference_url = f"{self.database_url}/{ref}.json"
        response = requests.get(url=reference_url, params=params)
        if convert_to_list:
            list_json = response.json()
            return [list_json[key] for key in list_json]
        else:
            return response.json()

    def update_value(self, ref: str, key: str, value):
        """Update a value of a object entry in firebase"""
        if self._check_inactive():
            return
        data = json.dumps({key: value})
        response = requests.patch(
            url=f"{self.database_url}/{ref}.json", headers=self.headers, data=data
        )
        self.log.debug(f"Updating Value: {response.text}")

    def delete_entry(self, ref: str):
        """Delete an object entry from firebase"""
        if self._check_inactive():
            return
        requests.delete(url=f"{self.database_url}/{ref}.json")

    def get_entry(self, ref: str):
        """Get an object entry from firebase"""
        if self._check_inactive():
            return
        return requests.get(url=f"{self.database_url}/{ref}.json").json()

    def set_entry(self, ref: str, data: dict):
        """Set an object entry in firebase"""
        if self._check_inactive():
            return
        response = requests.put(
            url=f"{self.database_url}/{ref}.json", headers=self.headers, data=json.dumps(data)
        )
        self.log.info(f"Set entry {ref} with data {data} in firebase. Response: {response.text}")

    def set_entry_df(self, ref: str, df: DataFrame):
        """Set a dataframe entry in firebase, by first converting it to a dictionary"""
        if self._check_inactive():
            return
        data = df.to_dict(orient="index")
        response = requests.put(
            url=f"{self.database_url}/{ref}.json", headers=self.headers, data=json.dumps(data)
        )
        self.log.info(f"Set df entry {ref} in firebase. Response: {response.text}")

    def get_entry_df(self, ref: str) -> DataFrame | None:
        """Get a dataframe entry from firebase, by converting it from a dictionary"""
        if self._check_inactive():
            return None
        data = requests.get(url=f"{self.database_url}/{ref}.json").json()
        return DataFrame.from_dict(data, orient="index")


if __name__ == "__main__":
    firebase = FirebaseHandler()
    firebase.update_value(ref="To-Do/t-18002271", key="start_datum", value="2022_01_01")
