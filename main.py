"""
main module for the moodle cohort updater
"""
import json
import os
from datetime import datetime
import re

import requests
from dotenv import load_dotenv

from Cohort import Cohort
from Member import Member
from Person import Person


def main():
    """
    main function
    :return:
    """
    load_dotenv()
    cohort_dict = {}
    people_dict = {}

    load_ad_users(cohort_dict, people_dict)
    load_moodle_users(cohort_dict, people_dict)
    update_moodle_cohorts(cohort_dict)
    pass


def load_ad_users(cohort_dict: dict, people_dict: dict) -> None:
    """
    loads the users from active directory
    :param cohort_dict: the cohort dictionary
    :param people_dict: the people dictionary
    :return:
    """
    semesters = get_semesters()
    with open(os.getenv('GROUPFILE'), 'r', encoding='UTF-8') as file:
        groups = json.load(file)
        for group in groups:
            if not is_relevant_group(group['name']):
                if os.getenv('DEBUG') == 'True':
                    print(f'Skipping AD Group {group["name"]}')
                continue

            if os.getenv('DEBUG') == 'True':
                print(f'Loading AD Group {group["name"]}')
            for ix, semester in enumerate(semesters):
                current = ix == 0
                group_key = group['name'] + semester
                ad_group = Cohort(name=group_key, moodle_id=-1, member_dict={}, current=current)

                for email in group['students']:
                    if email in people_dict:  # See if we already have this person
                        person = people_dict[email]
                    else:  # If not, create a new person
                        person = Person(username=email, moodle_id=-1, active=True)
                        people_dict[email] = person
                    member = Member(azure=True, moodle=False, person=person)
                    ad_group.member_dict[email] = member
                cohort_dict[group_key] = ad_group


def load_moodle_users(cohort_dict: dict, people_dict: dict) -> None:
    """
    loads the cohorts and their members from moodle
    :param cohort_dict: the cohort dictionary
    :param people_dict: the people dictionary
    :return: None
    """
    url = f'{os.getenv("MOODLEURL")}' \
          f'?wstoken={os.getenv("MOODLETOKEN")}' \
          f'&wsfunction=core_cohort_get_cohorts' \
          f' &moodlewsrestformat=json'
    response = requests.get(url, verify=True)
    for cohort in response.json():
        cohort_name = cohort['name']
        if cohort_name in cohort_dict:
            if os.getenv('DEBUG') == 'True':
                print(f'Loading Moodle Cohort {cohort_name}')
            cohort_dict[cohort_name].moodle_id = cohort['id']
            load_members(cohort_dict[cohort_name], people_dict)


def load_members(cohort: Cohort, people_dict: dict) -> None:
    """
    reads the members of a cohort from moodle into the member-dict
    :param cohort: the cohort
    :param people_dict: the people dictionary
    """
    url = f'{os.getenv("MOODLEURL")}' \
          f'?wstoken={os.getenv("MOODLETOKEN")}' \
          f'&wsfunction=core_cohort_get_cohort_members' \
          f'&cohortids[0]={cohort.moodle_id}' \
          f'&moodlewsrestformat=json'
    response = requests.get(url, verify=True)
    for moodle_cohort in response.json():
        for user_id in moodle_cohort["userids"]:
            # Search for a matching person in the people_dict
            for person in people_dict.values():
                if person.moodle_id == user_id:
                    break
            else:
                # If we didn't find a match, create a new person
                person = Person(username='', moodle_id=user_id, active=True)
                people_dict[person.username] = person

            if person.username in cohort.member_dict:
                member = cohort.member_dict[person.username]
                member.moodle = True
            else:
                member = Member(azure=False, moodle=True, person=person)
                cohort.member_dict[person.username] = member

            pass


def update_moodle_cohorts(cohort_dict: dict) -> None:
    """
    updates the moodle cohorts
    """
    for cohort in cohort_dict.values():
        if os.getenv('DEBUG') == 'True':
            print(f'Updating {cohort.name}')
        if cohort.moodle_id == -1:
            create_moodle_cohort(cohort)

        update_moodle_cohort(cohort)
        pass


def update_moodle_cohort(cohort: Cohort) -> None:
    """
    updates the members in a moodle cohort
    :param cohort: the cohort
    """
    for member in cohort.member_dict.values():
        student = member.person
        if member.azure is True and member.moodle is False and student.active is True:
            add_member(cohort, student)

        if cohort.current is False and \
                member.moodle is True and \
                (member.azure is False or student.active is False):
            delete_members(cohort, student)


