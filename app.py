import json
import os
import re
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
    MetaData, ForeignKey, text, inspect
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

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


# ----------------------------
#       FLASK CONFIG
# ----------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# cartella immagini (assoluta)
BASE_DIR = os.path.dirname(__file__)
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'immagini')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# timeout sessione (in minuti)
SESSION_TIMEOUT_MINUTES = 60

# DB: usa DATABASE_URL se presente (es. Postgres su Render), altrimenti SQLite locale
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///guardaroba.db")
engine = create_engine(DATABASE_URL)


def ensure_schema():
    """
    Si assicura che le tabelle users e wardrobes siano allineate
    (solo su Postgres controlliamo/ droppiamo se schema vecchio).
    """
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            # ---- Tabella USERS ----
            users_exists = conn.execute(text("""
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'users'
            """)).first() is not None

            if users_exists:
                has_password_hash = conn.execute(text("""
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'users'
                      AND column_name = 'password_hash'
                """)).first() is not None

                if not has_password_hash:
                    conn.execute(text("DROP TABLE users CASCADE"))

            # ---- Tabella WARDROBES ----
            wardrobes_exists = conn.execute(text("""
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'wardrobes'
            """)).first() is not None

            if wardrobes_exists:
                has_user_id = conn.execute(text("""
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'wardrobes'
                      AND column_name = 'user_id'
                """)).first() is not None

                if not has_user_id:
                    conn.execute(text("DROP TABLE wardrobes CASCADE"))

    # (ri)creiamo le tabelle secondo i modelli User/Wardrobe
    BaseMaster.metadata.create_all(engine)


# esegui la sistemazione dello schema
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


def validate_password_strength(password: str) -> str | None:
    """
    Controlla robustezza password.
    Ritorna messaggio di errore, oppure None se ok.
    """
    if len(password) < 8:
        return "La password deve avere almeno 8 caratteri."
    if not re.search(r"[A-Za-z]", password):
        return "La password deve contenere almeno una lettera."
    if not re.search(r"\d", password):
        return "La password deve contenere almeno un numero."
    return None


def crea_tabella_wardrobe(nome_tabella: str) -> str:
    """
    Crea dinamicamente la tabella del wardrobe (per utente).
    Colonne allineate a tutto il codice.
    """
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
        Column('immagine2', String),
        Column('created_at', String)   # opzionale ma utile in header
    )
    metadata.create_all(engine)
    return nome_tabella


def get_personal_wardrobe(user: User) -> Wardrobe:
    """
    Restituisce (o crea) il wardrobe personale dell'utente,
    con nome: wardrobe_<username_normalizzato>
    """
    raw_name = f"wardrobe_{user.username}"
    nome_tabella = re.sub(r'\W+', '_', raw_name.lower())

    w = db_session.query(Wardrobe).filter_by(
        nome=nome_tabella,
        user_id=user.id
    ).first()

    if not w:
        # crea tabella fisica
        crea_tabella_wardrobe(nome_tabella)
        # registra nel DB master
        w = Wardrobe(nome=nome_tabella, user_id=user.id)
        db_session.add(w)
        db_session.commit()

    return w


# ----------------------------
#       SESSIONE / LOGIN
# ----------------------------

def login_required(view_func):
    """Decorator per proteggere le route: richiede utente loggato, sessione non scaduta e utente esistente."""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        user_id = session.get("user_id")
        last_active = session.get("last_active")

        if not user_id:
            flash("Devi fare login per accedere a questa pagina.", "error")
            return redirect(url_for("home"))

        # Controllo che l'utente esista ancora nel DB
        user = db_session.query(User).get(user_id)
        if not user:
            session.clear()
            flash("La tua sessione non è più valida. Effettua di nuovo il login.", "error")
            return redirect(url_for("home"))

        if last_active:
            try:
                last_active_dt = datetime.fromisoformat(last_active)
                delta = datetime.utcnow() - last_active_dt
                if delta > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                    session.clear()
                    flash("Sessione scaduta, effettua di nuovo il login.", "error")
                    return redirect(url_for("home"))
            except Exception:
                session.clear()
                flash("La sessione è scaduta, effettua di nuovo il login.", "error")
                return redirect(url_for("home"))

        session["last_active"] = datetime.utcnow().isoformat()
        return view_func(*args, **kwargs)

    return wrapped_view



