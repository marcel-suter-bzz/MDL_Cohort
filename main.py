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
    people_dict = dict()
    load_ad_groups(groups_dict, people_dict)
    load_mdl_cohorts(groups_dict)

    for group_key in groups_dict:
        group = groups_dict[group_key]
        if group.moodle_id == -1:
            create_cohort(group)
        load_members(group, people_dict)
        update_cohorts(group, people_dict)
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


def find_groupid(name: str) -> int:
    """
    finds the category id by matching the cohortname
    :param name:
    :return:
    """
    categories = {
        'ABU?[0-9]{2}[a-z]': '17',
        'FB(A|B|M)[0-9]{2}[a-z]': '7',
        'I(A|M)[0-9]{2}[a-z]': '3',
        'ME[0-9]{2}[a-z]': '11',
        '[A-Z]{1,20}': '2',
    }
    for pattern in categories:
        if re.match(rf'{pattern}', name):
            return categories[pattern]

    return 1


def update_cohorts(group: Group, people_dict: dict) -> None:
    """
    updates the moodle cohorts
    :param group:
    :param people_dict:
    :return:
    """
    for student in group.students:
        if people_dict[student].moodle_id == -1:
            add_members(group, people_dict[student])
        elif not people_dict[student].azure_user:
            delete_members(group, people_dict[student])


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
        if item['name'] in cohort_dicts:
            cohort_dicts[item['name']].moodle_id = item['id']


def load_members(cohort: Group, people_dict: dict) -> None:
    """
    reads the members of a cohort into the cohort-dict
    :param cohort: the cohort
    :param people_dict: a dictionary of all people
    :return:
    """
    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_get_cohort_members' \
          '&cohortids[0]=' + str(cohort.moodle_id) + '&moodlewsrestformat=json'
    response = requests.get(url)
    users = []
    try:
        for item in response.json():
            for user_id in item["userids"]:
                if not has_moodle_id(people_dict, user_id):
                    users.append(user_id)
            if users:
                load_users(cohort, people_dict, users)
    except:
        print(f'Error in load_members: {user_id}')


def has_moodle_id(people_dict: dict, user_id: int) -> bool:
    for person_key in people_dict:
        if people_dict[person_key].moodle_id == user_id:
            return True
    return False


def load_users(cohort: Group, people_dict: dict, user_ids: list) -> None:
    """
    loads the moodle users
    :param cohort:
    :param people_dict:
    :param user_ids:
    :return:
    """

    query = ''
    count = 0
    for user_id in user_ids:
        query += '&values[' + str(count) + ']=' + str(user_id)
        count += 1

    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_user_get_users_by_field&field=id' + \
          query + '&moodlewsrestformat=json'
    response = requests.get(url)
    for item in response.json():
        key = item['username']
        if key in people_dict:
            people_dict[key].moodle_id = item['id']
        else:
            people_dict[key] = Person(key, item['id'], False)
        if key not in cohort.students:
            cohort.students.append(key)


def load_ad_groups(group_dict: dict, person_dict: dict) -> None:
    """
    loads the groups and members from azure ad export
    :param group_dict:
    :param person_dict:
    :return:
    """
    semeters = get_semesters()
    with open(os.getenv('GROUPFILE'), 'r', encoding='UTF-8') as file:
        groups = json.load(file)
        for group in groups:
            for semester in semeters:
                group_key = group['name'] + semester
                group_dict[group_key] = Group(group_key, -1, group['students'])
            for email in group['students']:
                if email not in person_dict:
                    person_dict[email] = Person(email, -1, True)


def get_semesters() -> list[str]:
    """
    gets the current and next semester
    :return:
    """
    today = datetime.today()
    year = int(today.strftime("%Y"))
    month = today.strftime("%m")
    semesters = list()

    if month == '01':
        semesters.append('_' + str(year - 1) + 'HE')
    if '01' <= month <= '07':
        semesters.append('_' + str(year) + 'FR')
    if '05' <= month <= '12':
        semesters.append('_' + str(year) + 'HE')
    if '11' <= month <= '12':
        semesters.append('_' + str(year + 1) + 'FR')
    return semesters


if __name__ == '__main__':
    main()
