DROP TABLE IF EXISTS courses;
CREATE TABLE courses(
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	code TEXT,
	name TEXT,
	type TEXT,
	instructor TEXT
);

DROP TABLE IF EXISTS lectures;
CREATE TABLE lectures(
	courseid INTEGER,
	day INTEGER,
	hour INTEGER,
	room TEXT,
	PRIMARY KEY(courseid, day, hour),
	FOREIGN KEY(courseid) REFERENCES courses(id)
 );