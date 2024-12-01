-- Admin table
CREATE TABLE IF NOT EXISTS admin (
    email TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    token TEXT
);

-- Students table
CREATE TABLE IF NOT EXISTS students (
    rollNo INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    cnic TEXT NOT NULL,
    section TEXT NOT NULL,
    password TEXT NOT NULL
);

-- Diaries table
CREATE TABLE IF NOT EXISTS diaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT NOT NULL,
    text TEXT NOT NULL
);

-- Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rollNo INTEGER NOT NULL,
    date TEXT NOT NULL,
    present BOOLEAN NOT NULL,
    FOREIGN KEY (rollNo) REFERENCES students (rollNo)
);

-- Grades table
CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rollNo INTEGER NOT NULL,
    term TEXT NOT NULL,
    percentage REAL NOT NULL,
    FOREIGN KEY (rollNo) REFERENCES students (rollNo)
);

INSERT INTO admin (email, password, token)
SELECT 'admin@cms.com', 'admin', 'gj04tl5539'
WHERE NOT EXISTS (SELECT 1 FROM admin WHERE email = 'admin@cms.com');

