"""
TutoMotion — Serveur Flask
"""

import hashlib
import secrets
import os
import random
from datetime import datetime, timedelta
from flask import Flask, request, session, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from database import get_db, init_db

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
UPLOAD_DIR = os.path.join(STATIC_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app = Flask(__name__, static_folder=None)
app.secret_key = secrets.token_hex(32)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 Mo max

# ── Helpers ───────────────────────────────────────────────────────────────────

def hacher_mdp(mot_de_passe: str, sel: str) -> str:
    return hashlib.pbkdf2_hmac(
        'sha256', mot_de_passe.encode('utf-8'),
        sel.encode('utf-8'), iterations=260_000
    ).hex()

def verifier_mdp(mot_de_passe: str, sel: str, hash_stocke: str) -> bool:
    return secrets.compare_digest(hacher_mdp(mot_de_passe, sel), hash_stocke)

def utilisateur_connecte():
    return session.get('utilisateur_id') is not None

def est_admin():
    if not utilisateur_connecte():
        return False
    db = get_db()
    u  = db.execute('SELECT role FROM utilisateurs WHERE id = ?', (session['utilisateur_id'],)).fetchone()
    db.close()
    return u and u['role'] == 'admin'

def est_contributeur_ou_admin():
    if not utilisateur_connecte():
        return False
    db = get_db()
    u  = db.execute('SELECT role FROM utilisateurs WHERE id = ?', (session['utilisateur_id'],)).fetchone()
    db.close()
    return u and u['role'] in ('admin', 'contributeur')

def _get_current_user_id():
    return session.get('utilisateur_id')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ── Frontend ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'landingpage.html')

@app.route('/cours')
def page_cours():
    return send_from_directory(STATIC_DIR, 'cours.html')

@app.route('/admin')
def page_admin():
    return send_from_directory(STATIC_DIR, 'admin.html')

@app.route('/creer-cours')
def page_creer_cours():
    return send_from_directory(STATIC_DIR, 'creer-cours.html')

@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

# ── API Auth ──────────────────────────────────────────────────────────────────

@app.route('/api/inscription', methods=['POST'])
def inscription():
    data         = request.get_json()
    nom          = (data.get('nom')          or '').strip()
    email        = (data.get('email')        or '').strip().lower()
    telephone    = (data.get('telephone')    or '').strip()
    mot_de_passe = data.get('mot_de_passe', '')

    if not nom or not email or not mot_de_passe:
        return jsonify({'succes': False, 'message': 'Nom, email et mot de passe sont requis.'}), 400
    if len(mot_de_passe) < 8:
        return jsonify({'succes': False, 'message': 'Le mot de passe doit contenir au moins 8 caractères.'}), 400
    if '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'succes': False, 'message': 'Adresse email invalide.'}), 400

    sel  = secrets.token_hex(16)
    hash = hacher_mdp(mot_de_passe, sel)

    try:
        db = get_db()
        db.execute(
            "INSERT INTO utilisateurs (nom, email, telephone, mot_de_passe, sel) VALUES (?,?,?,?,?)",
            (nom, email, telephone or None, hash, sel)
        )
        db.commit()
        utilisateur = db.execute(
            "SELECT id, nom, email, telephone, role, cree_le FROM utilisateurs WHERE email = ?",
            (email,)
        ).fetchone()
        db.close()
    except Exception as e:
        if 'UNIQUE constraint failed' in str(e):
            return jsonify({'succes': False, 'message': 'Cette adresse email est déjà utilisée.'}), 409
        return jsonify({'succes': False, 'message': 'Erreur serveur.'}), 500

    session['utilisateur_id'] = utilisateur['id']
    session['nom']             = utilisateur['nom']
    session['email']           = utilisateur['email']

    return jsonify({
        'succes': True,
        'message': f'Bienvenue, {utilisateur["nom"]} !',
        'utilisateur': {
            'id': utilisateur['id'], 'nom': utilisateur['nom'],
            'email': utilisateur['email'], 'telephone': utilisateur['telephone'],
            'role': utilisateur['role'], 'cree_le': utilisateur['cree_le'],
            'avatar_url': utilisateur['avatar_url'] or '',
        }
    }), 201


@app.route('/api/connexion', methods=['POST'])
def connexion():
    data         = request.get_json()
    email        = (data.get('email') or '').strip().lower()
    mot_de_passe = data.get('mot_de_passe', '')

    if not email or not mot_de_passe:
        return jsonify({'succes': False, 'message': 'Email et mot de passe requis.'}), 400

    db          = get_db()
    utilisateur = db.execute("SELECT * FROM utilisateurs WHERE email = ?", (email,)).fetchone()
    db.close()

    if not utilisateur or not verifier_mdp(mot_de_passe, utilisateur['sel'], utilisateur['mot_de_passe']):
        return jsonify({'succes': False, 'message': 'Email ou mot de passe incorrect.'}), 401

    session['utilisateur_id'] = utilisateur['id']
    session['nom']             = utilisateur['nom']
    session['email']           = utilisateur['email']

    return jsonify({
        'succes': True,
        'message': f'Bon retour, {utilisateur["nom"]} !',
        'utilisateur': {
            'id': utilisateur['id'], 'nom': utilisateur['nom'],
            'email': utilisateur['email'], 'telephone': utilisateur['telephone'],
            'role': utilisateur['role'], 'cree_le': utilisateur['cree_le'],
            'avatar_url': utilisateur['avatar_url'] or '',
        }
    })


