from flask import Flask, render_template, request, redirect, url_for, flash, session as flask_session  # Renombrar la sesión de Flask
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from models import session as db_session, engine, Curso, Estudiante, Nota  # Renombrar la sesión de SQLAlchemy
import pandas as pd
import os
from werkzeug.utils import secure_filename
import os
import shutil
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = "clave_secreta"  # Clave secreta para las sesiones de Flask
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Configuración del logging
logging.basicConfig(level=logging.DEBUG)
handler = RotatingFileHandler("app.log", maxBytes=10000, backupCount=1)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Configuración de la carpeta de backups
BACKUP_FOLDER = "backups"
if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

def crear_backup():
    """
    Crea una copia de seguridad de la base de datos antes de una actualización.
    """
    try:
        # Nombre del archivo de backup (incluye la fecha y hora actual)
        fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_backup = f"backup_{fecha_hora}.db"
        ruta_backup = os.path.join(BACKUP_FOLDER, nombre_backup)

        # Ruta de la base de datos actual
        ruta_base_datos = "app_notas.db"  # Cambia esto si tu base de datos tiene otro nombre o ruta

        # Verificar si el archivo de la base de datos existe
        if not os.path.exists(ruta_base_datos):
            print(f"Error: No se encontró el archivo de la base de datos en {ruta_base_datos}")
            return False

        # Crear una copia de la base de datos actual
        shutil.copy2(ruta_base_datos, ruta_backup)
        print(f"Backup creado exitosamente: {ruta_backup}")
        return True
    except Exception as e:
        print(f"Error al crear el backup: {e}")
        return False

@app.route("/backups")
@login_required
def listar_backups():
    """
    Muestra una lista de backups disponibles.
    """
    try:
        # Obtener la lista de archivos en la carpeta de backups
        backups = os.listdir(BACKUP_FOLDER)
        backups = [f for f in backups if f.endswith(".db")]  # Filtrar solo archivos .db
        backups.sort(reverse=True)  # Ordenar de más reciente a más antiguo
    except Exception as e:
        flash(f"Error al listar los backups: {e}", "error")
        backups = []

    return render_template("backups.html", backups=backups)

@app.route("/restaurar_backup/<nombre_backup>")
@login_required
def restaurar_backup(nombre_backup):
    """
    Restaura la base de datos desde un backup seleccionado.
    """
    try:
        # Ruta del backup seleccionado
        ruta_backup = os.path.join(BACKUP_FOLDER, nombre_backup)

        # Verificar que el backup exista
        if not os.path.exists(ruta_backup):
            flash(f"El backup {nombre_backup} no existe.", "error")
            app.logger.error(f"El backup {nombre_backup} no existe.")
            return redirect(url_for("listar_backups"))

        # Ruta de la base de datos actual
        ruta_base_datos = "pp_notas.db"  # Cambia esto si tu base de datos tiene otro nombre

        # Reemplazar la base de datos actual con el backup
        app.logger.debug(f"Restaurando la base de datos desde el backup: {ruta_backup}")
        shutil.copy2(ruta_backup, ruta_base_datos)

        # --- CORRECCIÓN: Manejo de la sesión de SQLAlchemy ---
        app.logger.debug("Reiniciando la sesión de SQLAlchemy...")

        # 1. Cerrar la sesión actual (si existe)
        if db_session:  # Verifica si db_session existe
            db_session.close()  # Usa close() para cerrar la sesión

        # 2. Reconfigurar la sesión con el nuevo engine
        db_session.bind = engine  # Asigna el engine a la sesión

        # --- FIN DE LA CORRECCIÓN ---

        flash(f"Base de datos restaurada desde el backup: {nombre_backup}", "success")
        app.logger.debug(f"Base de datos restaurada desde el backup: {nombre_backup}")

    except Exception as e:
        flash(f"Error al restaurar el backup: {e}", "error")
        app.logger.error(f"Error al restaurar el backup: {e}")

    return redirect(url_for("listar_backups"))

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Simulación de usuarios (profesores)
usuarios = {
    "profesor": {"password": "claveprofesor", "nombre": "Profesor"}
}

