from flask import Flask, render_template, request, redirect, url_for, flash, session as flask_session  # Renombrar la sesión de Flask
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from models import session as db_session, Curso, Estudiante, Nota  # Renombrar la sesión de SQLAlchemy
import pandas as pd
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "clave_secreta"  # Clave secreta para las sesiones de Flask
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Simulación de usuarios (profesores)
usuarios = {
    "profesor": {"password": "claveprofesor", "nombre": "Profesor"}
}

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

    return render_template("notas_estudiante.html", notas=notas, estudiante=estudiante)

# Ruta para subir archivos de Excel
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        curso_nombre = request.form["curso"]
        archivo = request.files["archivo"]

        if archivo.filename == "":
            flash("No se seleccionó ningún archivo.", "error")
            return redirect(url_for("upload"))

        if not allowed_file(archivo.filename):
            flash("Solo se permiten archivos de Excel (.xlsx).", "error")
            return redirect(url_for("upload"))

        filename = secure_filename(archivo.filename)
        ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        archivo.save(ruta_archivo)

        try:
            df = pd.read_excel(ruta_archivo)
            
            # Columnas obligatorias
            columnas_obligatorias = [
                "ID",  # Nueva columna para el ID de identificación
                "Estudiante", 
                "Running Average", 
                "Letter Grade", 
                "Conducta2"
            ]
            if not all(col in df.columns for col in columnas_obligatorias):
                flash("El archivo no tiene las columnas obligatorias.", "error")
                return redirect(url_for("upload"))

            # Detectar columnas de actividades dinámicamente
            actividades = [col for col in df.columns if col.startswith("Actividad")]
            
            # Buscar o crear el curso
            curso = db_session.query(Curso).filter_by(nombre=curso_nombre).first()
            if not curso:
                curso = Curso(nombre=curso_nombre)
                db_session.add(curso)
                db_session.commit()

            # Procesar cada fila del archivo
            for _, row in df.iterrows():
                # Buscar al estudiante por ID
                estudiante = db_session.query(Estudiante).filter_by(id=row["ID"]).first()
                
                # Si el estudiante no existe, crearlo
                if not estudiante:
                    estudiante = Estudiante(
                        id=row["ID"],  # Usar el ID del archivo
                        nombre=row["Estudiante"],
                        curso_id=curso.id,
                        running_average=row["Running Average"],
                        letter_grade=row["Letter Grade"],
                        conducta2=row["Conducta2"]
                    )
                    db_session.add(estudiante)
                    db_session.commit()
                else:
                    # Si el estudiante ya existe, actualizar sus datos
                    estudiante.nombre = row["Estudiante"]
                    estudiante.running_average = row["Running Average"]
                    estudiante.letter_grade = row["Letter Grade"]
                    estudiante.conducta2 = row["Conducta2"]
                    db_session.commit()

                # Eliminar notas existentes para evitar duplicados
                db_session.query(Nota).filter_by(estudiante_id=estudiante.id).delete()
                db_session.commit()

                # Guardar las notas dinámicamente
                for actividad in actividades:
                    calificacion = row[actividad]
                    nota = Nota(
                        estudiante_id=estudiante.id,
                        actividad=actividad,
                        calificacion=calificacion
                    )
                    db_session.add(nota)
                db_session.commit()

            flash("¡Datos actualizados correctamente!", "success")
        except Exception as e:
            db_session.rollback()
            flash(f"Error: {str(e)}", "error")
        finally:
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

# Función para verificar extensiones de archivo permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}

# Crear la carpeta de subidas si no existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if __name__ == "__main__":
    app.run(debug=False)  # Cambia a False para producción