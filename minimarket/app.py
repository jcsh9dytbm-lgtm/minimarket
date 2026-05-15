from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///minimarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mi_clave_secreta'

db = SQLAlchemy(app)

# LOGIN
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# USUARIO (con roles + hash)
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default="cajero")

# PRODUCTO
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    categoria = db.Column(db.String(100))
    precio = db.Column(db.Float)
    stock = db.Column(db.Integer)

# VENTA
class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto = db.Column(db.String(100))
    cantidad = db.Column(db.Integer)
    total = db.Column(db.Float)
    fecha = db.Column(db.Date, default=date.today)

with app.app_context():
    db.create_all()

    # ADMIN por defecto (solo 1 vez)
    if not Usuario.query.filter_by(username="admin").first():
        db.session.add(
            Usuario(
                username="admin",
                password=generate_password_hash("1234"),
                role="admin"
            )
        )
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# 🔐 LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form['username']).first()

        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect('/')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# 🏠 DASHBOARD
@app.route('/')
@login_required
def index():
    productos = Producto.query.all()
    ventas = Venta.query.all()

    total_productos = len(productos)
    total_ventas = sum(v.total for v in ventas)
    total_hoy = sum(v.total for v in ventas if v.fecha == date.today())

    return render_template(
        'index.html',
        productos=productos,
        ventas=ventas,
        total_productos=total_productos,
        total_ventas=total_ventas,
        total_hoy=total_hoy,
        role=current_user.role
    )

# ➕ PRODUCTO (solo admin)
@app.route('/agregar', methods=['POST'])
@login_required
def agregar():
    if current_user.role != "admin":
        return redirect('/')

    db.session.add(Producto(
        nombre=request.form['nombre'],
        categoria=request.form['categoria'],
        precio=float(request.form['precio']),
        stock=int(request.form['stock'])
    ))
    db.session.commit()
    return redirect('/')

# ❌ ELIMINAR (solo admin)
@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    if current_user.role != "admin":
        return redirect('/')

    p = Producto.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return redirect('/')

# 💰 VENTA
@app.route('/venta', methods=['POST'])
@login_required
def venta():
    producto = Producto.query.get(int(request.form['producto_id']))
    cantidad = int(request.form['cantidad'])

    if producto and producto.stock >= cantidad:
        producto.stock -= cantidad
        total = producto.precio * cantidad

        db.session.add(Venta(
            producto=producto.nombre,
            cantidad=cantidad,
            total=total
        ))
        db.session.commit()

        return render_template('ticket.html', producto=producto, cantidad=cantidad, total=total)

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)