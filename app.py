import json
import os
import re
import pandas as pd
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- SQLAlchemy setup ---
BaseMaster = declarative_base()

class Wardrobe(BaseMaster):
    __tablename__ = 'wardrobes'
    id = Column(Integer, primary_key=True)
    nome = Column(String, unique=True)

from models import Base, Capo

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'immagini'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

engine = create_engine('sqlite:///guardaroba.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
BaseMaster.metadata.create_all(engine)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def esporta_csv():
    df = pd.read_sql_table('guardaroba', con=engine)
    df.to_csv('guardaroba.csv', index=False)

def importa_csv():
    if session.query(Capo).count() == 0:
        df = pd.read_csv('guardaroba.csv')
        for _, row in df.iterrows():
            capo = Capo(
                categoria=row['categoria'],
                tipologia=row['tipologia'],
                taglia=row['taglia'],
                fit=row['fit'],
                colore=row['colore'],
                brand=row['brand'],
                destinazione=row['destinazione'],
                immagine=row['immagine']
            )
            session.add(capo)
        session.commit()

def ricalcola_id():
    capi = session.query(Capo).order_by(Capo.id).all()
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
    session.query(Capo).delete()
    session.commit()
    for data in dati_capi:
        session.add(Capo(**data))
    session.commit()

def crea_tabella_wardrobe(nome_tabella):
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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/guardaroba')
def guardaroba():
    capi = session.query(Capo).all()
    return render_template('guardaroba.html', capi=capi)

@app.route('/immagini/<path:filename>')
def immagini(filename):
    return send_from_directory('immagini', filename)

@app.route('/modifica/<int:capo_id>', methods=['GET', 'POST'])
def modifica(capo_id):
    capo = session.query(Capo).get(capo_id)
    if not capo:
        return redirect(url_for('guardaroba'))

    if request.method == 'POST':
        for field in ['categoria', 'tipologia', 'taglia', 'fit', 'colore', 'brand', 'destinazione']:
            setattr(capo, field, request.form[field])

        file = request.files.get('immagine')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            capo.immagine = f"immagini/{filename}"

        file2 = request.files.get('immagine2')
        if file2 and allowed_file(file2.filename):
            filename2 = secure_filename(file2.filename)
            file2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename2))
            capo.immagine2 = f"immagini/{filename2}"

        session.commit()
        ricalcola_id()
        esporta_csv()
        return redirect(url_for('guardaroba'))

    return render_template('modifica_capo_wardrobe.html', capo=capo)

@app.route('/elimina/<int:capo_id>', methods=['POST'])
def elimina(capo_id):
    capo = session.query(Capo).get(capo_id)
    if capo:
        session.delete(capo)
        session.commit()
        ricalcola_id()
        esporta_csv()
    return redirect(url_for('guardaroba'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/private-wardrobe')
def private_wardrobe():
    metadata = MetaData()
    wardrobes_table = Table('wardrobes', metadata, autoload_with=engine)
    with engine.connect() as conn:
        wardrobes = conn.execute(wardrobes_table.select()).fetchall()
        wardrobes = [dict(w._mapping) for w in wardrobes]
    return render_template('private_wardrobe.html', wardrobes=wardrobes)

@app.route('/public-wardrobe')
def public_wardrobe():
    return render_template('public_wardrobe.html')

@app.route('/create-private-wardrobe', methods=['GET', 'POST'])
def create_private_wardrobe():
    if request.method == 'POST':
        nome_wardrobe = request.form['nome_wardrobe']
        nome_tabella = f"wardrobe_{nome_wardrobe}"
        nome_tabella = crea_tabella_wardrobe(nome_tabella)
        session.add(Wardrobe(nome=nome_tabella))
        session.commit()
        return redirect(url_for('private_wardrobe'))
    return render_template('create_private_wardrobe.html')

@app.route('/select-private-wardrobe', methods=['GET', 'POST'])
def select_private_wardrobe():
    wardrobes = session.query(Wardrobe).all()
    return render_template('select_private_wardrobe.html', wardrobes=wardrobes)

@app.route('/gestisci-private-wardrobe/<nome_tabella>')
def gestisci_private_wardrobe(nome_tabella):
    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)
    with engine.connect() as conn:
        rows = conn.execute(wardrobe_table.select()).fetchall()
        columns = wardrobe_table.columns.keys()
        capi = [dict(zip(columns, row)) for row in rows]
    return render_template('gestisci_private_wardrobe.html', capi=capi, nome_tabella=nome_tabella)

@app.route('/aggiungi-capo-wardrobe/<nome_tabella>', methods=['GET', 'POST'])
def aggiungi_capo_wardrobe(nome_tabella):
    with open('static/data/form_data.json') as f:
        data = json.load(f)

    if request.method == 'POST':
        values = {field: request.form.get(field) for field in ['categoria', 'tipologia', 'brand', 'destinazione', 'taglia', 'fit','colore']}
        file = request.files.get('immagine')
        file2 = request.files.get('immagine2')

        if not all(values.values()) or not file:
            return "Errore: tutti i campi sono obbligatori.", 400
        if not allowed_file(file.filename):
            return "Errore: immagine non valida.", 400

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        values['immagine'] = f"immagini/{filename}"

        if file2 and allowed_file(file2.filename):
            filename2 = secure_filename(file2.filename)
            file2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename2))
            values['immagine2'] = f"immagini/{filename2}"

        metadata = MetaData()
        tbl = Table(nome_tabella, metadata, autoload_with=engine)
        with engine.begin() as conn:
            conn.execute(tbl.insert().values(**values))
        return redirect(url_for('gestisci_private_wardrobe', nome_tabella=nome_tabella))

    return render_template('aggiungi_capo_wardrobe.html', nome_tabella=nome_tabella, **data)