@app.route('/api/deconnexion', methods=['POST'])
def deconnexion():
    uid = session.get('utilisateur_id')
    if uid:
        db = get_db()
        db.execute("DELETE FROM sessions_actives WHERE utilisateur_id = ?", (uid,))
        db.commit()
        db.close()
    session.clear()
    return jsonify({'succes': True, 'message': 'Déconnexion réussie.'})


@app.route('/api/desinscription', methods=['DELETE'])
def desinscription():
    if not utilisateur_connecte():
        return jsonify({'succes': False, 'message': 'Non connecté.'}), 401
    user_id = session['utilisateur_id']
    db = get_db()
    db.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
    db.commit()
    db.close()
    session.clear()
    return jsonify({'succes': True, 'message': 'Compte supprimé définitivement.'})


@app.route('/api/moi', methods=['GET'])
def moi():
    if not utilisateur_connecte():
        return jsonify({'connecte': False}), 200

    db          = get_db()
    utilisateur = db.execute(
        "SELECT id, nom, email, telephone, role, avatar_url, cree_le FROM utilisateurs WHERE id = ?",
        (session['utilisateur_id'],)
    ).fetchone()
    historique  = db.execute(
        """
        SELECT t.id, t.titre, t.categorie, t.duree_min, t.emoji, t.theme_class,
               h.statut, h.commence_le, h.termine_le
        FROM   historique h
        JOIN   tutoriels  t ON t.id = h.tutoriel_id
        WHERE  h.utilisateur_id = ?
        ORDER  BY h.commence_le DESC
        """,
        (session['utilisateur_id'],)
    ).fetchall()
    db.close()

    if not utilisateur:
        session.clear()
        return jsonify({'connecte': False}), 200

    return jsonify({
        'connecte': True,
        'utilisateur': {
            'id': utilisateur['id'], 'nom': utilisateur['nom'],
            'email': utilisateur['email'], 'telephone': utilisateur['telephone'],
            'role': utilisateur['role'], 'cree_le': utilisateur['cree_le'],
            'avatar_url': utilisateur['avatar_url'] or '',
        },
        'historique': [dict(h) for h in historique]
    })


@app.route('/api/profil', methods=['PUT'])
def modifier_profil():
    if not utilisateur_connecte():
        return jsonify({'succes': False, 'message': 'Non connecté.'}), 401
    data      = request.get_json()
    nom       = (data.get('nom')       or '').strip()
    telephone = (data.get('telephone') or '').strip()
    if not nom:
        return jsonify({'succes': False, 'message': 'Le nom est requis.'}), 400
    db = get_db()
    db.execute("UPDATE utilisateurs SET nom=?, telephone=? WHERE id=?",
               (nom, telephone or None, session['utilisateur_id']))
    db.commit()
    utilisateur = db.execute(
        "SELECT id, nom, email, telephone, role, avatar_url, cree_le FROM utilisateurs WHERE id=?",
        (session['utilisateur_id'],)
    ).fetchone()
    db.close()
    session['nom'] = nom
    return jsonify({'succes': True, 'message': 'Profil mis à jour.', 'utilisateur': dict(utilisateur)})


@app.route('/api/profil/avatar', methods=['POST'])
def modifier_avatar():
    if not utilisateur_connecte():
        return jsonify({'succes': False, 'message': 'Non connecté.'}), 401
    fichier = request.files.get('avatar')
    if not fichier or not allowed_file(fichier.filename):
        return jsonify({'succes': False, 'message': 'Fichier invalide. Formats acceptés : png, jpg, jpeg, gif, webp.'}), 400
    fname     = secrets.token_hex(8) + '_' + secure_filename(fichier.filename)
    fichier.save(os.path.join(UPLOAD_DIR, fname))
    avatar_url = '/uploads/' + fname
    db = get_db()
    db.execute("UPDATE utilisateurs SET avatar_url = ? WHERE id = ?",
               (avatar_url, session['utilisateur_id']))
    db.commit()
    db.close()
    return jsonify({'succes': True, 'avatar_url': avatar_url})


@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    if not utilisateur_connecte():
        return jsonify({'succes': False}), 401
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO sessions_actives (utilisateur_id, derniere_activite) VALUES (?, ?)",
        (session['utilisateur_id'], datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    )
    db.commit()
    db.close()
    return jsonify({'succes': True})


# ── API Tutoriels (publique) ──────────────────────────────────────────────────

@app.route('/api/tutoriels', methods=['GET'])
def get_tutoriels():
    db    = get_db()
    tutos = db.execute("SELECT * FROM tutoriels ORDER BY cree_le DESC").fetchall()
    db.close()
    return jsonify({'succes': True, 'tutoriels': [dict(t) for t in tutos]})


