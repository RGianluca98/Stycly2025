import json
import os
import re
import pandas as pd
import io
import csv
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, session, flash, Response
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import (
    create_engine, Table, Column, Integer, String,
    MetaData, ForeignKey, text     # <- AGGIUNTO text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ----------------------------
#       SQLALCHEMY MODELS
# ----------------------------

BaseMaster = declarative_base()


class Wardrobe(BaseMaster):
    __tablename__ = 'wardrobes'
    id = Column(Integer, primary_key=True)
    nome = Column(String, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)


class User(BaseMaster):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


# Modello della tabella guardaroba "generale"
from models import Base, Capo


# ----------------------------
#       FLASK CONFIG
# ----------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# cartella immagini (assoluta)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'immagini')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# timeout sessione (in minuti)
SESSION_TIMEOUT_MINUTES = 60

# DB: usa DATABASE_URL se presente (es. Postgres su Render), altrimenti SQLite locale
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///guardaroba.db")
engine = create_engine(DATABASE_URL)


def ensure_schema():
    """
    Assicura che sul DB (soprattutto su Render/Postgres) esistano
    le colonne introdotte dopo: users.password_hash, wardrobes.user_id.
    Se la colonna esiste già, l'errore viene ignorato.
    """
    with engine.begin() as conn:
        # Aggiungi password_hash a users se manca
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);"
            ))
        except Exception:
            # colonna già presente o tabella non ancora creata
            pass

        # Aggiungi user_id a wardrobes se manca
        try:
            conn.execute(text(
                "ALTER TABLE wardrobes ADD COLUMN user_id INTEGER;"
            ))
        except Exception:
            # colonna già presente
            pass


# crea tabelle definite in models.py (Capo / guardaroba)
Base.metadata.create_all(engine)

# crea tabelle definite qui (User, Wardrobe)
BaseMaster.metadata.create_all(engine)

# assicura che le tabelle abbiano le colonne più recenti
ensure_schema()

# sessione DB
Session = sessionmaker(bind=engine)
db_session = Session()


# ----------------------------
#       FUNZIONI UTILI
# ----------------------------

def allowed_file(filename: str) -> bool:
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    )


def esporta_csv():
    """Esporta la tabella 'guardaroba' in guardaroba.csv (backup locale)."""
    try:
        df = pd.read_sql_table('guardaroba', con=engine)
        df.to_csv('guardaroba.csv', index=False)
    except Exception:
        # se la tabella non esiste o altro, non bloccare l'app
        pass


def importa_csv():
    """Importa dati iniziali da guardaroba.csv se la tabella è vuota."""
    try:
        if db_session.query(Capo).count() == 0 and os.path.exists('guardaroba.csv'):
            df = pd.read_csv('guardaroba.csv')
            for _, row in df.iterrows():
                capo = Capo(
                    categoria=row['categoria'],
                    tipologia=row['tipologia'],
                    taglia=row['taglia'],
                    fit=row.get('fit'),
                    colore=row['colore'],
                    brand=row['brand'],
                    destinazione=row['destinazione'],
                    immagine=row['immagine']
                )
                db_session.add(capo)
            db_session.commit()
    except Exception:
        # non blocchiamo l'avvio se manca il file o c'è un problema
        pass


def ricalcola_id():
    """Ricompatta gli ID nella tabella guardaroba (Capo)."""
    capi = db_session.query(Capo).order_by(Capo.id).all()
    dati_capi = [{
        'categoria': c.categoria,
        'tipologia': c.tipologia,
        'taglia': c.taglia,
        'colore': c.colore,
        'fit': c.fit,
        'brand': c.brand,
        'destinazione': c.destinazione,
        'immagine': c.immagine
    } for c in capi]

    db_session.query(Capo).delete()
    db_session.commit()

    for data in dati_capi:
        db_session.add(Capo(**data))
    db_session.commit()


def crea_tabella_wardrobe(nome_tabella: str) -> str:
    """Crea dinamicamente la tabella del wardrobe (per utente)."""
    nome_tabella = re.sub(r'\W+', '_', nome_tabella.lower())
    metadata = MetaData()
    Table(
        nome_tabella, metadata,
        Column('id', Integer, primary_key=True),
        Column('categoria', String),
        Column('tipologia', String),
        Column('taglia', String),
        Column('fit', String),
        Column('colore', String),
        Column('brand', String),
        Column('destinazione', String),
        Column('immagine', String),
        Column('immagine2', String)
    )
    metadata.create_all(engine)
    return nome_tabella


