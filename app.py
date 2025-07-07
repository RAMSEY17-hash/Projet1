
# ------------------- IMPORTS ET CONFIGURATION -------------------
import sqlite3
import logging
logging.basicConfig(level=logging.INFO)
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_a_modifier'  # À personnaliser !
DB_NAME = 'joueurs.db'

# ------------------- ROUTES ET FONCTIONS -------------------

# Suppression d'un joueur
@app.route('/supprimer/<int:joueur_id>', methods=['POST'])
def supprimer_joueur(joueur_id):
    if not session.get('admin_logged_in'):
        flash('Accès réservé. Veuillez vous connecter.')
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM joueurs WHERE id = ?', (joueur_id,))
    conn.commit()
    conn.close()
    flash('Joueur supprimé avec succès.')
    return redirect(url_for('liste'))

# Modification d'un joueur
@app.route('/modifier/<int:joueur_id>', methods=['GET', 'POST'])
def modifier_joueur(joueur_id):
    if not session.get('admin_logged_in'):
        flash('Accès réservé. Veuillez vous connecter.')
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        age = request.form['age']
        poste = request.form['poste']
        dossard = request.form['dossard']
        # Vérifier unicité du dossard (hors joueur courant)
        c.execute('SELECT COUNT(*) FROM joueurs WHERE dossard = ? AND id != ?', (dossard, joueur_id))
        if c.fetchone()[0] > 0:
            conn.close()
            flash('Ce numéro de dossard est déjà pris. Veuillez en choisir un autre.')
            return redirect(url_for('modifier_joueur', joueur_id=joueur_id))
        c.execute('UPDATE joueurs SET nom=?, prenom=?, age=?, poste=?, dossard=? WHERE id=?',
                  (nom, prenom, age, poste, dossard, joueur_id))
        conn.commit()
        conn.close()
        flash('Joueur modifié avec succès.')
        return redirect(url_for('liste'))
    else:
        c.execute('SELECT id, nom, prenom, age, poste, dossard FROM joueurs WHERE id=?', (joueur_id,))
        joueur = c.fetchone()
        conn.close()
        if joueur:
            joueur_dict = dict(id=joueur[0], nom=joueur[1], prenom=joueur[2], age=joueur[3], poste=joueur[4], dossard=joueur[5])
            return render_template('modifier.html', joueur=joueur_dict)
        else:
            flash('Joueur introuvable.')
            return redirect(url_for('liste'))

