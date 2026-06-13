"""
Migration : ajoute la colonne createur_id à la table tutoriels.
Lance ce script une seule fois depuis le dossier du projet :
    python migrate_contributeur.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutolab.db')

db = sqlite3.connect(DB_PATH)

try:
    db.execute("ALTER TABLE tutoriels ADD COLUMN createur_id INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL")
    db.commit()
    print("✅ Colonne createur_id ajoutée avec succès.")
except Exception as e:
    if "duplicate column" in str(e).lower():
        print("ℹ️  La colonne createur_id existe déjà, rien à faire.")
    else:
        print(f"❌ Erreur : {e}")
finally:
    db.close()
