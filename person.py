from dataclasses import dataclass
from json import dumps


@dataclass
class Person:
    """
    a person

    author: Marcel Suter
    """
    email: str
    moodle_id: int
    azure_user: bool

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
        self._email = value

    @property
    def moodle_id(self):
        return self._moodle_id

    @moodle_id.setter
    def moodle_id(self, value):
        self._moodle_id = value
        
    @property
    def azure_user(self):
        return self._azure_user
    
    @azure_user.setter
    def azure_user(self, value):
        self._azure_user = value
