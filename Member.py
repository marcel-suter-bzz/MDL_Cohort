from dataclasses import dataclass

from Person import Person


@dataclass
class Member:
    """
    A member of a group
    """
    person: Person
    azure: bool
    moodle: bool

    @property
    def person(self) -> Person:
        return self._person

    @person.setter
    def person(self, value: Person):
        self._person = value

    @property
    def azure(self) -> bool:
        return self._azure

    @azure.setter
    def azure(self, value: bool):
        self._azure = value

    @property
    def moodle(self) -> bool:
        return self._moodle

    @moodle.setter
    def moodle(self, value: bool):
        self._moodle = value
