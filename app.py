from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd

app = Flask(__name__)
app.secret_key = "clave_secreta"  # Necesario para manejar sesiones

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Simulación de una base de datos de usuarios
usuarios = {
    "juan": {"password": "clavejuan", "nombre": "Juan"},
    "maria": {"password": "clavemaria", "nombre": "María"}
}

# Cargar los datos de Excel
df = pd.read_excel("notas.xlsx")
notas = df.to_dict(orient="records")

class Usuario(UserMixin):
    def __init__(self, id):
        self.id = id
        self.nombre = usuarios[id]["nombre"]

    @staticmethod
    def obtener(usuario_id):
        if usuario_id in usuarios:
            return Usuario(usuario_id)
        return None

@login_manager.user_loader
def load_user(usuario_id):
    return Usuario.obtener(usuario_id)

@app.route("/")
@login_required
def inicio():
    notas_estudiante = [estudiante for estudiante in notas if estudiante["Estudiante"] == current_user.nombre]
    return render_template("index.html", notas=notas_estudiante)

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

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=False)