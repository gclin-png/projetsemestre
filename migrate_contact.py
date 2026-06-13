"""
Migration : crée la table messages_contact.
Lance : python migrate_contact.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutomotion.db')
db = sqlite3.connect(DB_PATH)

try:
    db.execute('''
        CREATE TABLE IF NOT EXISTS messages_contact (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nom         TEXT    NOT NULL,
            email       TEXT    NOT NULL,
            sujet       TEXT    NOT NULL,
            message     TEXT    NOT NULL,
            image_url   TEXT    DEFAULT '',
            lu          INTEGER NOT NULL DEFAULT 0,
            envoye_le   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()
    print("ok : table messages_contact creee.")
except Exception as e:
    print(f"erreur : {e}")
finally:
    db.close()
