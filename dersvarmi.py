#!/usr/bin/python

from bs4 import BeautifulSoup
from pyquery import PyQuery as pq
from soupselect import select
from datetime import date
import re

# =========================================================================
#                  TODO
# 1. Parse the schedule_url to get the room/hour pairs
# 2. Put them in a database where you can query quickly (sqlite maybe)
# 3. When the page is visited, get date/time info and check the
#    rooms at the floor -2.
# 4. After this, make another screen for printing the occupation for
#    all rooms in the building (ETA)
# =========================================================================


# define the semester periods (in month)
spring_period = (2, 6)
summer_period = (7, 8)
fall_period = (9, 1)


def find_semester(month=date.today().month, year=date.today().year):
    if month >= fall_period[0] or month <= fall_period[1]:
        semester = "%d/%d-1" % (year, year + 1)
    else:
        semester = "%d/%d-" % (year - 1, year)
        if spring_period[0] <= month <= spring_period[1]:
            semester += "2"
        else:
            semester += "3"
    return semester


def get_schedule_url(department="CMPE", semester=find_semester()):
    return "http://registration.boun.edu.tr/scripts/sch.asp?donem=%s&bolum=%s" % (semester, department)


def get_departments():
    d = pq(url='http://registration.boun.edu.tr/scripts/schdepsel.asp')
    departments = {}
    for dep in d('td.schtd').items():
        department_name = dep.text()
        department_code = dep('a').attr('href')
        department_code = department_code[department_code.find('bolum=') + 6:]
        departments[department_name] = department_code
    return departments


def extract_lecture_hours_helper(first, rest):
    """
    if rest is not None return [first|rest]
    else return None
    """
    if rest is None:
        return None
    else:
        return [first] + rest


def extract_lecture_hours(hours, lecture_count):
    """
    extracts the lecture hours from the given text
    by looking at the lecture lecture count
    """
    # base cases
    if (hours == '') and (lecture_count == 0):
        return []
    elif (hours == '') ^ (lecture_count == 0):
        return None

    if '2' <= hours[0] <= '9':  # 2,3,4,5,6,7,8,9
        return extract_lecture_hours_helper(
            int(hours[0]),
            extract_lecture_hours(hours[1:], lecture_count - 1))
    elif hours[0] == '1':
        if len(hours) >= 2 and hours[1] == '0':  # 10
            return extract_lecture_hours_helper(
                int(hours[0:2]),
                extract_lecture_hours(hours[2:], lecture_count - 2))
        else:
            # first try 1
            result = extract_lecture_hours_helper(
                int(hours[0]),
                extract_lecture_hours(hours[1:], lecture_count - 1))
            if result is not None:
                return result
            else:
                # then try 11, 12 or 13
                return extract_lecture_hours_helper(
                    int(hours[0:2]),
                    extract_lecture_hours(hours[2:], lecture_count - 2))
    else:
        return None  # cannot start with 0


def test_extract_lecture_hours():
    inputs = [('123', 3), ('12310', 4), ('1112', 2), ('12345', 4), ('111', 3)]
    outputs = [[1, 2, 3], [1, 2, 3, 10], [11, 12], [12, 3, 4, 5], [1, 1, 1]]

    for i, o in zip(inputs, outputs):
        if extract_lecture_hours(*i) != o:
            print(i, extract_lecture_hours(*i))
            break


def extract_lectures(day, hour, room):
    days = re.findall('[A-Z][^A-Z]*', day)
    # lecture_count = len(days)


def get_courses(schedule_url=get_schedule_url()):
    soup = BeautifulSoup(pq(url=schedule_url).html())
    courses = []
    # Second table contains the courses and first row of it is the header
    for index, c_row in enumerate(soup.select('table:nth-of-type(2) tr')[1:]):
        c_col = c_row.select('td')
        course_id = c_col[0].get_text()
        course_name = c_col[2].get_text()
        course_instr = c_col[5].get_text()
        course_days = c_col[6].get_text()
        course_hours = c_col[7].get_text()
        course_rooms = c_col[8].get_text()
    return courses


# test_extract_lecture_hours()
# departments = get_departments()
# courses = get_courses()