import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'tutomotion.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # ── Table utilisateurs ──────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nom           TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            telephone     TEXT,
            mot_de_passe  TEXT    NOT NULL,
            sel           TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'apprenant',
            avatar_url    TEXT    DEFAULT '',
            cree_le       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Table tutoriels ─────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tutoriels (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            titre       TEXT    NOT NULL,
            categorie   TEXT    NOT NULL,
            auteur      TEXT    NOT NULL,
            duree_min   INTEGER NOT NULL DEFAULT 5,
            emoji       TEXT    DEFAULT '🎬',
            theme_class TEXT    DEFAULT 'motion1',
            contenu     TEXT    DEFAULT '',
            image_url   TEXT    DEFAULT '',
            cree_le     DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration avatar_url
    try:
        cursor.execute("ALTER TABLE utilisateurs ADD COLUMN avatar_url TEXT DEFAULT ''")
    except Exception:
        pass

    # Migrations : ajouter les colonnes si elles n'existent pas encore
    for col, definition in [
        ('contenu',     "TEXT DEFAULT ''"),
        ('image_url',   "TEXT DEFAULT ''"),
        ('createur_id', "INTEGER REFERENCES utilisateurs(id) ON DELETE SET NULL"),
        ('accroche',    "TEXT DEFAULT ''"),
    ]:
        try:
            cursor.execute(f'ALTER TABLE tutoriels ADD COLUMN {col} {definition}')
        except Exception:
            pass

    # ── Table historique ─────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historique (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
            tutoriel_id     INTEGER NOT NULL REFERENCES tutoriels(id)    ON DELETE CASCADE,
            statut          TEXT NOT NULL DEFAULT 'en_cours',
            commence_le     DATETIME DEFAULT CURRENT_TIMESTAMP,
            termine_le      DATETIME,
            UNIQUE(utilisateur_id, tutoriel_id)
        )
    ''')

    # ── Table messages_contact ───────────────────────────────────────────────
    cursor.execute('''
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

    # ── Table questionnaires ─────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questionnaires (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            tutoriel_id         INTEGER NOT NULL REFERENCES tutoriels(id) ON DELETE CASCADE,
            question            TEXT    NOT NULL,
            type                TEXT    NOT NULL DEFAULT 'qcm',
            options             TEXT    DEFAULT '',
            reponses_correctes  TEXT    DEFAULT '',
            multiple            INTEGER NOT NULL DEFAULT 0,
            ordre               INTEGER NOT NULL DEFAULT 0,
            cree_le             DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Table reponses_utilisateurs ─────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reponses_utilisateurs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
            tutoriel_id     INTEGER NOT NULL REFERENCES tutoriels(id)    ON DELETE CASCADE,
            question_id     INTEGER NOT NULL REFERENCES questionnaires(id) ON DELETE CASCADE,
            reponse         TEXT    NOT NULL,
            soumis_le       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Table sessions_actives (heartbeat) ──────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions_actives (
            utilisateur_id    INTEGER PRIMARY KEY REFERENCES utilisateurs(id) ON DELETE CASCADE,
            derniere_activite DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Seed tutoriels de base ───────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM tutoriels")
    if cursor.fetchone()[0] == 0:
        tutoriels_seed = [
            ("Apprendre les bases d'After Effect",                        "Motion Design",      "Guillaume Clin", 5,  "🎬", "motion1"),
            ("Comment faire une introduction de vidéo en Motion Design",  "Motion Design",      "Guillaume Clin", 10, "✨", "motion2"),
            ("Comment faire des animations de textes avec After Effect",  "Motion Design",      "Guillaume Clin", 5,  "🔤", "motion3"),
            ("Comment intégrer du Motion Design dans vos montages vidéos","Motion Design,Montage Vidéo", "Guillaume Clin", 10, "🎞️", "motion4"),
            ("Comment utiliser une caméra 3D sur After Effect",           "Motion Design",      "Guillaume Clin", 15, "📷", "motion5"),
            ("Les bases du montage vidéo sur Premiere Pro",               "Montage Vidéo",      "Guillaume Clin", 12, "✂️", "motion1"),
            ("Créer un générique de film avec After Effect",              "Motion Design,Montage Vidéo", "Guillaume Clin", 20, "🎥", "motion2"),
            ("Introduction à CSS Grid",                                    "Design Graphique",  "Léa Martin",     10, "💻", "motion3"),
            ("Les bases de Flexbox",                                       "Design Graphique",  "Léa Martin",     8,  "📐", "motion4"),
            ("Les fondamentaux de Figma",                                  "Design UI/UX",       "Sofia Renard",   12, "🎨", "motion5"),
            ("Créer une maquette responsive sur Figma",                   "Design UI/UX",       "Sofia Renard",   20, "📱", "motion1"),
            ("Animer une interface avec After Effect",                     "Motion Design,Design UI/UX", "Sofia Renard", 15, "⚡", "motion2"),
        ]
        cursor.executemany(
            "INSERT INTO tutoriels (titre, categorie, auteur, duree_min, emoji, theme_class) VALUES (?,?,?,?,?,?)",
            tutoriels_seed
        )

    conn.commit()
    conn.close()
    print(f"✅ Base de données initialisée : {DB_PATH}")

if __name__ == '__main__':
    init_db()