"""
Migration : ajoute la colonne avatar_url à la table utilisateurs.
Lance depuis le dossier projet : python migrate_avatar.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutomotion.db')
db = sqlite3.connect(DB_PATH)

try:
    db.execute("ALTER TABLE utilisateurs ADD COLUMN avatar_url TEXT DEFAULT ''")
    db.commit()
    print("✅ Colonne avatar_url ajoutée avec succès.")
except Exception as e:
    if "duplicate column" in str(e).lower():
        print("ℹ️  La colonne avatar_url existe déjà, rien à faire.")
    else:
        print(f"❌ Erreur : {e}")
finally:
    db.close()