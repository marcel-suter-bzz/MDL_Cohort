from dataclasses import dataclass
from json import dumps


@dataclass
class Cohort:
    """
    a cohort of students
    """
    
    name: str
    moodle_id: int
    member_dict: dict
    current: bool
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        self._name = value
    @property
    def moodle_id(self):
        return self._moodle_id
    
    @moodle_id.setter
    def moodle_id(self, value):
        self._moodle_id = value
    @property
    def member_dict(self):
        return self._member_dict
    
    @member_dict.setter
    def member_dict(self, value):
        self._member_dict = value
        
    @property
    def current(self):
        return self._current
    
    @current.setter
    def current(self, value):
        self._current = value