# En app.py, antes de iniciar la aplicación
with app.app_context():
    cursos_predefinidos = [
        "Ciencias Sociales 9A",
        "Ciencias Sociales 9B",
        "Ciencias Sociales 9C",
        "Ciencias Sociales 10A",
        "Ciencias Sociales 10B",
        "Ciencias Sociales 11A",
        "Ciencias Sociales 11B"
    ]
    for nombre_curso in cursos_predefinidos:
        curso = db_session.query(Curso).filter_by(nombre=nombre_curso).first()
        if not curso:
            nuevo_curso = Curso(nombre=nombre_curso)
            db_session.add(nuevo_curso)
    db_session.commit()

# Clase Usuario para Flask-Login
class Usuario(UserMixin):
    def __init__(self, id):
        self.id = id
        self.nombre = usuarios[id]["nombre"]

    @staticmethod
    def obtener(usuario_id):
        if usuario_id in usuarios:
            return Usuario(usuario_id)
        return None

# Función user_loader para Flask-Login
@login_manager.user_loader
def load_user(usuario_id):
    return Usuario.obtener(usuario_id)

# Ruta principal
@app.route("/")
def inicio():
    return render_template("index.html")

# Ruta para el login del profesor
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario_id = request.form["usuario"]
        clave = request.form["clave"]
        if usuario_id in usuarios and usuarios[usuario_id]["password"] == clave:
            usuario = Usuario(usuario_id)
            login_user(usuario)
            return redirect(url_for("inicio"))
        else:
            flash("Usuario o contraseña incorrectos", "error")
    return render_template("login.html")

# Ruta para el login de estudiantes
@app.route("/login-estudiante", methods=["GET", "POST"])
def login_estudiante():
    if request.method == "POST":
        id_estudiante = request.form["id"]
        try:
            id_estudiante = int(id_estudiante)
            estudiante = db_session.query(Estudiante).filter_by(id=id_estudiante).first()
            if estudiante:
                # Crear una sesión para el estudiante
                flask_session['estudiante_id'] = estudiante.id
                return redirect(url_for("notas_estudiante"))
            else:
                flash("Número de identificación incorrecto", "error")
        except ValueError:
            flash("El ID debe ser un número válido", "error")
    return render_template("login_estudiante.html")

# Ruta para mostrar las notas del estudiante
@app.route("/notas-estudiante")
def notas_estudiante():
    if 'estudiante_id' not in flask_session:
        return redirect(url_for("login_estudiante"))

    estudiante = db_session.query(Estudiante).filter_by(id=flask_session['estudiante_id']).first()
    notas = db_session.query(Nota).filter_by(estudiante_id=estudiante.id).all()

    # Obtener las actividades únicas
    actividades = list(set(nota.actividad for nota in notas))

    return render_template("notas_estudiante.html", notas=notas, estudiante=estudiante, actividades=actividades)