@app.route('/api/tutoriels/<int:tid>', methods=['GET'])
def get_tutoriel(tid):
    db   = get_db()
    tuto = db.execute("SELECT * FROM tutoriels WHERE id = ?", (tid,)).fetchone()
    if not tuto:
        db.close()
        return jsonify({'succes': False, 'message': 'Tutoriel introuvable.'}), 404
    images = db.execute(
        "SELECT id, url, position, est_couverture FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position",
        (tid,)
    ).fetchall()
    db.close()
    data = dict(tuto)
    data['images'] = [dict(img) for img in images]
    # Masquer le contenu complet si non connecté
    if not utilisateur_connecte():
        data['contenu'] = None
    return jsonify({'succes': True, 'tutoriel': data, 'connecte': utilisateur_connecte()})


@app.route('/api/historique', methods=['POST'])
def ajouter_historique():
    if not utilisateur_connecte():
        return jsonify({'succes': False, 'message': 'Non connecté.'}), 401
    data        = request.get_json()
    tutoriel_id = data.get('tutoriel_id')
    statut      = data.get('statut', 'en_cours')
    if not tutoriel_id:
        return jsonify({'succes': False, 'message': 'tutoriel_id requis.'}), 400
    db = get_db()
    try:
        db.execute(
            "INSERT OR IGNORE INTO historique (utilisateur_id, tutoriel_id, statut) VALUES (?,?,?)",
            (session['utilisateur_id'], tutoriel_id, statut)
        )
        if statut == 'termine':
            db.execute(
                "UPDATE historique SET statut='termine', termine_le=? WHERE utilisateur_id=? AND tutoriel_id=?",
                (datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), session['utilisateur_id'], tutoriel_id)
            )
        db.commit()
    finally:
        db.close()
    return jsonify({'succes': True})


# ── API Admin ─────────────────────────────────────────────────────────────────

