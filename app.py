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
    MetaData, ForeignKey, text
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
    Si assicura che le tabelle users e wardrobes abbiano le colonne
    aggiornate. Se mancano colonne critiche su Postgres, droppa e ricrea.
    Su SQLite non usa information_schema.
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


def get_personal_wardrobe(user: User) -> Wardrobe:
    """
    Restituisce (o crea) il wardrobe personale dell'utente,
    con nome del tipo: wardrobe_<username_normalizzato>
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
    """Decorator per proteggere le route: richiede utente loggato e sessione non scaduta."""

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        user_id = session.get("user_id")
        last_active = session.get("last_active")

        if not user_id:
            flash("Devi fare login per accedere a questa pagina.", "error")
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
    # gestiamo solo POST dal modal; GET → home
    if request.method == 'GET':
        return redirect(url_for('home'))

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password')

    if not username or not email or not password:
        flash("Tutti i campi sono obbligatori.", "error")
        return redirect(url_for('home'))

    if len(password) < 6:
        flash("La password deve avere almeno 6 caratteri.", "error")
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
    # gestiamo solo POST dal modal; GET → home
    if request.method == 'GET':
        return redirect(url_for('home'))

    email_or_username = request.form.get('email_or_username', '').strip()
    password = request.form.get('password')

    if not email_or_username or not password:
        flash("Inserisci credenziali valide.", "error")
        return redirect(url_for('home'))

    user = db_session.query(User).filter(
        (User.email == email_or_username.lower()) | (User.username == email_or_username)
    ).first()

    if not user or not check_password_hash(user.password_hash, password):
        flash("Credenziali non valide.", "error")
        return redirect(url_for('home'))

    # assicuriamo l'esistenza del wardrobe personale
    get_personal_wardrobe(user)

    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['last_active'] = datetime.utcnow().isoformat()

    return redirect(url_for('private_wardrobe'))


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
def products():
    return render_template('products.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/immagini/<path:filename>')
def immagini(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/public-wardrobe')
def public_wardrobe():
    """
    Mostra TUTTI i capi di TUTTI i wardrobe di TUTTI gli utenti.
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


# ----------------------------
#       PRIVATE WARDROBE
# ----------------------------

@app.route('/private-wardrobe')
@login_required
def private_wardrobe():
    """
    Unico wardrobe personale per utente.
    Pagina: "<username> Personal Wardrobe" + grid di capi + card "+" per aggiungere.
    """
    user_id = session['user_id']
    user = db_session.query(User).get(user_id)

    # recupera (o crea) il wardrobe personale
    w = get_personal_wardrobe(user)

    metadata = MetaData()
    wardrobe_table = Table(w.nome, metadata, autoload_with=engine)
    with engine.connect() as conn:
        rows = conn.execute(wardrobe_table.select()).fetchall()
        columns = wardrobe_table.columns.keys()
        capi = [dict(zip(columns, row)) for row in rows]

    return render_template(
        'private_wardrobe.html',
        capi=capi,
        nome_tabella=w.nome,
        username=user.username
    )


# le route seguenti restano per la gestione tecnica dei capi/tabelle
# (agganciare i link dalla pagina My Wardrobe)

@app.route('/create-private-wardrobe', methods=['GET', 'POST'])
@login_required
def create_private_wardrobe():
    """
    NON più usata in UI (niente link nel menu).
    La teniamo solo per compatibilità, ma idealmente da rimuovere in futuro.
    """
    flash("La creazione di nuovi wardrobe non è più disponibile.", "info")
    return redirect(url_for('private_wardrobe'))


@app.route('/select-private-wardrobe', methods=['GET', 'POST'])
@login_required
def select_private_wardrobe():
    """
    Non più necessaria con un solo wardrobe personale.
    Reindirizziamo alla pagina principale del wardrobe.
    """
    return redirect(url_for('private_wardrobe'))


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

    with open('static/data/form_data.json') as f:
        data = json.load(f)

    with engine.connect() as conn:
        capo = conn.execute(
            wardrobe_table.select().where(wardrobe_table.c.id == capo_id)
        ).first()

    if not capo:
        return redirect(url_for('private_wardrobe'))

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
    with engine.begin() as conn:
        conn.execute(wardrobe_table.delete().where(wardrobe_table.c.id == capo_id))
    return redirect(url_for('private_wardrobe'))


@app.route('/elimina-wardrobe/<nome_tabella>', methods=['POST'])
@login_required
def elimina_wardrobe(nome_tabella):
    """
    Con un solo wardrobe personale, in pratica questa route non dovrebbe servire.
    La lascio per compatibilità, ma idealmente da non esporre nella UI.
    """
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

    return redirect(url_for('private_wardrobe'))


@app.route('/visualizza-private-wardrobe/<nome_tabella>')
@login_required
def visualizza_private_wardrobe(nome_tabella):
    """
    Se qualcuno ci arriva, reindirizziamo al wardrobe personale.
    """
    return redirect(url_for('private_wardrobe'))


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