def add_member(cohort: Cohort, student: Person) -> None:
    """
    adds a member to a cohort
    :param cohort: the cohort
    :param student: the student
    """
    url = f'{os.getenv("MOODLEURL")}' \
          f'?wstoken={os.getenv("MOODLETOKEN")}' \
          f'&wsfunction=core_cohort_add_cohort_members' \
          f'&moodlewsrestformat=json'
    data = {
        'cohortid': cohort.moodle_id,
        'userids[0]': student.moodle_id
    }
    if os.environ['CREATE'] == 'True' or \
            os.environ['CREATE'] == 'Manual' and \
            input(f'Add {student.username} to {cohort.name} (y/n)? ') == 'y':
        response = requests.get(url, data=data, verify=True)
        if os.getenv('DEBUG') == 'True':
            print(f'add_member {student.username} to {cohort.name}')
    else:
        if os.getenv('DEBUG') == 'True':
            print(f'Not added {cohort.name} / {student}')


def delete_members(cohort: Cohort, student: Person) -> None:
    """
       deletes a member from the group (cohort)
       :param cohort: the cohort
       :param student: the student
       :return: None
       """
    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_delete_cohort_members&moodlewsrestformat=json'
    data = {
        'members[0][cohortid]': cohort.moodle_id,
        'members[0][userid]': student.moodle_id
    }

    if os.environ['DELETE'] == 'True' or \
            os.environ['DELETE'] == 'Manual' and \
            input(f'Remove {student.username} from {cohort.name} (y/n)? ') == 'y':
        response = requests.post(url, params=data, verify=True)
        if os.getenv('DEBUG') == 'True':
            print(f'Delete {cohort.name} / {student}')
    else:
        if os.getenv('DEBUG') == 'True':
            print(f'Not deleted {cohort.name} / {student}')


def create_moodle_cohort(cohort: Cohort) -> None:
    """
    creates a new moodle cohort
    :param cohort: the cohort
    """
    url = f'{os.getenv("MOODLEURL")}' \
          f'?wstoken={os.getenv("MOODLETOKEN")}' \
          f'&wsfunction=core_cohort_create_cohorts' \
          f'&moodlewsrestformat=json'
    data = {
        'cohorts[0][categorytype][type]': 'id',
        'cohorts[0][categorytype][value]': find_groupid(cohort.name),
        'cohorts[0][name]': cohort.name,
        'cohorts[0][idnumber]': cohort.name
    }
    if os.environ['CREATE'] == 'True' or \
            os.environ['CREATE'] == 'Manual' and \
            input(f'Create {cohort.name} in {find_groupid(cohort.name)} (y/n)? ') == 'y':
        response = requests.get(url, verify=True)
        cohort.moodle_id = response.json()[0]['id']

        if os.getenv('DEBUG') == 'True':
            print(f'create_cohort {cohort.name}')
    pass

def is_relevant_group(group: str) -> bool:
    """
    checks if a group is relevant
    :param group:
    :return:
    """
    if not re.match(r'[A-Z]{2,3}\d{2}[a-z]$', group):
        if os.getenv('DEBUG') == 'True':
            print(f'Skipping AD Group {group}')
        return False

    match = re.search(r'\d{2}', group)
    if match:
        current_year = int(datetime.today().strftime("%Y"))
        group_year = 2000 + int(match.group())
        if group_year + 5 < current_year:
            if os.getenv('DEBUG') == 'True':
                print(f'Skipping AD Group {group}')
            return False

    return True


def get_semesters() -> list[str]:
    """
    gets the current and next semester
    :return:
    """
    today = datetime.today()
    year = int(today.strftime("%Y"))
    month = today.strftime("%m")
    semesters = list()

    if '02' <= month <= '07':
        semesters.append('_' + str(year) + 'FR')
        semesters.append('_' + str(year) + 'HE')
    elif month == '01':
        semesters.append('_' + str(year - 1) + 'HE')
        semesters.append('_' + str(year) + 'FR')
    else:
        semesters.append('_' + str(year) + 'HE')
        semesters.append('_' + str(year + 1) + 'FR')

    return semesters


def find_groupid(name: str) -> int:
    """
    finds the category id by matching the cohortname
    :param name:
    :return:
    """
    categories = {  # TODO regex / values from .env
        'ABU?[0-9]{2}[a-z]': '17',
        'FB(A|B|M)[0-9]{2}[a-z]': '7',
        'I(A|M)[0-9]{2}[a-z]': '3',
        'ME[0-9]{2}[a-z]': '11',
        '[A-Z]{1,20}': '2',
    }
    for pattern in categories:
        if re.match(rf'{pattern}', name):
            return categories[pattern]

    return 1  # TODO value from .env


if __name__ == '__main__':
    main()
