import json
import os
import re
from datetime import datetime

import requests
from dotenv import load_dotenv

from group import Group
from person import Person


def main():
    load_dotenv()
    groups_dict = dict()
    load_ad_groups(groups_dict)
    load_mdl_cohorts(groups_dict)

    for group_key in groups_dict:
        print(f'Processing {group_key}')
        group = groups_dict[group_key]
        if group.moodle_id == -1:
            create_cohort(group)
        update_cohorts(group)
    pass


def create_cohort(group: Group) -> None:
    """
    creates a new cohort in moodle
    :param group: the group to be created
    :return:
    """

    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_create_cohorts&moodlewsrestformat=json'

    data = {
        'cohorts[0][categorytype][type]': 'id',
        'cohorts[0][categorytype][value]': find_groupid(group.name),
        'cohorts[0][name]': group.name,
        'cohorts[0][idnumber]': group.name
    }

    if os.environ['CREATE'] == 'True' or \
            os.environ['CREATE'] == 'Manual' and \
            input(f'Create {group.name} in {find_groupid(group.name)} (y/n)? ') == 'y':
        response = requests.post(url, params=data)
        content = response.json()
        group.moodle_id = content[0]['id']

        print(f'create_cohort {group.name}')


def update_cohorts(cohort: Group) -> None:
    """
    updates the moodle cohorts
    :param cohort:
    :return:
    """
    for student in cohort.students:
        if student.moodle_id == -1:
            add_members(cohort, student)
        elif student.azure_user is False and cohort.is_current is False:
            delete_members(cohort, student)


def add_members(group: Group, student: Person) -> None:
    """
    adds all new members to a cohort
    :param group: the group (moodle cohort)
    :param student: the student to be added
    :return:
    """
    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_add_cohort_members&moodlewsrestformat=json'
    data = {
        'members[0][cohorttype][type]': 'id',
        'members[0][cohorttype][value]': group.moodle_id,
        'members[0][usertype][type]': 'username',
        'members[0][usertype][value]': student.email
    }

    if os.environ['CREATE'] == 'True' or \
            os.environ['CREATE'] == 'Manual' and \
            input(f'Add {student.email} to {group.name} (y/n)? ') == 'y':
        response = requests.post(url, params=data)
        print(f'Add {group.name} / {student}')
    else:
        print(f'Not added {group.name} / {student}')


def delete_members(group: Group, student: Person) -> None:
    """
    deletes a member from the group (cohort)
    :param group:
    :param student:
    :return:
    """
    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_delete_cohort_members&moodlewsrestformat=json'
    data = {
        'members[0][cohortid]': group.moodle_id,
        'members[0][userid]': student.moodle_id
    }

    if os.environ['DELETE'] == 'True' or \
            os.environ['DELETE'] == 'Manual' and \
            input(f'Remove {student.email} from {group.name} (y/n)? ') == 'y':
        response = requests.post(url, params=data)
        print(f'Delete {group.name} / {student}')
    else:
        print(f'Not deleted {group.name} / {student}')


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


def load_ad_groups(group_dict: dict) -> None:
    """
    loads the groups and members from azure ad export
    :param group_dict:
    :return:
    """
    semesters = get_semesters()
    with open(os.getenv('GROUPFILE'), 'r', encoding='UTF-8') as file:
        groups = json.load(file)
        for group in groups:
            for ix, semester in enumerate(semesters):
                current = ix == 0
                group_key = group['name'] + semester
                ad_group = Group(group_key, -1, list(), current)

                for email in group['students']:
                    person = Person(email=email, moodle_id=-1, azure_user=True)
                    ad_group.students.append(person)
                group_dict[group_key] = ad_group


def load_mdl_cohorts(cohort_dicts: dict) -> None:
    """
    loads all moodle cohorts
    :param cohort_dicts:
    :return:
    """
    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_get_cohorts&moodlewsrestformat=json'
    response = requests.get(url)
    for item in response.json():
        cohort_name = item['name']
        if cohort_name in cohort_dicts:
            cohort_dicts[cohort_name].moodle_id = item['id']
            load_members(cohort_dicts[cohort_name])


def load_members(cohort: Group) -> None:
    """
    reads the members of a cohort into the cohort-dict
    :param cohort: the cohort
    :return: None
    """
    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_get_cohort_members' \
          '&cohortids[0]=' + str(cohort.moodle_id) + '&moodlewsrestformat=json'
    response = requests.get(url)
    # try:
    for member in response.json():
        user_dict = dict()
        for user_id in member["userids"]:
            user_dict[user_id] = ''
    if user_dict:
        load_users(user_dict)
        for moodle_id, user in user_dict.items():
            student_ix = get_student_index(cohort, user)
            if student_ix == -1:
                student = Person(email=user, moodle_id=moodle_id, azure_user=False)
                cohort.students.append(student)
            else:
                cohort.students[student_ix].moodle_id = moodle_id
            pass
        pass
    # except:
    #    print(f'Error in load_members: {cohort.name}')


def get_student_index(cohort: Group, email):
    i = 0
    while i < len(cohort.students):
        if cohort.students[i].email == email:
            return i
        i += 1
    return -1


def load_users(user_dict):
    query = ''
    count = 0
    for user_id in user_dict:
        query += '&values[' + str(count) + ']=' + str(user_id)
        count += 1
    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_user_get_users_by_field&field=id' + \
          query + '&moodlewsrestformat=json'
    response = requests.get(url)
    for user in response.json():
        user_dict[user['id']] = user['username']


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


if __name__ == '__main__':
    main()
