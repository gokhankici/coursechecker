# =========================================================================
#                  TODO
# =========================================================================
# [X] Parse the schedule_url to get the room/hour pairs
# [X] Put them in a database where you can query quickly (sqlite maybe)
# [ ] When the page is visited, get date/time info and check the
#     rooms at the floor #2.
# [ ] After this, make another screen for printing the occupation for
#     all rooms in the building (ETA)
# =========================================================================


import os
import sqlite3
import re, sys
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from bs4 import BeautifulSoup
from pyquery import PyQuery as pq
from soupselect import select
from datetime import date
from unidecode import unidecode

app = Flask(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'courses.db'),
    DEBUG=True,
    SECRET_KEY='development key',
))

# ##############################################################################
# ###############  database ####################################################
# ##############################################################################

def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.row
    return rv

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
    
# ##############################################################################
# ############### controllers ##################################################
# ##############################################################################

@app.route('/')
def show_entries():
    db = get_db()
    cur = db.execute('SELECT title, text from entries order by id desc')
    entries = cur.fetchall()
    return render_template('show_entries.html', entries=entries)

# ##############################################################################
# ############### functions used for crawling the website ######################
# ##############################################################################

# define the semester periods (in month)
spring_period = (2, 6)
summer_period = (7, 8)
fall_period = (9, 1)
day_map = {'M' :  1, 'T' :  2, 'W' :  3, 'Th' :  4,  'F' :  5,
            1  : 'M', 2  : 'T', 3  : 'W', 4   : 'Th', 5  : 'F'}


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
    if rest is not None:
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
        return

    if '2' <= hours[0] <= '9':  # 2,3,4,5,6,7,8,9
        return extract_lecture_hours_helper(
            int(hours[0]),
            extract_lecture_hours(hours[1:], lecture_count - 1))
    elif hours[0] == '1':
        if len(hours) >= 2 and hours[1] == '0':  # 10
            return extract_lecture_hours_helper(
                int(hours[0:2]),
                extract_lecture_hours(hours[2:], lecture_count - 1))
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
                    extract_lecture_hours(hours[2:], lecture_count - 1))
    else:
        return  # cannot start with 0


def test_extract_lecture_hours():
    inputs = [('123', 3), ('12310', 4), ('1112', 2), ('12345', 4), ('111', 3)]
    outputs = [[1, 2, 3], [1, 2, 3, 10], [11, 12], [12, 3, 4, 5], [1, 1, 1]]

    for i, o in zip(inputs, outputs):
        if extract_lecture_hours(*i) != o:
            print('Error with input %s !\nexpected: %s, got: %s' % (i, o, extract_lecture_hours(*i)))
            break


def extract_lectures(day, hour, room):
    if day == '' or day == 'TBA' or hour == '':
        return

    days = re.findall('[A#Z][^A#Z]*', day)
    hours = extract_lecture_hours(hour, len(days))
    rooms = re.findall('[a#zA#Z\.]+\s?[a#zA#Z\d\.]*', room)

    # discard lectures with no day/hour/room info
    if hours is None:
        # print '***** day : |%s|, hour : |%s|, room : |%s| *****' % (day, hour, room)
        # print '***** days: |%s|, hours: |%s|, rooms: |%s| *****' % (days, hours, rooms)
        return
    elif not (len(days) == len(hours) == len(rooms)):
        if len(rooms) > 0 and all(rooms[0] == item for item in rooms):
            rooms = [rooms[0]] * len(days)
        else:
            # print '***** day : |%s|, hour : |%s|, room : |%s| *****' % (day, hour, room)
            # print '***** days: |%s|, hours: |%s|, rooms: |%s| *****' % (days, hours, rooms)
            return

    return zip(days, hours, rooms)


def get_courses(conn, schedule_url=get_schedule_url()):
    soup = BeautifulSoup(pq(url=schedule_url).html())
    c = conn.cursor()

    # Second table contains the courses and first row of it is the header
    for index, c_row in enumerate(soup.select('table:nth-of-type(2) tr')[1:]):
        c_col = c_row.select('td')
        is_course_def = unidecode(c_col[0].get_text(strip=True)) != ''

        if is_course_def: 
            course_code  = unidecode(c_col[0].get_text(strip=True))
            course_name  = unidecode(c_col[2].get_text(strip=True))
            course_type  = 'LECTURE'
        else:
            course_type  = unidecode(c_col[2].get_text(strip=True))

        course_instr = unidecode(c_col[5].get_text(strip=True))
        course_days  = unidecode(c_col[6].get_text(strip=True))
        course_hours = unidecode(c_col[7].get_text(strip=True))
        course_rooms = unidecode(c_col[8].get_text(strip=True))

        lectures = extract_lectures(course_days, course_hours, course_rooms)
        if 'course_code' in locals() and lectures is not None:
            c.execute('INSERT INTO courses (code,name,type,instructor) VALUES (?,?,?,?)',
                (course_code, course_name, course_type, course_instr))
            course_table_id = c.lastrowid
            for d,h,r in lectures:
                c.execute('INSERT INTO lectures VALUES (?,?,?,?)', (course_table_id, d, h, r))


def fill_db():
    os.system('rm #f courses.db')
    os.system('sqlite3 courses.db < tables.sql')
    conn = sqlite3.connect('courses.db')

    print 'CRAWLING REGISTRATION WEBSITE ...'
    departments = get_departments()
    dep_size = len(departments)
    for index, dep_n in enumerate(departments):
        url = get_schedule_url(departments[dep_n])
        print '%-2d/%-2d : %60s' % (index + 1, dep_size, dep_n)
        get_courses(conn, url)
    
    conn.commit()
    conn.close()
    print 'DONE !'

# ##############################################################################
# ######################### start the application ##############################
# ##############################################################################

if __name__ == '__main__':
    app.run()
