from dataclasses import dataclass
from json import dumps


@dataclass
class Group:
    """
    a group of students

    author: Marcel Suter
    """

    name: str
    moodle_id: int
    students: list
    is_current: bool

    @property
    def __dict__(self):
        return {
            'name': self.name,
            'moodle_id': self.moodle_id,
            'students': self.students
        }

    @property
    def json(self):
        return dumps(self.__dict__)

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
    def students(self):
        return self._students

    @students.setter
    def students(self, value):
        self._students = value

    @property
    def is_current(self):
        return self._is_current

    @is_current.setter
    def is_current(self, value):
        self._is_current = value