@app.route('/modifica-capo-wardrobe/<nome_tabella>/<int:capo_id>', methods=['GET', 'POST'])
def modifica_capo_wardrobe(nome_tabella, capo_id):
    # Carica metadati della tabella
    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)

    # Carica dati JSON per dropdown
    with open('static/data/form_data.json') as f:
        data = json.load(f)

    # Recupera il capo da modificare
    with engine.connect() as conn:
        capo = conn.execute(
            wardrobe_table.select().where(wardrobe_table.c.id == capo_id)
        ).first()

    if not capo:
        return redirect(url_for('gestisci_private_wardrobe', nome_tabella=nome_tabella))

    capo_dict = dict(capo._mapping)

    if request.method == 'POST':
        values = {field: request.form[field] for field in ['categoria', 'tipologia', 'taglia', 'fit', 'colore', 'brand', 'destinazione']}
        file = request.files.get('immagine')
        file2 = request.files.get('immagine2')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            values['immagine'] = f"immagini/{filename}"
        else:
            values['immagine'] = capo_dict.get('immagine')

        if file2 and allowed_file(file2.filename):
            filename2 = secure_filename(file2.filename)
            file2.save(os.path.join(app.config['UPLOAD_FOLDER'], filename2))
            values['immagine2'] = f"immagini/{filename2}"
        else:
            values['immagine2'] = capo_dict.get('immagine2')

        # Esegui aggiornamento
        with engine.begin() as conn:
            conn.execute(
                wardrobe_table.update().where(wardrobe_table.c.id == capo_id).values(**values)
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
def elimina_capo_wardrobe(nome_tabella, capo_id):
    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)
    with engine.begin() as conn:
        conn.execute(wardrobe_table.delete().where(wardrobe_table.c.id == capo_id))
    return redirect(url_for('gestisci_private_wardrobe', nome_tabella=nome_tabella))

@app.route('/elimina-wardrobe/<nome_tabella>', methods=['POST'])
def elimina_wardrobe(nome_tabella):
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
def visualizza_private_wardrobe(nome_tabella):
    # Load wardrobe table dynamically
    metadata = MetaData()
    wardrobe_table = Table(nome_tabella, metadata, autoload_with=engine)

    # Fetch all rows and columns
    with engine.connect() as conn:
        rows = conn.execute(wardrobe_table.select()).fetchall()
        columns = wardrobe_table.columns.keys()
        capi = [dict(zip(columns, row)) for row in rows]

    # Load form data
    with open('static/data/form_data.json') as f:
        form_data = json.load(f)

    # Flatten all tipologie
    all_tipologie = sorted({tip for cat in form_data['tipologie'].values() for tip in cat})

    return render_template(
        'visualizza_private_wardrobe.html',
        capi=capi,
        nome_tabella=nome_tabella,
        tipologie=all_tipologie,  # Not a dict anymore!
        taglie=form_data['taglie'],
        colori=form_data['colori'],
        brands=form_data['brands']
    )




if __name__ == '__main__':
    importa_csv()
    app.run(debug=True)
