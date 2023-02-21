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


def create_cohort(group):
    """
    creates a new cohort in moodle
    :param group: the group to be created
    :return:
    """

    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_create_cohorts&moodlewsrestformat=json'

    data = {
        'cohorts[0][categorytype][type]': 'id',
        'cohorts[0][categorytype][value]': find_cohortid(group.name),
        'cohorts[0][name]': group.name,
        'cohorts[0][idnumber]': group.name
    }

    if os.environ['DEBUG'] == 'False':
        response = requests.post(url, params=data)
        content = response.json()
        group.moodle_id = content[0]['id']

    print(f'create_cohort {group.name}')


def find_cohortid(name):
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


def update_cohorts(group, people_dict):
    """
    updates the moodle cohorts
    :param group:
    :param people_dict:
    :return:
    """
    for student in group.students:
        if people_dict[student].moodle_id == -1:
            add_members(group, people_dict[student])
        elif people_dict[student].azure_user == False:
            print(f'Delete {group.name} / {student}')


def add_members(group, student):
    """
    adds all new members to a cohort
    :param group: the group (moodle cohort)
    :param student: the student to be added
    :return:
    """
    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_add_cohort_members&moodlewsrestformat=json'
    data = {}
    data['members[0][cohorttype][type]'] = 'id'
    data['members[0][cohorttype][value]'] = group.moodle_id
    data['members[0][usertype][type]'] = 'username'
    data['members[0][usertype][value]'] = student.email

    if os.environ['DEBUG'] == 'False':
        response = requests.post(url, params=data)
        foo = response.json()
    print(f'Add {group.name} / {student}')


def load_mdl_cohorts(cohort_dicts):
    """
    TODO
    :param cohort_dicts:
    :return:
    """
    url = os.getenv('MOODLEURL') + '?wstoken=' + os.getenv('MOODLETOKEN') + \
          '&wsfunction=core_cohort_get_cohorts&moodlewsrestformat=json'
    response = requests.get(url)
    for item in response.json():
        if item['name'] in cohort_dicts:
            cohort_dicts[item['name']].moodle_id = item['id']


def load_members(cohort, people_dict):
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
        pass


def has_moodle_id(people_dict, user_id):
    for person_key in people_dict:
        if people_dict[person_key].moodle_id == user_id:
            return True
    return False


def load_users(cohort, people_dict, user_ids):
    """
    loads the moodle users
    :param user_ids: list of user-ids
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


def load_ad_groups(group_dict, person_dict):
    """
    TODO
    :param group_dict:
    :param person_dict:
    :return:
    """
    semeters = get_semesters()
    with open(os.getenv('DATAPATH') + 'groups2.json', 'r', encoding='UTF-8') as file:
        groups = json.load(file)
        for group in groups:
            for semester in semeters:
                group_key = group['name'] + semester
                group_dict[group_key] = Group(group_key, -1, group['students'])
            for email in group['students']:
                if email not in person_dict:
                    person_dict[email] = Person(email, -1, True)


def get_semesters():
    """
    gets the current and next semester
    """
    today = datetime.today()
    year = int(today.strftime("%Y"))
    month = today.strftime("%m")
    semesters = list()

    if month == '01':
        semesters.append('_' + str(year - 1) + 'HE')
    if month >= '01' and month <= '07':
        semesters.append('_' + str(year) + 'FR')
    if month >= '05' and month <= '12':
        semesters.append('_' + str(year) + 'HE')
    if month >= '11' and month <= '12':
        semesters.append('_' + str(year + 1) + 'FR')
    return semesters


if __name__ == '__main__':
    main()
