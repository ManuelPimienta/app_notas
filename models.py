# En models.py
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session

# Configuración de la base de datos
engine = create_engine("sqlite:///app_notas.db")  # 
db_session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

class Curso(Base):
    __tablename__ = 'cursos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    estudiantes = relationship("Estudiante", back_populates="curso")

class Estudiante(Base):
    __tablename__ = 'estudiantes'
    id = Column(Integer, primary_key=True, autoincrement=False)  # ID no autoincremental
    nombre = Column(String, nullable=False)
    curso_id = Column(Integer, ForeignKey('cursos.id'))
    running_average = Column(Float)
    letter_grade = Column(String)
    conducta2 = Column(Float)
    curso = relationship("Curso", back_populates="estudiantes")
    notas = relationship("Nota", back_populates="estudiante")

class Nota(Base):
    __tablename__ = 'notas'
    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey('estudiantes.id'))
    actividad = Column(String, nullable=False)
    calificacion = Column(Float, nullable=False)
    estudiante = relationship("Estudiante", back_populates="notas")

# Crear la base de datos y las tablas
Base.metadata.create_all(engine)

# Configurar la sesión de SQLAlchemy
Session = sessionmaker(bind=engine)
session = Session()