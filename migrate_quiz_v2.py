"""
Migration : ajoute reponses_correctes et multiple à questionnaires.
Lance : python migrate_quiz_v2.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutomotion.db')
db = sqlite3.connect(DB_PATH)

for col, definition in [
    ('reponses_correctes', "TEXT DEFAULT ''"),
    ('multiple',           "INTEGER NOT NULL DEFAULT 0"),
]:
    try:
        db.execute(f"ALTER TABLE questionnaires ADD COLUMN {col} {definition}")
        db.commit()
        print(f"ok: '{col}' ajoutee.")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print(f"info: '{col}' existe deja.")
        else:
            print(f"erreur '{col}': {e}")

db.execute("UPDATE questionnaires SET type = 'qcm' WHERE type = 'texte'")
db.commit()
print("ok: types texte convertis en qcm.")
db.close()
print("Migration terminee. Redemarre Flask.")
