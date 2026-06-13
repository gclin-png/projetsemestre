"""
Migration : ajoute la colonne accroche à la table tutoriels.
Lance depuis le dossier projet : python migrate_accroche.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutomotion.db')
db = sqlite3.connect(DB_PATH)

try:
    db.execute("ALTER TABLE tutoriels ADD COLUMN accroche TEXT DEFAULT ''")
    db.commit()
    print("✅ Colonne accroche ajoutée.")
except Exception as e:
    if "duplicate column" in str(e).lower():
        print("ℹ️  La colonne accroche existe déjà.")
    else:
        print(f"❌ Erreur : {e}")
finally:
    db.close()
