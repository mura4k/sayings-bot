import sqlite3
import pandas as pd

data = pd.read_excel('../data/sayings.xlsx')

conn = sqlite3.connect('../data/stats_by_saying.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS sayings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    russian_saying TEXT,
    english_correct_translation TEXT,
    english_incorrect_translation TEXT,
    difficulty_level INTEGER,
    attempts INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0
)
''')

for _, row in data.iterrows():
    cursor.execute('''
    INSERT INTO sayings (russian_saying, english_correct_translation, english_incorrect_translation, difficulty_level)
    VALUES (?, ?, ?, ?)
    ''', (row['russian_sayings'], row['english_correct_translation'], row['english_incorrect_translation'], row['difficulty_level']))

conn.commit()
conn.close()
