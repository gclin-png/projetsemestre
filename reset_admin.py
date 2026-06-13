"""
Crée un compte admin ou élève un compte existant en admin.
Lance depuis le dossier projet : python reset_admin.py
"""
import sqlite3, hashlib, secrets, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tutolab.db')

EMAIL    = 'guillaumec27@yahoo.com'   # ← change si besoin
NOM      = 'Guillaume Clin'           # ← change si besoin
MOT_DE_PASSE = 'admin1234'            # ← change après connexion !

def hacher(mdp, sel):
    return hashlib.pbkdf2_hmac('sha256', mdp.encode(), sel.encode(), 260_000).hex()

db = sqlite3.connect(DB_PATH)

# Vérifie si le compte existe déjà
existing = db.execute("SELECT id FROM utilisateurs WHERE email = ?", (EMAIL,)).fetchone()

if existing:
    db.execute("UPDATE utilisateurs SET role = 'admin' WHERE email = ?", (EMAIL,))
    db.commit()
    print(f"✅ Compte {EMAIL} passé en admin.")
else:
    sel  = secrets.token_hex(16)
    hash = hacher(MOT_DE_PASSE, sel)
    db.execute(
        "INSERT INTO utilisateurs (nom, email, mot_de_passe, sel, role) VALUES (?,?,?,?,?)",
        (NOM, EMAIL, hash, sel, 'admin')
    )
    db.commit()
    print(f"✅ Compte admin créé : {EMAIL} / {MOT_DE_PASSE}")
    print("⚠️  Change le mot de passe après ta première connexion !")

db.close()
