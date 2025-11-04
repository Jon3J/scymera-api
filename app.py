import os
from flask import Flask, render_template,request,send_file,url_for,redirect
from dotenv import load_dotenv
import stripe
from itsdangerous import URLSafeTimedSerializer,SignatureExpired,BadSignature

#Cargamos variables de entorno (.env)
load_dotenv()

#Inicializamos aplicación de Flask
app = Flask(__name__)

# Configuración de claves
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

#------------------------------------------
# Rutas principales
#------------------------------------------

# 💰 Datos de tus robots
robots = {
    "dowjonesbot": {
        "name": "C.E.C.I. Dow 30 (Dow Jones Bot)",
        "amount": 25000,  # 💶 250€ (en céntimos)
        "file": "C.E.C.I. DOW 30.zip",
        "image": "Dow_Jones_dolar.png"
    },
    "orobot": {
        "name": "Project Gold (Oro Bot)",
        "amount": 25000,  # 💶 250€ (en céntimos)
        "file": "PROJECT GOLD.zip",
        "image": "XAUUSD_oro.png"
    },
    "nasdaqbot": {
        "name": "Nasdaq 10 (Nasdaq Bot)",
        "amount": 25000,  # 💶 250€ (en céntimos)
        "file": "NASDAQ 10.zip",
        "image": "Nasdaq.png"
    }
}

#ruta de la página principal
@app.route('/')
def index():
    return render_template('base.html',robots=robots)

# Página de pago
@app.route('/checkout/<robot_name>')
def checkout(robot_name):
    robot = robots.get(robot_name)
    if not robot:
        return "Robot no encontrado", 404

    return render_template(
        'checkout.html',
        key=os.getenv("STRIPE_PUBLISHABLE_KEY"),
        robot=robot,
        robot_name=robot_name
    )

# Procesar el pago
@app.route('/create-checkout-session/<robot_name>', methods=['POST'])
def create_checkout_session(robot_name):
    robot = robots.get(robot_name)
    if not robot:
        return "Robot no encontrado", 404

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'eur',
                'product_data': {
                    'name': robot['name'],
                },
                'unit_amount': robot['amount'],
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('success', robot_name=robot_name, _external=True),
        cancel_url=url_for('cancel', _external=True),
    )

    return redirect(session.url, code=303)

@app.route('/success/<robot_name>')
def success(robot_name):
    robot = robots.get(robot_name)
    if not robot:
        return "Robot no encontrado", 404

    # Crear token temporal de descarga (válido 5 minutos)
    token = serializer.dumps(robot['file'])
    download_url = url_for('secure_download', token=token, _external=True)

    return render_template(
        'success.html',
        robot=robot,
        download_url=download_url
    )

# Página de pago cancelado
@app.route('/cancel')
def cancel():
    return render_template('cancel.html')


# Diccionario global para tokens usados
used_tokens = set()

# Ruta segura de descarga
@app.route('/download/<token>')
def secure_download(token):
    try:
        # Verifica si el token ya se usó
        if token in used_tokens:
            return "❌ Este enlace ya ha sido usado.", 403

        # Decodifica el token
        filename = serializer.loads(token, max_age=300)  # 5 minutos
        file_path = os.path.join('downloads', filename)

        # Marca el token como usado
        used_tokens.add(token)

        return send_file(file_path, as_attachment=True, download_name=filename)

    except SignatureExpired:
        return "⚠️ Enlace expirado. Solicita uno nuevo.", 403
    except BadSignature:
        return "❌ Enlace inválido.", 403

#Corre la aplicación
if __name__ == '__main__':
    app.run(debug=True)