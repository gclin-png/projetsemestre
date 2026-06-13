"""
Migration : crée la table tutoriel_images.
Lance une seule fois : python migrate_images.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutolab.db')
db = sqlite3.connect(DB_PATH)

try:
    db.execute('''
        CREATE TABLE IF NOT EXISTS tutoriel_images (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            tutoriel_id    INTEGER NOT NULL REFERENCES tutoriels(id) ON DELETE CASCADE,
            url            TEXT    NOT NULL,
            position       INTEGER NOT NULL DEFAULT 0,
            est_couverture INTEGER NOT NULL DEFAULT 0,
            ajoute_le      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()
    print("✅ Table tutoriel_images créée.")

    # Migrer les image_url existantes vers la nouvelle table
    rows = db.execute("SELECT id, image_url FROM tutoriels WHERE image_url != ''").fetchall()
    for row in rows:
        exists = db.execute("SELECT 1 FROM tutoriel_images WHERE tutoriel_id = ?", (row[0],)).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO tutoriel_images (tutoriel_id, url, position, est_couverture) VALUES (?,?,0,1)",
                (row[0], row[1])
            )
    db.commit()
    print(f"✅ {len(rows)} image(s) existante(s) migrée(s).")
except Exception as e:
    print(f"❌ Erreur : {e}")
finally:
    db.close()