# Ruta para subir archivos de Excel
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        curso_nombre = request.form["curso"]
        archivo = request.files["archivo"]

        # Validar que se haya seleccionado un archivo
        if archivo.filename == "":
            flash("No se seleccionó ningún archivo.", "error")
            return redirect(url_for("upload"))

        # Validar la extensión del archivo
        if not allowed_file(archivo.filename):
            flash("Solo se permiten archivos de Excel (.xlsx).", "error")
            return redirect(url_for("upload"))

        # Crear un backup antes de la actualización
        app.logger.debug("Intentando crear un backup antes de la actualización...")
        if not crear_backup():
            flash("Error al crear el backup. No se realizaron cambios.", "error")
            return redirect(url_for("upload"))

        # Guardar el archivo temporalmente
        filename = secure_filename(archivo.filename)
        ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        archivo.save(ruta_archivo)

        try:
            # Leer el archivo Excel
            app.logger.debug(f"Leyendo el archivo Excel: {ruta_archivo}")
            df = pd.read_excel(ruta_archivo, sheet_name="Hoja1", engine="openpyxl")

            # Verificar que el archivo no esté vacío
            if df.empty:
                flash("El archivo no tiene datos válidos.", "error")
                return redirect(url_for("upload"))

            # Columnas obligatorias
            columnas_obligatorias = ["ID", "Estudiante", "Running Average", "Letter Grade", "Conducta2"]
            if not all(col in df.columns for col in columnas_obligatorias):
                flash("El archivo no tiene las columnas obligatorias.", "error")
                return redirect(url_for("upload"))

            # Limpiar la columna "ID"
            df = df.dropna(subset=["ID"])
            df = df[pd.to_numeric(df["ID"], errors="coerce").notna()]

            # Verificar que el archivo no esté vacío después de la limpieza
            if df.empty:
                flash("El archivo no tiene datos válidos después de la limpieza.", "error")
                return redirect(url_for("upload"))

            # Convertir la columna "ID" a enteros
            df["ID"] = df["ID"].astype(int)

            # Buscar o crear el curso
            curso = db_session.query(Curso).filter_by(nombre=curso_nombre).first()
            if not curso:
                flash("El curso seleccionado no existe.", "error")
                return redirect(url_for("upload"))

            # Identificar dinámicamente las columnas de actividades
            actividades = [col for col in df.columns if col not in columnas_obligatorias]
            actividades = [col for col in actividades if not col.startswith("Unnamed") and not col.strip() == ""]

            # Procesar cada fila del archivo
            app.logger.debug("Procesando filas del archivo Excel...")
            for _, row in df.iterrows():
                # Reemplazar NaN en campos numéricos
                running_avg = row["Running Average"] if not pd.isna(row["Running Average"]) else 0.0
                conducta = row["Conducta2"] if not pd.isna(row["Conducta2"]) else 0.0
                letter_grade = row["Letter Grade"] if not pd.isna(row["Letter Grade"]) else "N/A"

                # Buscar al estudiante por ID
                estudiante = db_session.query(Estudiante).filter_by(id=row["ID"]).first()
                
                # Si el estudiante no existe, crearlo
                if not estudiante:
                    estudiante = Estudiante(
                        id=row["ID"],
                        nombre=row["Estudiante"],
                        curso_id=curso.id,
                        running_average=running_avg,
                        letter_grade=letter_grade,
                        conducta2=conducta
                    )
                    db_session.add(estudiante)
                else:
                    # Si el estudiante ya existe, actualizar sus datos
                    estudiante.nombre = row["Estudiante"]
                    estudiante.running_average = running_avg
                    estudiante.letter_grade = letter_grade
                    estudiante.conducta2 = conducta

                db_session.commit()

                # Eliminar notas existentes para evitar duplicados
                db_session.query(Nota).filter_by(estudiante_id=estudiante.id).delete()
                db_session.commit()

                # Guardar las notas dinámicamente
                for actividad in actividades:
                    calificacion = row[actividad] if not pd.isna(row[actividad]) else 0.0
                    nota = Nota(
                        estudiante_id=estudiante.id,
                        actividad=actividad,
                        calificacion=calificacion
                    )
                    db_session.add(nota)
                db_session.commit()

            flash("¡Datos actualizados correctamente!", "success")
            app.logger.debug("Datos actualizados correctamente.")
        except Exception as e:
            db_session.rollback()
            flash(f"Error: {str(e)}", "error")
            app.logger.error(f"Error al procesar el archivo Excel: {e}")
        finally:
            # Eliminar el archivo temporal
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)

        return redirect(url_for("upload"))

    return render_template("upload.html")

# Ruta para cerrar sesión del profesor
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("inicio"))

# Ruta para cerrar sesión del estudiante
@app.route("/logout-estudiante")
def logout_estudiante():
    flask_session.pop('estudiante_id', None)
    return redirect(url_for("inicio"))

# Ruta para buscar estudiantes
@app.route("/buscar-estudiante", methods=["GET"])
@login_required
def buscar_estudiante():
    query = request.args.get("q", "").strip()  # Término de búsqueda
    curso_nombre = request.args.get("curso", "").strip()  # Curso seleccionado

    # Construir la consulta base
    consulta = db_session.query(Estudiante)

    # Filtrar por curso si se seleccionó uno
    if curso_nombre:
        curso = db_session.query(Curso).filter_by(nombre=curso_nombre).first()
        if curso:
            consulta = consulta.filter_by(curso_id=curso.id)

    # Filtrar por nombre o ID
    if query:
        consulta = consulta.filter(
            (Estudiante.nombre.ilike(f"%{query}%")) | (Estudiante.id == query)
        )

    # Ejecutar la consulta
    estudiantes = consulta.all()

    return render_template("resultados_busqueda.html", estudiantes=estudiantes, query=query, curso_nombre=curso_nombre)

# Función para verificar extensiones de archivo permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}

# Crear la carpeta de subidas si no existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if __name__ == "__main__":
    app.run(debug=False)  # Cambia a False para producción