# ----------------------------
#       SESSIONE / LOGIN
# ----------------------------

def login_required(view_func):
    """Decorator per proteggere le route: richiede utente loggato e sessione non scaduta."""

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        user_id = session.get("user_id")
        last_active = session.get("last_active")

        # Non loggato
        if not user_id:
            flash("Devi fare login per accedere a questa pagina.", "error")
            return redirect(url_for("login"))

        # Controllo timeout sessione
        if last_active:
            try:
                last_active_dt = datetime.fromisoformat(last_active)
                delta = datetime.utcnow() - last_active_dt
                if delta > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                    session.clear()
                    flash("Sessione scaduta, effettua di nuovo il login.", "error")
                    return redirect(url_for("login"))
            except Exception:
                session.clear()
                flash("La sessione è scaduta, effettua di nuovo il login.", "error")
                return redirect(url_for("login"))

        # aggiorno last_active
        session["last_active"] = datetime.utcnow().isoformat()
        return view_func(*args, **kwargs)

    return wrapped_view


# ----------------------------
#       AUTH ROUTES
# ----------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        if not username or not email or not password:
            flash("Tutti i campi sono obbligatori.", "error")
            return redirect(url_for('register'))

        if len(password) < 6:
            flash("La password deve avere almeno 6 caratteri.", "error")
            return redirect(url_for('register'))

        existing_user = db_session.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("Username o email già registrati.", "error")
            return redirect(url_for('register'))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db_session.add(user)
        db_session.commit()
        flash("Registrazione completata, ora puoi fare login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_username = request.form.get('email_or_username', '').strip()
        password = request.form.get('password')

        if not email_or_username or not password:
            flash("Inserisci credenziali valide.", "error")
            return redirect(url_for('login'))

        user = db_session.query(User).filter(
            (User.email == email_or_username.lower()) | (User.username == email_or_username)
        ).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Credenziali non valide.", "error")
            return redirect(url_for('login'))

        session.clear()
        session['user_id'] = user.id
        session['username'] = user.username
        session['last_active'] = datetime.utcnow().isoformat()

        return redirect(url_for('private_wardrobe'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# ----------------------------
#       ROUTE PUBBLICHE
# ----------------------------

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/guardaroba')
def guardaroba():
    capi = db_session.query(Capo).all()
    return render_template('guardaroba.html', capi=capi)


@app.route('/immagini/<path:filename>')
def immagini(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/public-wardrobe')
def public_wardrobe():
    return render_template('public_wardrobe.html')


# ----------------------------
#       CRUD CAPO "GENERALE"
# ----------------------------

@app.route('/modifica/<int:capo_id>', methods=['GET', 'POST'])
def modifica(capo_id):
    capo = db_session.query(Capo).get(capo_id)
    if not capo:
        return redirect(url_for('guardaroba'))

    if request.method == 'POST':
        for field in ['categoria', 'tipologia', 'taglia', 'fit', 'colore', 'brand', 'destinazione']:
            setattr(capo, field, request.form[field])

        file = request.files.get('immagine')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)
            capo.immagine = f"immagini/{filename}"

        file2 = request.files.get('immagine2')
        if file2 and allowed_file(file2.filename):
            filename2 = secure_filename(file2.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename2))
            capo.immagine2 = f"immagini/{filename2}"

        db_session.commit()
        ricalcola_id()
        esporta_csv()
        return redirect(url_for('guardaroba'))

    return render_template('modifica_capo_wardrobe.html', capo=capo)


@app.route('/elimina/<int:capo_id>', methods=['POST'])
def elimina(capo_id):
    capo = db_session.query(Capo).get(capo_id)
    if capo:
        db_session.delete(capo)
        db_session.commit()
        ricalcola_id()
        esporta_csv()
    return redirect(url_for('guardaroba'))


# ----------------------------
#       PRIVATE WARDROBE
# ----------------------------

@app.route('/private-wardrobe')
@login_required
def private_wardrobe():
    user_id = session['user_id']
    wardrobes = db_session.query(Wardrobe).filter_by(user_id=user_id).all()
    return render_template('private_wardrobe.html', wardrobes=wardrobes)


@app.route('/create-private-wardrobe', methods=['GET', 'POST'])
@login_required
def create_private_wardrobe():
    if request.method == 'POST':
        nome_wardrobe = request.form['nome_wardrobe']
        nome_tabella = f"wardrobe_{nome_wardrobe}"
        nome_tabella = crea_tabella_wardrobe(nome_tabella)

        user_id = session['user_id']
        db_session.add(Wardrobe(nome=nome_tabella, user_id=user_id))
        db_session.commit()
        return redirect(url_for('private_wardrobe'))

    return render_template('create_private_wardrobe.html')


@app.route('/select-private-wardrobe', methods=['GET', 'POST'])
@login_required
def select_private_wardrobe():
    user_id = session['user_id']
    wardrobes = db_session.query(Wardrobe).filter_by(user_id=user_id).all()
    return render_template('select_private_wardrobe.html', wardrobes=wardrobes)


@app.route('/gestisci-private-wardrobe/<nome_tabella>')
@login_required
def gestisci_private_wardrobe(nome_tabella):
    # controllo ownership
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)
    with engine.connect() as conn:
        rows = conn.execute(wardrobe_table.select()).fetchall()
        columns = wardrobe_table.columns.keys()
        capi = [dict(zip(columns, row)) for row in rows]
    return render_template('gestisci_private_wardrobe.html', capi=capi, nome_tabella=nome_tabella)


@app.route('/aggiungi-capo-wardrobe/<nome_tabella>', methods=['GET', 'POST'])
@login_required
def aggiungi_capo_wardrobe(nome_tabella):
    # controllo ownership
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    with open('static/data/form_data.json') as f:
        data = json.load(f)

    if request.method == 'POST':
        values = {
            field: request.form.get(field)
            for field in ['categoria', 'tipologia', 'brand', 'destinazione', 'taglia', 'fit', 'colore']
        }
        file = request.files.get('immagine')
        file2 = request.files.get('immagine2')

        if not all(values.values()) or not file:
            return "Errore: tutti i campi sono obbligatori.", 400
        if not allowed_file(file.filename):
            return "Errore: immagine non valida.", 400

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        values['immagine'] = filename

        if file2 and allowed_file(file2.filename):
            filename2 = secure_filename(file2.filename)
            file2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename2))
            values['immagine2'] = filename2

        metadata = MetaData()
        tbl = Table(nome_tabella, metadata, autoload_with=engine)
        with engine.begin() as conn:
            conn.execute(tbl.insert().values(**values))
        return redirect(url_for('gestisci_private_wardrobe', nome_tabella=nome_tabella))

    return render_template('aggiungi_capo_wardrobe.html', nome_tabella=nome_tabella, **data)


