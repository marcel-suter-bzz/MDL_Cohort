import os
from dataclasses import dataclass

import requests


@dataclass
class Person:
    """
    a person
    """

    username: str
    moodle_id: int
    active: bool

    def __post_init__(self):
        """
        Initialize the person with data from Moodle
        """
        url = f'{os.getenv("MOODLEURL")}' \
              f'?wstoken={os.getenv("MOODLETOKEN")}' \
              f'&moodlewsrestformat=json' \
              f'&wsfunction=core_user_get_users_by_field'
        if self.moodle_id != -1:
            url += f'&field=id' \
                  f'&values[0]={self.moodle_id}'
        elif self.username != '':
            url += f'&field=username' \
                  f'&values[0]={self.username}'
        else:
            return

        response = requests.get(url, verify=True)
        if len(response.json()) == 0:
            self.active = False
            self.moodle_id = -1
        else:
            self.moodle_id = response.json()[0]['id']
            self.username = response.json()[0]['username']
            for custom_field in response.json()[0]['customfields']:
                if custom_field['shortname'] == 'quit':
                    self.quit = custom_field['value'] == 1

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        self._username = value
    @property
    def moodle_id(self) -> int:
        return self._moodle_id

    @moodle_id.setter
    def moodle_id(self, value: int):
        self._moodle_id = value
    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value