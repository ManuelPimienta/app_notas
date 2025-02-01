from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd
import os
import csv
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "clave_secreta"
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

# Almacenar notas por curso (global para este ejemplo, en producción usa una base de datos)
notas_por_curso = {
    "Curso A": [],
    "Curso B": []
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

# Cargar estudiantes desde el archivo CSV
def cargar_estudiantes():
    estudiantes = {}
    try:
        with open('estudiantes.csv', mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if 'id' in row and 'nombre' in row and 'curso' in row:
                    estudiantes[row['id']] = {
                        "nombre": row['nombre'],
                        "curso": row['curso']
                    }
    except FileNotFoundError:
        print("Error: El archivo 'estudiantes.csv' no existe.")
    except Exception as e:
        print(f"Error al leer el archivo CSV: {str(e)}")
    return estudiantes

estudiantes = cargar_estudiantes()

# Ruta principal
@app.route("/")
def inicio():
    return render_template("index.html", estudiantes=estudiantes)

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
        if id_estudiante in estudiantes:
            # Crear una sesión para el estudiante
            session['estudiante'] = id_estudiante
            return redirect(url_for("inicio"))
        else:
            flash("Número de identificación incorrecto", "error")
    return render_template("login_estudiante.html")

# Ruta para mostrar las notas del estudiante
@app.route("/notas-estudiante")
def notas_estudiante():
    if 'estudiante' not in session:
        return redirect(url_for("login_estudiante"))

    id_estudiante = session['estudiante']
    estudiante = estudiantes[id_estudiante]
    curso = estudiante["curso"]
    notas = notas_por_curso.get(curso, [])

    # Filtrar las notas del estudiante actual
    notas_estudiante = [nota for nota in notas if nota["Estudiante"] == estudiante["nombre"]]

    return render_template("notas_estudiante.html", notas=notas_estudiante, estudiante=estudiante)

# Ruta para subir archivos de Excel
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        curso = request.form["curso"]
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
            columnas_esperadas = ["Estudiante", "Running Average", "Letter Grade", "Conducta2", "Actividad 1", "Actividad 2"]
            if not all(col in df.columns for col in columnas_esperadas):
                flash("El archivo no tiene la estructura esperada.", "error")
                return redirect(url_for("upload"))

            # Convertir las notas a una lista de diccionarios
            notas = df.to_dict(orient="records")
            notas_por_curso[curso] = notas  # Almacenar las notas en el curso correspondiente
            flash(f"Archivo subido correctamente para el curso {curso}.", "success")
        except Exception as e:
            flash(f"Error al procesar el archivo: {str(e)}", "error")
        finally:
            os.remove(ruta_archivo)  # Eliminar el archivo después de procesarlo

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
    session.pop('estudiante', None)
    return redirect(url_for("inicio"))

# Función para verificar extensiones de archivo permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}

# Crear la carpeta de subidas si no existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if __name__ == "__main__":
    app.run(debug=True)