@app.route('/modifica-capo-wardrobe/<nome_tabella>/<int:capo_id>', methods=['GET', 'POST'])
@login_required
def modifica_capo_wardrobe(nome_tabella, capo_id):
    # controllo ownership
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)

    with open('static/data/form_data.json') as f:
        data = json.load(f)

    with engine.connect() as conn:
        capo = conn.execute(
            wardrobe_table.select().where(wardrobe_table.c.id == capo_id)
        ).first()

    if not capo:
        return redirect(url_for('gestisci_private_wardrobe', nome_tabella=nome_tabella))

    capo_dict = dict(capo._mapping)

    if request.method == 'POST':
        values = {
            field: request.form[field]
            for field in ['categoria', 'tipologia', 'taglia', 'fit', 'colore', 'brand', 'destinazione']
        }
        file = request.files.get('immagine')
        file2 = request.files.get('immagine2')

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            values['immagine'] = filename
        else:
            values['immagine'] = capo_dict.get('immagine')

        if file2 and allowed_file(file2.filename):
            filename2 = secure_filename(file2.filename)
            file2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename2))
            values['immagine2'] = filename2
        else:
            values['immagine2'] = capo_dict.get('immagine2')

        with engine.begin() as conn:
            conn.execute(
                wardrobe_table.update()
                .where(wardrobe_table.c.id == capo_id)
                .values(**values)
            )

        return redirect(url_for('gestisci_private_wardrobe', nome_tabella=nome_tabella))

    return render_template(
        'modifica_capo_wardrobe.html',
        capo=capo_dict,
        nome_tabella=nome_tabella,
        tipologie=data['tipologie'],
        brands=data['brands'],
        destinazioni=data['destinazioni'],
        taglie=data['taglie'],
        fit=data['fit'],
        colori=data['colori']
    )