def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE joueurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                email TEXT NOT NULL,
                age INTEGER NOT NULL,
                poste TEXT NOT NULL,
                dossard INTEGER NOT NULL,
                photo TEXT,
                equipe TEXT
            )
        ''')
        conn.commit()
        conn.close()

@app.route('/')
def acceuil():
    return render_template('acceuil.html')

@app.route('/inscription', methods=['GET'])
def inscription():
    import random
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    question = f"Combien font {a} + {b} ?"
    from flask import session
    session['captcha_answer'] = str(a + b)
    return render_template('inscription.html', captcha_question=question)

@app.route('/submit', methods=['POST'])
def submit():
    from werkzeug.utils import secure_filename
    import os
    nom = request.form['nom']
    prenom = request.form['prenom']
    email = request.form['email']
    age = request.form['age']
    poste = request.form['poste']
    dossard = request.form['dossard']
    equipe = request.form.get('equipe')
    captcha = request.form.get('captcha')
    from flask import session, flash
    if captcha != session.get('captcha_answer'):
        flash('Captcha incorrect. Veuillez réessayer.')
        return redirect(url_for('inscription'))
    photo_file = request.files.get('photo')
    photo_filename = None
    if photo_file and photo_file.filename:
        photo_filename = secure_filename(photo_file.filename)
        photo_path = os.path.join('static/photos', photo_filename)
        photo_file.save(photo_path)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Vérifier unicité du dossard
    c.execute('SELECT COUNT(*) FROM joueurs WHERE dossard = ?', (dossard,))
    if c.fetchone()[0] > 0:
        conn.close()
        from flask import flash
        flash('Ce numéro de dossard est déjà pris. Veuillez en choisir un autre.')
        return redirect(url_for('inscription'))
    c.execute('INSERT INTO joueurs (nom, prenom, email, age, poste, dossard, photo, equipe) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
              (nom, prenom, email, age, poste, dossard, photo_filename, equipe))
    conn.commit()
    conn.close()
    # Envoi d'un email de confirmation (simulation)
    try:
        from flask import flash
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(f"Bonjour {prenom} {nom}, votre inscription a bien été prise en compte.")
        msg['Subject'] = 'Confirmation inscription football'
        msg['From'] = 'ton.email@gmail.com'
        msg['To'] = email
        # Décommente et configure pour un vrai envoi :
        # with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        #     server.login('ton.email@gmail.com', 'mot_de_passe')
        #     server.send_message(msg)
        print(f"[SIMULATION] Email envoyé à {email}")
    except Exception as e:
        print(f"Erreur envoi email: {e}")
    return render_template('felicitation.html', nom=nom, prenom=prenom)


# Nouvelle route pour la liste des joueurs (admin)
@app.route('/liste')
def liste():
    if not session.get('admin_logged_in'):
        flash('Accès réservé. Veuillez vous connecter.')
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Construction de la requête dynamique selon les filtres
    query = 'SELECT id, nom, prenom, age, poste, dossard, photo, equipe FROM joueurs WHERE 1=1'
    params = []
    if request.args.get('nom'):
        query += ' AND nom LIKE ?'
        params.append('%' + request.args['nom'] + '%')
    if request.args.get('prenom'):
        query += ' AND prenom LIKE ?'
        params.append('%' + request.args['prenom'] + '%')
    if request.args.get('age'):
        query += ' AND age = ?'
        params.append(request.args['age'])
    if request.args.get('poste'):
        query += ' AND poste = ?'
        params.append(request.args['poste'])
    if request.args.get('dossard'):
        query += ' AND dossard = ?'
        params.append(request.args['dossard'])
    if request.args.get('equipe'):
        query += ' AND equipe = ?'
        params.append(request.args['equipe'])
    c.execute(query, params)
    joueurs = [dict(id=row[0], nom=row[1], prenom=row[2], age=row[3], poste=row[4], dossard=row[5], photo=row[6], equipe=row[7]) for row in c.fetchall()]

    # Statistiques globales
    c.execute('SELECT COUNT(*), AVG(age) FROM joueurs')
    total, moyenne_age = c.fetchone()
    c.execute('SELECT poste, COUNT(*) FROM joueurs GROUP BY poste')
    par_poste = c.fetchall()
    c.execute('SELECT equipe, COUNT(*) FROM joueurs GROUP BY equipe')
    par_equipe = c.fetchall()
    conn.close()
    return render_template('liste.html', joueurs=joueurs, total=total, moyenne_age=moyenne_age, par_poste=par_poste, par_equipe=par_equipe)

# Export CSV
@app.route('/export-csv')
def export_csv():
    if not session.get('admin_logged_in'):
        flash('Accès réservé. Veuillez vous connecter.')
        return redirect(url_for('admin_login'))
    import csv
    from io import StringIO
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT nom, prenom, age, poste, dossard FROM joueurs')
    joueurs = c.fetchall()
    conn.close()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Nom', 'Prénom', 'Âge', 'Poste', 'Dossard'])
    for row in joueurs:
        writer.writerow(row)
    output = si.getvalue()
    from flask import Response
    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=joueurs.csv"}
    )


# Page de login admin
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        code_2fa = request.form.get('code_2fa')
        import random
        if '2fa_step' not in session:
            if password == 'joker17':
                # Générer un code 2FA et le stocker en session
                code = str(random.randint(100000, 999999))
                session['2fa_code'] = code
                session['2fa_step'] = True
                app.logger.info(f"[2FA DEMO] Code 2FA pour admin : {code}")
                flash('Entrez le code 2FA affiché dans la console.')
                return render_template('admin_login.html', require_2fa=True)
            else:
                flash('Mot de passe incorrect.')
        else:
            if code_2fa == session.get('2fa_code'):
                session['admin_logged_in'] = True
                session.pop('2fa_code', None)
                session.pop('2fa_step', None)
                return redirect(url_for('liste'))
            else:
                flash('Code 2FA incorrect.')
                return render_template('admin_login.html', require_2fa=True)
    return render_template('admin_login.html')

# Déconnexion admin
@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Déconnecté.')
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
