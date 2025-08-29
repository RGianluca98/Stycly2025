from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Capo(Base):
    __tablename__ = 'guardaroba'

    id = Column(Integer, primary_key=True)
    categoria = Column(String)
    tipologia = Column(String)
    taglia = Column(String)
    colore = Column(String)
    brand = Column(String)
    immagine = Column(String)
    immagine2 = Column(String)  # immagine retro
    destinazione = Column(String)
    fit = Column(String)  # Add this line to class Capo