# ----------------------------
#       AUTH ROUTES
# ----------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return redirect(url_for('home'))

    username = request.form.get('username', '').strip()
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''
    confirm_password = request.form.get('confirm_password') or ''

    if not username or not email or not password or not confirm_password:
        flash("Tutti i campi sono obbligatori.", "error")
        return redirect(url_for('home'))

    if password != confirm_password:
        flash("Le password non coincidono.", "error")
        return redirect(url_for('home'))

    err = validate_password_strength(password)
    if err:
        flash(err, "error")
        return redirect(url_for('home'))

    existing_user = db_session.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing_user:
        flash("Username o email già registrati.", "error")
        return redirect(url_for('home'))

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password)
    )
    db_session.add(user)
    db_session.commit()

    flash("Registrazione completata, ora effettua il login dall'Area Riservata.", "success")
    return redirect(url_for('home'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return redirect(url_for('home'))

    # piccolo rate limiting per tentativi falliti
    failed_count = session.get("login_failed_count", 0)
    last_failed_str = session.get("login_last_failed")
    if last_failed_str:
        try:
            last_failed = datetime.fromisoformat(last_failed_str)
            if datetime.utcnow() - last_failed < timedelta(minutes=10) and failed_count >= 5:
                flash("Troppi tentativi falliti. Riprova tra qualche minuto.", "error")
                return redirect(url_for('home'))
        except Exception:
            session.pop("login_failed_count", None)
            session.pop("login_last_failed", None)

    email_or_username = (request.form.get('email_or_username') or '').strip()
    password = request.form.get('password') or ''

    if not email_or_username or not password:
        flash("Inserisci credenziali valide.", "error")
        return redirect(url_for('home'))

    user = db_session.query(User).filter(
        (User.email == email_or_username.lower()) | (User.username == email_or_username)
    ).first()

    if not user or not check_password_hash(user.password_hash, password):
        session["login_failed_count"] = failed_count + 1
        session["login_last_failed"] = datetime.utcnow().isoformat()
        flash("Credenziali non valide.", "error")
        return redirect(url_for('home'))

    # login ok → reset rate limit
    session.pop("login_failed_count", None)
    session.pop("login_last_failed", None)

    # assicuro il wardrobe personale
    get_personal_wardrobe(user)

    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['email'] = user.email
    session['last_active'] = datetime.utcnow().isoformat()

    return redirect(url_for('private_wardrobe'))


@app.context_processor
def inject_user_header_info():
    """
    Aggiunge al contesto (solo se loggato):
    - current_user_username
    - current_user_email
    - current_user_last_added (timestamp ultimo capo, se disponibile)
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return {}

        user = db_session.query(User).get(user_id)
        if not user:
            session.clear()
            return {}

        last_added = None

        w = db_session.query(Wardrobe).filter_by(user_id=user_id).first()
        if w:
            metadata = MetaData()
            inspector = inspect(engine)
            existing_tables = set(inspector.get_table_names())

            if w.nome in existing_tables:
                tbl = Table(w.nome, metadata, autoload_with=engine)
                if 'created_at' in tbl.c:
                    with engine.connect() as conn:
                        row = conn.execute(
                            tbl.select()
                               .order_by(tbl.c.created_at.desc())
                               .limit(1)
                        ).first()
                    if row:
                        last_added = row._mapping.get('created_at')

        return dict(
            current_user_username=user.username,
            current_user_email=user.email,
            current_user_last_added=last_added
        )
    except Exception:
        return {}


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash("Inserisci una email valida.", "error")
            return redirect(url_for('forgot_password'))

        flash("Se l'email è registrata, riceverai le istruzioni per reimpostare la password.", "info")
        return redirect(url_for('home'))

    return render_template('forgot_password.html')


@app.route('/clear-wardrobe', methods=['POST'])
@login_required
def clear_wardrobe():
    """
    Svuota TUTTI i capi del wardrobe personale dell'utente loggato.
    """
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(user_id=user_id).first()
    if not w:
        flash("Nessun wardrobe da svuotare.", "info")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    try:
        tbl = Table(w.nome, metadata, autoload_with=engine)
        with engine.begin() as conn:
            conn.execute(tbl.delete())
        flash("Wardrobe svuotato con successo.", "success")
    except Exception as e:
        print("Errore clear_wardrobe:", e)
        flash("Errore durante la pulizia del wardrobe.", "error")

    return redirect(url_for('private_wardrobe'))


@app.route('/delete-account', methods=['GET', 'POST'])
@login_required
def delete_account():
    # se qualcuno arriva in GET, rimando alla pagina privata
    if request.method == 'GET':
        return redirect(url_for('private_wardrobe'))

    user_id = session.get('user_id')
    if not user_id:
        session.clear()
        flash("Sessione non valida.", "error")
        return redirect(url_for('home'))

    try:
        # 1) Recupero tutti i wardrobe dell'utente
        wardrobes = db_session.query(Wardrobe).filter_by(user_id=user_id).all()

        metadata = MetaData()
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        # 2) Svuoto le tabelle fisiche dei wardrobe (NON le droppo)
        for w in wardrobes:
            if w.nome in existing_tables:
                try:
                    tbl = Table(w.nome, metadata, autoload_with=engine)
                    with engine.begin() as conn:
                        conn.execute(tbl.delete())
                except Exception as e:
                    print("Errore nello svuotare la tabella wardrobe:", w.nome, e)

        # 3) Cancello le righe nella tabella master wardrobes
        db_session.query(Wardrobe).filter_by(user_id=user_id).delete(synchronize_session=False)

        # 4) Cancello l'utente
        db_session.query(User).filter_by(id=user_id).delete(synchronize_session=False)

        # 5) Commit finale
        db_session.commit()

    except Exception as e:
        db_session.rollback()
        print("Errore delete_account:", e)
        flash("Si è verificato un errore durante l'eliminazione dell'account.", "error")
        return redirect(url_for('private_wardrobe'))

    # 6) Pulisco la sessione e porto alla home
    session.clear()
    flash("Account e dati associati eliminati definitivamente.", "success")
    return redirect(url_for('home'))



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


@app.route('/products')
@app.route('/public-wardrobe')
def products():
    """
    Products = somma di tutti i wardrobe (per ora).
    """
    metadata = MetaData()
    all_capi = []

    wardrobes = db_session.query(Wardrobe).all()

    for w in wardrobes:
        try:
            tbl = Table(w.nome, metadata, autoload_with=engine)
        except Exception:
            continue

        with engine.connect() as conn:
            rows = conn.execute(tbl.select()).fetchall()
            columns = tbl.columns.keys()

            for row in rows:
                rd = dict(zip(columns, row))
                rd["wardrobe_name"] = w.nome
                all_capi.append(rd)

    return render_template("public_wardrobe.html", capi=all_capi)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/immagini/<path:filename>')
def immagini(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/contact')
def contact():
    return render_template('contact.html')


# ----------------------------
#       PRIVATE WARDROBE
# ----------------------------

@app.route('/private-wardrobe')
@login_required
def private_wardrobe():
    user_id = session.get('user_id')
    if not user_id:
        session.clear()
        flash("Sessione non valida. Effettua di nuovo il login.", "error")
        return redirect(url_for('home'))

    user = db_session.query(User).get(user_id)
    if not user:
        session.clear()
        flash("Utente non trovato. Effettua di nuovo il login.", "error")
        return redirect(url_for('home'))

    w = get_personal_wardrobe(user)

    metadata = MetaData()
    capi = []

    try:
        wardrobe_table = Table(w.nome, metadata, autoload_with=engine)
        with engine.connect() as conn:
            rows = conn.execute(wardrobe_table.select()).fetchall()
            columns = wardrobe_table.columns.keys()
            capi = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print("Errore private_wardrobe:", e)
        flash("Si è verificato un problema nel caricamento del guardaroba.", "error")

    return render_template(
        'private_wardrobe.html',
        capi=capi,
        nome_tabella=w.nome,
        username=user.username
    )


@app.route('/create-private-wardrobe', methods=['GET', 'POST'])
@login_required
def create_private_wardrobe():
    flash("La creazione di nuovi wardrobe non è più disponibile.", "info")
    return redirect(url_for('private_wardrobe'))


@app.route('/select-private-wardrobe', methods=['GET', 'POST'])
@login_required
def select_private_wardrobe():
    """
    Per ora abbiamo 1 wardrobe personale. Se in futuro vuoi più wardrobe,
    qui puoi caricare la lista.
    """
    user_id = session['user_id']
    wardrobes = db_session.query(Wardrobe).filter_by(user_id=user_id).all()
    return render_template('select_private_wardrobe.html', wardrobes=wardrobes)


@app.route('/gestisci-private-wardrobe/<nome_tabella>')
@login_required
def gestisci_private_wardrobe(nome_tabella):
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
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    # carico i dati dal JSON (tipologie, taglie ecc.)
    try:
        with open(os.path.join(BASE_DIR, 'static', 'data', 'form_data.json'), encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print("Errore lettura form_data.json:", e)
        flash("Errore interno: file di configurazione form non trovato.", "error")
        return redirect(url_for('private_wardrobe'))

    if request.method == 'POST':
        try:
            values = {
                field: request.form.get(field)
                for field in ['categoria', 'tipologia', 'brand', 'destinazione', 'taglia', 'fit', 'colore']
            }
            file = request.files.get('immagine')
            file2 = request.files.get('immagine2')

            # controllo campi obbligatori
            if not all(values.values()) or not file:
                flash("Tutti i campi e l'immagine principale sono obbligatori.", "error")
                return redirect(url_for('aggiungi_capo_wardrobe', nome_tabella=nome_tabella))

            if not allowed_file(file.filename):
                flash("Formato immagine non valido.", "error")
                return redirect(url_for('aggiungi_capo_wardrobe', nome_tabella=nome_tabella))

            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            values['immagine'] = filename

            if file2 and allowed_file(file2.filename):
                filename2 = secure_filename(file2.filename)
                file2_path = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
                file2.save(file2_path)
                values['immagine2'] = filename2
            else:
                values['immagine2'] = None

            metadata = MetaData()
            tbl = Table(nome_tabella, metadata, autoload_with=engine)

            # aggiungo created_at solo se la colonna esiste davvero
            if 'created_at' in tbl.c:
                values['created_at'] = datetime.utcnow().isoformat()

            with engine.begin() as conn:
                conn.execute(tbl.insert().values(**values))

            flash("Capo aggiunto correttamente.", "success")
            return redirect(url_for('private_wardrobe'))

        except Exception as e:
            print("Errore aggiungi_capo_wardrobe:", e)
            flash("Si è verificato un errore durante l'aggiunta del capo.", "error")
            return redirect(url_for('private_wardrobe'))

    return render_template('aggiungi_capo_wardrobe.html', nome_tabella=nome_tabella, **data)


@app.route('/modifica-capo-wardrobe/<nome_tabella>/<int:capo_id>', methods=['GET', 'POST'])
@login_required
def modifica_capo_wardrobe(nome_tabella, capo_id):
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)

    try:
        with open(os.path.join(BASE_DIR, 'static', 'data', 'form_data.json'), encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print("Errore lettura form_data.json:", e)
        flash("Errore interno: file di configurazione form non trovato.", "error")
        return redirect(url_for('private_wardrobe'))

    with engine.connect() as conn:
        capo = conn.execute(
            wardrobe_table.select().where(wardrobe_table.c.id == capo_id)
        ).first()

    if not capo:
        flash("Capo non trovato.", "error")
        return redirect(url_for('private_wardrobe'))

    capo_dict = dict(capo._mapping)

    if request.method == 'POST':
        try:
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

            flash("Capo modificato correttamente.", "success")
            return redirect(url_for('private_wardrobe'))

        except Exception as e:
            print("Errore modifica_capo_wardrobe:", e)
            flash("Errore durante la modifica del capo.", "error")
            return redirect(url_for('private_wardrobe'))

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
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)
    try:
        with engine.begin() as conn:
            conn.execute(wardrobe_table.delete().where(wardrobe_table.c.id == capo_id))
        flash("Capo eliminato.", "success")
    except Exception as e:
        print("Errore elimina_capo_wardrobe:", e)
        flash("Errore durante l'eliminazione del capo.", "error")
    return redirect(url_for('private_wardrobe'))


@app.route('/elimina-wardrobe/<nome_tabella>', methods=['POST'])
@login_required
def elimina_wardrobe(nome_tabella):
    user_id = session['user_id']
    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    try:
        wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)
        wardrobe_table.drop(engine, checkfirst=True)

        with engine.begin() as conn:
            wardrobes_table = Table('wardrobes', metadata, autoload_with=engine)
            conn.execute(wardrobes_table.delete().where(wardrobes_table.c.nome == nome_tabella))

        flash("Wardrobe eliminato.", "success")
    except Exception as e:
        print("Errore elimina_wardrobe:", e)
        flash("Errore durante l'eliminazione del wardrobe.", "error")

    return redirect(url_for('private_wardrobe'))


@app.route('/visualizza-private-wardrobe/<nome_tabella>')
@login_required
def visualizza_private_wardrobe(nome_tabella):
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

    # carico le opzioni per i filtri dal form_data
    try:
        with open(os.path.join(BASE_DIR, 'static', 'data', 'form_data.json'), encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print("Errore lettura form_data.json visualizza:", e)
        data = {
            'tipologie': [],
            'taglie': [],
            'colori': [],
            'brands': []
        }

    return render_template(
        'visualizza_private_wardrobe.html',
        capi=capi,
        nome_tabella=nome_tabella,
        tipologie=list(data.get('tipologie', {}).keys()) if isinstance(data.get('tipologie'), dict) else data.get('tipologie', []),
        taglie=data.get('taglie', []),
        colori=data.get('colori', []),
        brands=data.get('brands', [])
    )


# ----------------------------
#       EXPORT DATI GUARDAROBA
# ----------------------------

@app.route('/export-wardrobe/<nome_tabella>')
@login_required
def export_wardrobe(nome_tabella):
    user_id = session['user_id']

    w = db_session.query(Wardrobe).filter_by(nome=nome_tabella, user_id=user_id).first()
    if not w:
        flash("Non hai accesso a questo wardrobe.", "error")
        return redirect(url_for('private_wardrobe'))

    metadata = MetaData()
    wardrobe_table = Table(w.nome, metadata, autoload_with=engine)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

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

    csv_data = '\ufeff' + csv_data  # BOM per Excel

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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)