@app.route('/elimina_capo_wardrobe/<nome_tabella>/<int:capo_id>', methods=['POST'])
@login_required
def elimina_capo_wardrobe(nome_tabella, capo_id):
    # controllo ownership
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)
    with engine.begin() as conn:
        conn.execute(wardrobe_table.delete().where(wardrobe_table.c.id == capo_id))
    return redirect(url_for('gestisci_private_wardrobe', nome_tabella=nome_tabella))


@app.route('/elimina-wardrobe/<nome_tabella>', methods=['POST'])
@login_required
def elimina_wardrobe(nome_tabella):
    # controllo ownership
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)
    wardrobe_table.drop(engine)

    try:
        wardrobes_table = Table('wardrobes', metadata, autoload_with=engine)
        with engine.begin() as conn:
            conn.execute(wardrobes_table.delete().where(wardrobes_table.c.nome == nome_tabella))
    except Exception:
        pass

    return redirect(url_for('select_private_wardrobe'))


@app.route('/visualizza-private-wardrobe/<nome_tabella>')
@login_required
def visualizza_private_wardrobe(nome_tabella):
    # controllo ownership
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)

    with engine.connect() as conn:
        rows = conn.execute(wardrobe_table.select()).fetchall()
        columns = wardrobe_table.columns.keys()
        capi = [dict(zip(columns, row)) for row in rows]

    with open('static/data/form_data.json') as f:
        form_data = json.load(f)

    all_tipologie = sorted({tip for cat in form_data['tipologie'].values() for tip in cat})

    return render_template(
        'visualizza_private_wardrobe.html',
        capi=capi,
        nome_tabella=nome_tabella,
        tipologie=all_tipologie,
        taglie=form_data['taglie'],
        colori=form_data['colori'],
        brands=form_data['brands']
    )


# ----------------------------
#       EXPORT DATI GUARDAROBA
# ----------------------------

@app.route('/export-wardrobe/<nome_tabella>')
@login_required
def export_wardrobe(nome_tabella):
    user_id = session['user_id']

    # Controllo che il wardrobe appartenga all'utente loggato
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    wardrobe_table = Table(w.nome, metadata, autoload_with=engine)

    # Usiamo StringIO per costruire il CSV in memoria
    output = io.StringIO()

    # IMPORTANTE: separatore ';' per Excel in italiano
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Intestazioni colonne (ordine chiaro e fisso)
    writer.writerow([
        "wardrobe_name",
        "capo_id",
        "categoria",
        "tipologia",
        "taglia",
        "fit",
        "colore",
        "brand",
        "destinazione",
        "immagine",
        "immagine2",
    ])

    # Righe del guardaroba
    with engine.connect() as conn:
        rows = conn.execute(wardrobe_table.select()).fetchall()
        columns = wardrobe_table.columns.keys()

        for row in rows:
            row_dict = dict(zip(columns, row))
            writer.writerow([
                w.nome,
                row_dict.get('id'),
                row_dict.get('categoria'),
                row_dict.get('tipologia'),
                row_dict.get('taglia'),
                row_dict.get('fit'),
                row_dict.get('colore'),
                row_dict.get('brand'),
                row_dict.get('destinazione'),
                row_dict.get('immagine'),
                row_dict.get('immagine2'),
            ])

    csv_data = output.getvalue()
    output.close()

    # Aggiungiamo BOM per Excel (gestione corretta UTF-8)
    csv_data = '\ufeff' + csv_data

    filename = f"{w.nome}_stycly.csv"

    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ----------------------------
#       AVVIO LOCALE
# ----------------------------

if __name__ == '__main__':
    importa_csv()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)


