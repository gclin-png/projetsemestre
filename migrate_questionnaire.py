"""
Migration : crée les tables questionnaires et reponses_utilisateurs.
Lance depuis le dossier projet : python migrate_questionnaire.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutomotion.db')
db = sqlite3.connect(DB_PATH)

try:
    db.execute('''
        CREATE TABLE IF NOT EXISTS questionnaires (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tutoriel_id  INTEGER NOT NULL REFERENCES tutoriels(id) ON DELETE CASCADE,
            question     TEXT    NOT NULL,
            type         TEXT    NOT NULL DEFAULT 'texte',
            options      TEXT    DEFAULT '',
            ordre        INTEGER NOT NULL DEFAULT 0,
            cree_le      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Table questionnaires créée.")
except Exception as e:
    print(f"❌ questionnaires : {e}")

try:
    db.execute('''
        CREATE TABLE IF NOT EXISTS reponses_utilisateurs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
            tutoriel_id     INTEGER NOT NULL REFERENCES tutoriels(id)    ON DELETE CASCADE,
            question_id     INTEGER NOT NULL REFERENCES questionnaires(id) ON DELETE CASCADE,
            reponse         TEXT    NOT NULL,
            soumis_le       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Table reponses_utilisateurs créée.")
except Exception as e:
    print(f"❌ reponses_utilisateurs : {e}")

db.commit()
db.close()
print("\nMigration terminée. Redémarre Flask.")
