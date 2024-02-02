import requests
import json

from src._utils.common import secret
from src._utils.logger import create_logger



class FirebaseHandler:
    def __init__(self):
        self.log = create_logger("Firebase")
        self.headers = {'Content-Type': 'application/x-www-form-urlencoded', }
        if secret('FIREBASE_PROJECT'):
            self.active = True
            self.project = secret('FIREBASE_PROJECT')
        else:
            self.active = False
            self.log.warn("Could not load firebase project from environment variables. "
                           "It will ignore all future interaction")




    def get_list(self, ref: str, max_results: int = 100, convert_to_list: bool = True):
        """ Get a list of child-entries from a firebase object """
        if self.active is False:
            self.log.debug("Firebase client is not active. Ignoring get_list request")
            return
        reference_url = f'{self.project}/{ref}.json'
        params = {'orderBy': '"$key"', 'limitToFirst': max_results}
        response = requests.get(url=reference_url, params=params)
        if convert_to_list:
            list_json = response.json()
            return [list_json[key] for key in list_json]
        else:
            return response.json()


    def update_value(self, ref: str, key: str, value):
        """ Update a value of a firebase object """
        if self.active is False:
            self.log.debug("Firebase client is not active. Ignoring update_value request")
            return
        data = json.dumps({key: value})
        response = requests.patch(url=f'{self.project}/{ref}.json', headers=self.headers, data=data)
        print(f"FIREBASE: {response.text}")


    def delete_entry(self, ref: str):
        """ Delete an entry from firebase """
        if self.active is False:
            self.log.debug("Firebase client is not active. Ignoring delete_entry request")
            return
        requests.delete(url=f'{self.project}/{ref}.json')


    def get_entry(self, ref: str):
        """ Get an entry from firebase """
        if self.active is False:
            self.log.debug("Firebase client is not active. Ignoring get_entry request")
            return
        return requests.get(url=f'{self.project}/{ref}.json').json()


    def set_entry(self, ref: str, data: dict):
        """ Set an entry in firebase """
        if self.active is False:
            self.log.debug("Firebase client is not active. Ignoring set_entry request")
            return
        response = requests.put(url=f'{self.project}/{ref}.json', headers=self.headers, data=json.dumps(data))
        self.log.info(f"Set entry {ref} with data {data} in firebase. Response: {response.text}")



if __name__ == '__main__':
    firebase = FirebaseHandler()
    firebase.update_value(ref='To-Do/t-18002271', key='start_datum', value='2022_01_01')