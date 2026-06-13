"""
Migration : crée la table tutoriel_images et ajoute createur_id.
Lance depuis le dossier projet : python migrate_tutomotion.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutomotion.db')
db = sqlite3.connect(DB_PATH)

# Table tutoriel_images
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
except Exception as e:
    print(f"❌ tutoriel_images : {e}")

# Colonne createur_id
try:
    db.execute("ALTER TABLE tutoriels ADD COLUMN createur_id INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL")
    db.commit()
    print("✅ Colonne createur_id ajoutée.")
except Exception as e:
    if "duplicate column" in str(e).lower():
        print("ℹ️  createur_id existe déjà.")
    else:
        print(f"❌ createur_id : {e}")

# Migrer les image_url existantes
rows = db.execute("SELECT id, image_url FROM tutoriels WHERE image_url != ''").fetchall()
migrated = 0
for row in rows:
    exists = db.execute("SELECT 1 FROM tutoriel_images WHERE tutoriel_id = ?", (row[0],)).fetchone()
    if not exists:
        db.execute("INSERT INTO tutoriel_images (tutoriel_id, url, position, est_couverture) VALUES (?,?,0,1)",
                   (row[0], row[1]))
        migrated += 1
db.commit()
print(f"✅ {migrated} image(s) existante(s) migrée(s).")

db.close()
print("\nMigration terminée. Redémarre Flask.")