@app.route('/api/admin/membres', methods=['GET'])
def admin_membres():
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    seuil   = (datetime.utcnow() - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')
    db      = get_db()
    membres = db.execute(
        """
        SELECT u.id, u.nom, u.email, u.role, u.avatar_url, u.cree_le,
               CASE WHEN s.derniere_activite >= ? THEN 1 ELSE 0 END AS en_ligne,
               (SELECT COUNT(*) FROM historique h WHERE h.utilisateur_id = u.id AND h.statut = 'termine') AS cours_completes
        FROM   utilisateurs u
        LEFT JOIN sessions_actives s ON s.utilisateur_id = u.id
        ORDER  BY u.cree_le DESC
        """,
        (seuil,)
    ).fetchall()
    db.close()
    return jsonify({'succes': True, 'membres': [dict(m) for m in membres]})


@app.route('/api/admin/membres/<int:uid>', methods=['GET'])
def admin_profil_membre(uid):
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    seuil  = (datetime.utcnow() - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')
    db     = get_db()
    membre = db.execute(
        """
        SELECT u.id, u.nom, u.email, u.role, u.avatar_url, u.cree_le,
               CASE WHEN s.derniere_activite >= ? THEN 1 ELSE 0 END AS en_ligne,
               (SELECT COUNT(*) FROM historique h WHERE h.utilisateur_id = u.id AND h.statut = 'termine') AS cours_completes
        FROM   utilisateurs u
        LEFT JOIN sessions_actives s ON s.utilisateur_id = u.id
        WHERE  u.id = ?
        """,
        (seuil, uid)
    ).fetchone()
    db.close()
    if not membre:
        return jsonify({'succes': False, 'message': 'Membre introuvable.'}), 404
    return jsonify({'succes': True, 'membre': dict(membre)})


@app.route('/api/admin/membres/<int:uid>', methods=['DELETE'])
def admin_supprimer_membre(uid):
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    if uid == session['utilisateur_id']:
        return jsonify({'succes': False, 'message': 'Vous ne pouvez pas supprimer votre propre compte.'}), 400
    db = get_db()
    db.execute("DELETE FROM utilisateurs WHERE id = ?", (uid,))
    db.commit()
    db.close()
    return jsonify({'succes': True, 'message': 'Compte supprimé.'})


@app.route('/api/admin/utilisateurs/<int:uid>/role', methods=['PUT'])
def admin_changer_role(uid):
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    data    = request.get_json()
    nouveau = data.get('role', 'apprenant')
    if nouveau not in ('admin', 'apprenant', 'contributeur'):
        return jsonify({'succes': False, 'message': 'Rôle invalide.'}), 400
    if uid == session['utilisateur_id'] and nouveau != 'admin':
        return jsonify({'succes': False, 'message': 'Vous ne pouvez pas vous retirer le rôle admin.'}), 400
    db = get_db()
    db.execute('UPDATE utilisateurs SET role = ? WHERE id = ?', (nouveau, uid))
    db.commit()
    db.close()
    return jsonify({'succes': True, 'message': f'Rôle mis à jour : {nouveau}.'})


@app.route('/api/admin/tutoriels', methods=['POST'])
def admin_creer_tutoriel():
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403

    titre     = (request.form.get('titre')     or '').strip()
    categorie = (request.form.get('categorie') or '').strip()
    auteur    = (request.form.get('auteur')    or '').strip()
    duree_min = int(request.form.get('duree_min', 5) or 5)
    emoji     = (request.form.get('emoji', '🎬') or '🎬').strip()
    contenu   = (request.form.get('contenu', '') or '').strip()
    accroche  = (request.form.get('accroche', '') or '').strip()

    if not titre or not categorie or not auteur:
        return jsonify({'succes': False, 'message': 'Titre, catégorie et auteur sont requis.'}), 400

    theme_class = random.choice(['motion1','motion2','motion3','motion4','motion5'])
    db  = get_db()
    cur = db.execute(
        'INSERT INTO tutoriels (titre, categorie, auteur, duree_min, emoji, theme_class, contenu, image_url, accroche) VALUES (?,?,?,?,?,?,?,?,?)',
        (titre, categorie, auteur, duree_min, emoji, theme_class, contenu, '', accroche)
    )
    tid = cur.lastrowid

    fichiers  = request.files.getlist('images[]')
    cover_url = ''
    for i, fichier in enumerate(fichiers):
        if fichier and allowed_file(fichier.filename):
            fname = secrets.token_hex(8) + '_' + secure_filename(fichier.filename)
            fichier.save(os.path.join(UPLOAD_DIR, fname))
            url = '/uploads/' + fname
            est_couv = 1 if i == 0 else 0
            if est_couv: cover_url = url
            db.execute('INSERT INTO tutoriel_images (tutoriel_id, url, position, est_couverture) VALUES (?,?,?,?)',
                       (tid, url, i, est_couv))
    if cover_url:
        db.execute('UPDATE tutoriels SET image_url = ? WHERE id = ?', (cover_url, tid))

    db.commit()
    tuto   = db.execute('SELECT * FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    images = db.execute('SELECT id, url, position, est_couverture FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position', (tid,)).fetchall()
    db.close()
    data = dict(tuto); data['images'] = [dict(img) for img in images]
    return jsonify({'succes': True, 'message': 'Tutoriel créé.', 'tutoriel': data}), 201


@app.route('/api/admin/tutoriels/<int:tid>', methods=['PUT'])
def admin_modifier_tutoriel(tid):
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403

    titre     = (request.form.get('titre')     or '').strip()
    categorie = (request.form.get('categorie') or '').strip()
    auteur    = (request.form.get('auteur')    or '').strip()
    duree_min = int(request.form.get('duree_min', 5) or 5)
    emoji     = (request.form.get('emoji', '🎬') or '🎬').strip()
    contenu   = (request.form.get('contenu', '') or '').strip()
    accroche  = (request.form.get('accroche', '') or '').strip()

    if not titre or not categorie or not auteur:
        return jsonify({'succes': False, 'message': 'Titre, catégorie et auteur sont requis.'}), 400

    db = get_db()
    db.execute('UPDATE tutoriels SET titre=?, categorie=?, auteur=?, duree_min=?, emoji=?, contenu=?, accroche=? WHERE id=?',
               (titre, categorie, auteur, duree_min, emoji, contenu, accroche, tid))

    fichiers = request.files.getlist('images[]')
    if fichiers and any(f.filename for f in fichiers):
        pos_max = db.execute('SELECT COALESCE(MAX(position)+1, 0) FROM tutoriel_images WHERE tutoriel_id = ?', (tid,)).fetchone()[0]
        for i, fichier in enumerate(fichiers):
            if fichier and allowed_file(fichier.filename):
                fname = secrets.token_hex(8) + '_' + secure_filename(fichier.filename)
                fichier.save(os.path.join(UPLOAD_DIR, fname))
                db.execute('INSERT INTO tutoriel_images (tutoriel_id, url, position, est_couverture) VALUES (?,?,?,?)',
                           (tid, '/uploads/' + fname, pos_max + i, 0))

    cover = db.execute('SELECT url FROM tutoriel_images WHERE tutoriel_id = ? AND est_couverture = 1', (tid,)).fetchone()
    if not cover:
        cover = db.execute('SELECT url FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position LIMIT 1', (tid,)).fetchone()
    if cover:
        db.execute('UPDATE tutoriels SET image_url = ? WHERE id = ?', (cover['url'], tid))

    db.commit()
    tuto   = db.execute('SELECT * FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    images = db.execute('SELECT id, url, position, est_couverture FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position', (tid,)).fetchall()
    db.close()
    if not tuto:
        return jsonify({'succes': False, 'message': 'Tutoriel introuvable.'}), 404
    data = dict(tuto); data['images'] = [dict(img) for img in images]
    return jsonify({'succes': True, 'message': 'Tutoriel mis à jour.', 'tutoriel': data})


@app.route('/api/admin/tutoriels/<int:tid>', methods=['DELETE'])
def admin_supprimer_tutoriel(tid):
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    db = get_db()
    db.execute('DELETE FROM tutoriels WHERE id = ?', (tid,))
    db.commit()
    db.close()
    return jsonify({'succes': True, 'message': 'Tutoriel supprimé.'})


# ── API Upload image inline ───────────────────────────────────────────────────

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    if not est_contributeur_ou_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    fichier = request.files.get('image')
    if not fichier or not allowed_file(fichier.filename):
        return jsonify({'succes': False, 'message': 'Fichier invalide.'}), 400
    fname = secrets.token_hex(8) + '_' + secure_filename(fichier.filename)
    fichier.save(os.path.join(UPLOAD_DIR, fname))
    return jsonify({'succes': True, 'url': '/uploads/' + fname})


# ── API Contributeur ──────────────────────────────────────────────────────────

@app.route('/api/contributeur/tutoriels', methods=['POST'])
def contributeur_creer_tutoriel():
    if not est_contributeur_ou_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403

    titre     = (request.form.get('titre')     or '').strip()
    categorie = (request.form.get('categorie') or '').strip()
    auteur    = (request.form.get('auteur')    or '').strip()
    duree_min = int(request.form.get('duree_min', 5) or 5)
    emoji     = (request.form.get('emoji', '🎬') or '🎬').strip()
    contenu   = (request.form.get('contenu', '') or '').strip()
    accroche  = (request.form.get('accroche', '') or '').strip()

    if not titre or not categorie or not auteur:
        return jsonify({'succes': False, 'message': 'Titre, catégorie et auteur sont requis.'}), 400

    theme_class = random.choice(['motion1','motion2','motion3','motion4','motion5'])
    createur_id = _get_current_user_id()
    db  = get_db()
    cur = db.execute(
        'INSERT INTO tutoriels (titre, categorie, auteur, duree_min, emoji, theme_class, contenu, image_url, createur_id, accroche) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (titre, categorie, auteur, duree_min, emoji, theme_class, contenu, '', createur_id, accroche)
    )
    tid = cur.lastrowid

    fichiers  = request.files.getlist('images[]')
    cover_url = ''
    for i, fichier in enumerate(fichiers):
        if fichier and allowed_file(fichier.filename):
            fname = secrets.token_hex(8) + '_' + secure_filename(fichier.filename)
            fichier.save(os.path.join(UPLOAD_DIR, fname))
            url = '/uploads/' + fname
            est_couv = 1 if i == 0 else 0
            if est_couv: cover_url = url
            db.execute('INSERT INTO tutoriel_images (tutoriel_id, url, position, est_couverture) VALUES (?,?,?,?)',
                       (tid, url, i, est_couv))
    if cover_url:
        db.execute('UPDATE tutoriels SET image_url = ? WHERE id = ?', (cover_url, tid))

    db.commit()
    tuto   = db.execute('SELECT * FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    images = db.execute('SELECT id, url, position, est_couverture FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position', (tid,)).fetchall()
    db.close()
    data = dict(tuto); data['images'] = [dict(img) for img in images]
    return jsonify({'succes': True, 'message': 'Tutoriel créé.', 'tutoriel': data}), 201


@app.route('/api/contributeur/tutoriels/<int:tid>', methods=['PUT'])
def contributeur_modifier_tutoriel(tid):
    if not est_contributeur_ou_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403

    uid = _get_current_user_id()
    db  = get_db()
    tuto_check = db.execute('SELECT createur_id FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    if not tuto_check:
        db.close()
        return jsonify({'succes': False, 'message': 'Tutoriel introuvable.'}), 404
    user = db.execute('SELECT role FROM utilisateurs WHERE id = ?', (uid,)).fetchone()
    if user['role'] == 'contributeur' and tuto_check['createur_id'] != uid:
        db.close()
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403

    titre     = (request.form.get('titre')     or '').strip()
    categorie = (request.form.get('categorie') or '').strip()
    auteur    = (request.form.get('auteur')    or '').strip()
    duree_min = int(request.form.get('duree_min', 5) or 5)
    emoji     = (request.form.get('emoji', '🎬') or '🎬').strip()
    contenu   = (request.form.get('contenu', '') or '').strip()
    accroche  = (request.form.get('accroche', '') or '').strip()

    if not titre or not categorie or not auteur:
        db.close()
        return jsonify({'succes': False, 'message': 'Titre, catégorie et auteur sont requis.'}), 400

    db.execute('UPDATE tutoriels SET titre=?, categorie=?, auteur=?, duree_min=?, emoji=?, contenu=?, accroche=? WHERE id=?',
               (titre, categorie, auteur, duree_min, emoji, contenu, accroche, tid))

    fichiers = request.files.getlist('images[]')
    if fichiers and any(f.filename for f in fichiers):
        pos_max = db.execute('SELECT COALESCE(MAX(position)+1, 0) FROM tutoriel_images WHERE tutoriel_id = ?', (tid,)).fetchone()[0]
        for i, fichier in enumerate(fichiers):
            if fichier and allowed_file(fichier.filename):
                fname = secrets.token_hex(8) + '_' + secure_filename(fichier.filename)
                fichier.save(os.path.join(UPLOAD_DIR, fname))
                db.execute('INSERT INTO tutoriel_images (tutoriel_id, url, position, est_couverture) VALUES (?,?,?,?)',
                           (tid, '/uploads/' + fname, pos_max + i, 0))

    cover = db.execute('SELECT url FROM tutoriel_images WHERE tutoriel_id = ? AND est_couverture = 1', (tid,)).fetchone()
    if not cover:
        cover = db.execute('SELECT url FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position LIMIT 1', (tid,)).fetchone()
    if cover:
        db.execute('UPDATE tutoriels SET image_url = ? WHERE id = ?', (cover['url'], tid))

    db.commit()
    tuto   = db.execute('SELECT * FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    images = db.execute('SELECT id, url, position, est_couverture FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position', (tid,)).fetchall()
    db.close()
    data = dict(tuto); data['images'] = [dict(img) for img in images]
    return jsonify({'succes': True, 'message': 'Tutoriel mis à jour.', 'tutoriel': data})


@app.route('/api/contributeur/tutoriels/<int:tid>/images/<int:img_id>', methods=['DELETE'])
def contributeur_supprimer_image(tid, img_id):
    if not est_contributeur_ou_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    uid  = _get_current_user_id()
    db   = get_db()
    tuto = db.execute('SELECT createur_id FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    if not tuto:
        db.close()
        return jsonify({'succes': False, 'message': 'Tutoriel introuvable.'}), 404
    user = db.execute('SELECT role FROM utilisateurs WHERE id = ?', (uid,)).fetchone()
    if user['role'] == 'contributeur' and tuto['createur_id'] != uid:
        db.close()
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    img = db.execute('SELECT url, est_couverture FROM tutoriel_images WHERE id = ? AND tutoriel_id = ?', (img_id, tid)).fetchone()
    if not img:
        db.close()
        return jsonify({'succes': False, 'message': 'Image introuvable.'}), 404
    db.execute('DELETE FROM tutoriel_images WHERE id = ?', (img_id,))
    if img['est_couverture']:
        nxt = db.execute('SELECT id, url FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position LIMIT 1', (tid,)).fetchone()
        if nxt:
            db.execute('UPDATE tutoriel_images SET est_couverture = 1 WHERE id = ?', (nxt['id'],))
            db.execute('UPDATE tutoriels SET image_url = ? WHERE id = ?', (nxt['url'], tid))
        else:
            db.execute("UPDATE tutoriels SET image_url = '' WHERE id = ?", (tid,))
    db.commit()
    images = db.execute('SELECT id, url, position, est_couverture FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position', (tid,)).fetchall()
    db.close()
    return jsonify({'succes': True, 'message': 'Image supprimée.', 'images': [dict(i) for i in images]})


@app.route('/api/contributeur/tutoriels/<int:tid>/images/couverture', methods=['PUT'])
def contributeur_changer_couverture(tid):
    if not est_contributeur_ou_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    uid    = _get_current_user_id()
    data   = request.get_json()
    img_id = data.get('image_id')
    db     = get_db()
    tuto   = db.execute('SELECT createur_id FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    user   = db.execute('SELECT role FROM utilisateurs WHERE id = ?', (uid,)).fetchone()
    if not tuto or (user['role'] == 'contributeur' and tuto['createur_id'] != uid):
        db.close()
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    img = db.execute('SELECT url FROM tutoriel_images WHERE id = ? AND tutoriel_id = ?', (img_id, tid)).fetchone()
    if not img:
        db.close()
        return jsonify({'succes': False, 'message': 'Image introuvable.'}), 404
    db.execute('UPDATE tutoriel_images SET est_couverture = 0 WHERE tutoriel_id = ?', (tid,))
    db.execute('UPDATE tutoriel_images SET est_couverture = 1 WHERE id = ?', (img_id,))
    db.execute('UPDATE tutoriels SET image_url = ? WHERE id = ?', (img['url'], tid))
    db.commit()
    images = db.execute('SELECT id, url, position, est_couverture FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position', (tid,)).fetchall()
    db.close()
    return jsonify({'succes': True, 'images': [dict(i) for i in images]})


@app.route('/api/contributeur/tutoriels/<int:tid>/images/ordre', methods=['PUT'])
def contributeur_reordonner_images(tid):
    if not est_contributeur_ou_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    uid   = _get_current_user_id()
    data  = request.get_json()
    ordre = data.get('ordre', [])
    db    = get_db()
    tuto  = db.execute('SELECT createur_id FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    user  = db.execute('SELECT role FROM utilisateurs WHERE id = ?', (uid,)).fetchone()
    if not tuto or (user['role'] == 'contributeur' and tuto['createur_id'] != uid):
        db.close()
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    for pos, img_id in enumerate(ordre):
        db.execute('UPDATE tutoriel_images SET position = ? WHERE id = ? AND tutoriel_id = ?', (pos, img_id, tid))
    db.commit()
    images = db.execute('SELECT id, url, position, est_couverture FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position', (tid,)).fetchall()
    db.close()
    return jsonify({'succes': True, 'images': [dict(i) for i in images]})


@app.route('/api/contributeur/tutoriels/<int:tid>', methods=['DELETE'])
def contributeur_supprimer_tutoriel(tid):
    if not est_contributeur_ou_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    uid  = _get_current_user_id()
    db   = get_db()
    tuto = db.execute('SELECT createur_id FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    if not tuto:
        db.close()
        return jsonify({'succes': False, 'message': 'Tutoriel introuvable.'}), 404
    user = db.execute('SELECT role FROM utilisateurs WHERE id = ?', (uid,)).fetchone()
    if user['role'] == 'contributeur' and tuto['createur_id'] != uid:
        db.close()
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    db.execute('DELETE FROM tutoriels WHERE id = ?', (tid,))
    db.commit()
    db.close()
    return jsonify({'succes': True, 'message': 'Tutoriel supprimé.'})


@app.route('/api/contributeur/mes-tutoriels', methods=['GET'])
def contributeur_mes_tutoriels():
    if not est_contributeur_ou_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    uid    = _get_current_user_id()
    db     = get_db()
    tutos  = db.execute("SELECT * FROM tutoriels WHERE createur_id = ? ORDER BY cree_le DESC", (uid,)).fetchall()
    result = []
    for t in tutos:
        d = dict(t)
        images = db.execute(
            'SELECT id, url, position, est_couverture FROM tutoriel_images WHERE tutoriel_id = ? ORDER BY position',
            (t['id'],)
        ).fetchall()
        d['images'] = [dict(img) for img in images]
        result.append(d)
    db.close()
    return jsonify({'succes': True, 'tutoriels': result})


# ── API Contact ───────────────────────────────────────────────────────────────

@app.route('/api/contact', methods=['POST'])
def envoyer_message():
    nom     = (request.form.get('nom')     or '').strip()
    email   = (request.form.get('email')   or '').strip().lower()
    sujet   = (request.form.get('sujet')   or '').strip()
    message = (request.form.get('message') or '').strip()

    if not nom or not email or not sujet or not message:
        return jsonify({'succes': False, 'message': 'Tous les champs sont requis.'}), 400
    if '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'succes': False, 'message': 'Adresse email invalide.'}), 400

    image_url = ''
    fichier   = request.files.get('image')
    if fichier and allowed_file(fichier.filename):
        fname     = secrets.token_hex(8) + '_' + secure_filename(fichier.filename)
        fichier.save(os.path.join(UPLOAD_DIR, fname))
        image_url = '/uploads/' + fname

    db = get_db()
    db.execute(
        "INSERT INTO messages_contact (nom, email, sujet, message, image_url) VALUES (?,?,?,?,?)",
        (nom, email, sujet, message, image_url)
    )
    db.commit()
    db.close()
    return jsonify({'succes': True, 'message': 'Message envoyé ! Nous vous répondrons sous 48h.'})


@app.route('/api/admin/messages', methods=['GET'])
def admin_messages():
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    db       = get_db()
    messages = db.execute(
        "SELECT * FROM messages_contact ORDER BY envoye_le DESC"
    ).fetchall()
    db.close()
    return jsonify({'succes': True, 'messages': [dict(m) for m in messages]})


@app.route('/api/admin/messages/<int:mid>/lu', methods=['PUT'])
def admin_marquer_lu(mid):
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    db = get_db()
    db.execute("UPDATE messages_contact SET lu = 1 WHERE id = ?", (mid,))
    db.commit()
    db.close()
    return jsonify({'succes': True})


@app.route('/api/admin/messages/<int:mid>', methods=['DELETE'])
def admin_supprimer_message(mid):
    if not est_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403
    db = get_db()
    db.execute("DELETE FROM messages_contact WHERE id = ?", (mid,))
    db.commit()
    db.close()
    return jsonify({'succes': True, 'message': 'Message supprimé.'})


# ── API Questionnaires ────────────────────────────────────────────────────────

@app.route('/api/tutoriels/<int:tid>/questionnaire', methods=['GET'])
def get_questionnaire(tid):
    db = get_db()
    questions = db.execute(
        "SELECT id, question, type, options, reponses_correctes, multiple, ordre FROM questionnaires WHERE tutoriel_id = ? ORDER BY ordre",
        (tid,)
    ).fetchall()
    # Exposer reponses_correctes uniquement aux admins/contributeurs (pour l'éditeur)
    peut_voir_reponses = est_contributeur_ou_admin()
    result = []
    for q in questions:
        d = dict(q)
        if not peut_voir_reponses:
            d.pop('reponses_correctes', None)
        result.append(d)
    db.close()
    return jsonify({'succes': True, 'questions': result})


@app.route('/api/tutoriels/<int:tid>/questionnaire', methods=['PUT'])
def sauvegarder_questionnaire(tid):
    if not est_contributeur_ou_admin():
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403

    uid = _get_current_user_id()
    db  = get_db()
    tuto = db.execute('SELECT createur_id FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    if not tuto:
        db.close()
        return jsonify({'succes': False, 'message': 'Tutoriel introuvable.'}), 404
    user = db.execute('SELECT role FROM utilisateurs WHERE id = ?', (uid,)).fetchone()
    if user['role'] == 'contributeur' and tuto['createur_id'] != uid:
        db.close()
        return jsonify({'succes': False, 'message': 'Accès refusé.'}), 403

    data      = request.get_json()
    questions = data.get('questions', [])

    # Supprimer les anciennes questions et réinsérer
    db.execute("DELETE FROM questionnaires WHERE tutoriel_id = ?", (tid,))
    for i, q in enumerate(questions):
        question          = (q.get('question') or '').strip()
        options           = q.get('options', '')
        reponses_correctes = q.get('reponses_correctes', '')
        multiple          = 1 if q.get('multiple') else 0
        if not question:
            continue
        db.execute(
            "INSERT INTO questionnaires (tutoriel_id, question, type, options, reponses_correctes, multiple, ordre) VALUES (?,?,?,?,?,?,?)",
            (tid, question, 'qcm', options, reponses_correctes, multiple, i)
        )
    db.commit()
    questions_saved = db.execute(
        "SELECT id, question, type, options, reponses_correctes, multiple, ordre FROM questionnaires WHERE tutoriel_id = ? ORDER BY ordre",
        (tid,)
    ).fetchall()
    db.close()
    return jsonify({'succes': True, 'message': 'Questionnaire sauvegardé.', 'questions': [dict(q) for q in questions_saved]})


@app.route('/api/tutoriels/<int:tid>/soumettre', methods=['POST'])
def soumettre_questionnaire(tid):
    if not utilisateur_connecte():
        return jsonify({'succes': False, 'message': 'Connexion requise.'}), 401

    uid  = _get_current_user_id()
    data = request.get_json()
    reponses = data.get('reponses', [])  # [{question_id, reponse: "0" ou "0,2"}]

    db = get_db()
    tuto = db.execute('SELECT id FROM tutoriels WHERE id = ?', (tid,)).fetchone()
    if not tuto:
        db.close()
        return jsonify({'succes': False, 'message': 'Tutoriel introuvable.'}), 404

    questions = db.execute(
        "SELECT id, reponses_correctes, multiple FROM questionnaires WHERE tutoriel_id = ? ORDER BY ordre",
        (tid,)
    ).fetchall()

    if len(questions) == 0:
        db.close()
        return jsonify({'succes': False, 'message': 'Aucune question trouvée.'}), 400

    if len(reponses) < len(questions):
        db.close()
        return jsonify({'succes': False, 'message': 'Toutes les questions sont obligatoires.'}), 400

    # Calculer le score
    reponses_map = {str(r['question_id']): str(r['reponse']) for r in reponses}
    nb_correct = 0
    for q in questions:
        qid          = str(q['id'])
        rep_donnee   = set(v.strip() for v in reponses_map.get(qid, '').split(',') if v.strip())
        rep_correcte = set(v.strip() for v in (q['reponses_correctes'] or '').split(',') if v.strip())
        if rep_donnee and rep_correcte and rep_donnee == rep_correcte:
            nb_correct += 1

    score    = round((nb_correct / len(questions)) * 100)
    valide   = score >= 75

    # Supprimer les anciennes réponses
    db.execute(
        "DELETE FROM reponses_utilisateurs WHERE utilisateur_id = ? AND tutoriel_id = ?",
        (uid, tid)
    )
    # Sauvegarder les réponses
    for r in reponses:
        qid     = r.get('question_id')
        reponse = str(r.get('reponse', ''))
        if qid:
            db.execute(
                "INSERT INTO reponses_utilisateurs (utilisateur_id, tutoriel_id, question_id, reponse) VALUES (?,?,?,?)",
                (uid, tid, qid, reponse)
            )

    if valide:
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        db.execute(
            "INSERT OR IGNORE INTO historique (utilisateur_id, tutoriel_id, statut) VALUES (?,?,'termine')",
            (uid, tid)
        )
        db.execute(
            "UPDATE historique SET statut='termine', termine_le=? WHERE utilisateur_id=? AND tutoriel_id=?",
            (now, uid, tid)
        )
    else:
        # Marquer en_cours si pas encore dans l'historique
        db.execute(
            "INSERT OR IGNORE INTO historique (utilisateur_id, tutoriel_id, statut) VALUES (?,?,'en_cours')",
            (uid, tid)
        )

    db.commit()
    db.close()

    return jsonify({
        'succes':  True,
        'valide':  valide,
        'score':   score,
        'correct': nb_correct,
        'total':   len(questions),
        'message': f'Score : {score}% ({nb_correct}/{len(questions)}) — Cours validé ! 🎉' if valide
                   else f'Score : {score}% ({nb_correct}/{len(questions)}) — Il faut 75% pour valider. Réessayez !'
    })


@app.route('/api/tutoriels/<int:tid>/mes-reponses', methods=['GET'])
def mes_reponses(tid):
    if not utilisateur_connecte():
        return jsonify({'succes': False, 'message': 'Connexion requise.'}), 401
    uid = _get_current_user_id()
    db  = get_db()
    reponses = db.execute(
        "SELECT question_id, reponse FROM reponses_utilisateurs WHERE utilisateur_id = ? AND tutoriel_id = ?",
        (uid, tid)
    ).fetchall()
    db.close()
    return jsonify({'succes': True, 'reponses': [dict(r) for r in reponses]})


# ── Point d'entrée ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("\n🚀 TutoMotion démarré sur http://localhost:5000\n")
    app.run(debug=True, port=5000)