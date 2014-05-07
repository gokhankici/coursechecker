#!/usr/bin/python

from bs4 import BeautifulSoup
from pyquery import PyQuery as pq
from soupselect import select
import urllib
from datetime import date

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
spring_period = (2,6)
summer_period = (7,8)
fall_period   = (9,1)

class Course(object):
	"""Class to represent a course at BOUN"""
	def __init__(self, course_id, name, instructor, days, hours, rooms):
		self.course_id = course_id
		self.name = name
		self.instructor = instructor
		self.days = days
		self.hours = hours
		self.rooms = rooms

	def joined_time():
		return zip(days, hours, rooms)

def find_semester(month = date.today().month, year  = date.today().year):
	if month >= fall_period[0] or month <= fall_period[1]:
		semester = "%d/%d-1" % (year, year + 1)
	else:
		semester = "%d/%d-" % (year - 1, year) 
		if spring_period[0] <= month <= spring_period[1]:
			semester = semester + "2"
		else:
			semester = semester + "3"
	return semester

def get_schedule_url(department = "CMPE", semester = find_semester()):
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

def get_courses(schedule_url = get_schedule_url()):
	soup = BeautifulSoup(pq(url=schedule_url).html())
	courses = []
	# Second table contains the courses and first row of it is the header
	for index, c_row in enumerate(soup.select('table:nth-of-type(2) tr')[1:]):
		c_col = c_row.select('td')
		course_id    = c_col[0].get_text()
		print course_id
		# course_name  = c_row.select('td nth-of-type(3)')
		# course_instr = c_row.select('td nth-of-type(6)')
		# course_days  = c_row.select('td nth-of-type(7)')
		# course_hours = c_row.select('td nth-of-type(8)')
		# course_rooms = c_row.select('td nth-of-type(9)')
		# print course_id, course_name, course_instr, course_days, course_hours, course_rooms
		# courses.append(Course(course_name, None, None, None, None))
	return courses


departments = get_departments()
courses = get_courses()