import os
import random
import string
import datetime
import logging
import jwt
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint

# Variables de configuración
SECRET_KEY = os.getenv('SECRET_KEY')  # Usar una variable de entorno
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.yaml'

# Configuración de logging
logging.basicConfig(
    filename='acciones_usuario.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

error_logger = logging.getLogger('error_logger')
error_logger.setLevel(logging.ERROR)
file_handler = logging.FileHandler('errores_usuario.log', encoding="UTF-8")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
error_logger.addHandler(file_handler)

# Crear la aplicación Flask
app = Flask(__name__)

# Configuración de Swagger UI
swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Pokemon API 1.0"}
)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

# Ruta para servir archivos estáticos (Swagger)
@app.route("/static/<path:filename>")
def send_file(filename):
    return send_from_directory('static', filename)

# Función para generar un token JWT
def generar_token(username):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    payload = {'username': username, 'exp': expiration}
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

# Función para verificar el token JWT
def verificar_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Función para obtener el token de los encabezados
def obtener_token():
    token = request.headers.get('Authorization')
    if not token:
        return None
    return token.split(" ")[1] if len(token.split(" ")) > 1 else None

# Función para registrar las acciones del usuario
def registrar_accion(username, accion):
    logging.info(f'{accion}', extra={'username': username})

# Función para registrar errores
def registrar_error(username, mensaje_error):
    error_logger.error(f'{mensaje_error}', extra={'username': username})

# Función auxiliar para obtener información de un Pokémon
def obtener_info_pokemon(pokemon_name):
    url = f'https://pokeapi.co/api/v2/pokemon/{pokemon_name}'
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return response.json()

# Ruta de login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    pokemon_user = os.getenv('POKEMON_USER', 'mi_usuario')
    pokemon_pass = os.getenv('POKEMON_PASS', 'mi_contraseña')

    if username == pokemon_user and password == pokemon_pass:
        token = generar_token(username)
        registrar_accion(username, 'Inicio de sesión exitoso')
        return jsonify({'message': 'Inicio de sesión exitoso', 'token': token})

    registrar_error(username, 'Error de inicio de sesión: Usuario o contraseña incorrectos')
    return jsonify({'error': 'Usuario o contraseña incorrectos'}), 400

# Ruta para las búsquedas de Pokémon (requiere JWT)
@app.route('/busqueda', methods=['POST'])
def busqueda():
    token = obtener_token()
    if not token or not verificar_token(token):
        registrar_error('Desconocido', 'Token no proporcionado o inválido en la búsqueda')
        return jsonify({'error': 'Token no proporcionado o inválido'}), 403

    username = verificar_token(token)['username']
    data = request.get_json()
    pokemon_name = data.get('pokemon_name')

    if not pokemon_name:
        registrar_error(username, 'No se ha indicado el nombre de un Pokémon')
        return jsonify({'error': 'No se ha indicado el nombre de un Pokémon'}), 400

    pokemon_info = obtener_info_pokemon(pokemon_name)
    if not pokemon_info:
        registrar_error(username, f'No se pudo encontrar el Pokémon {pokemon_name}')
        return jsonify({'error': 'No se pudo encontrar el Pokémon'}), 404

    registrar_accion(username, f'Búsqueda de Pokémon: {pokemon_name}')
    info = {'name': pokemon_info['name'], 'type': pokemon_info['types'][0]['type']['name'], 'id': pokemon_info['id']}
    return jsonify(info)

# Ruta para la ruleta de Pokémon (requiere JWT)
@app.route('/ruleta', methods=['POST'])
def ruleta():
    token = obtener_token()
    if not token or not verificar_token(token):
        registrar_error('Desconocido', 'Token no proporcionado o inválido en la ruleta')
        return jsonify({'error': 'Token no proporcionado o inválido'}), 403

    username = verificar_token(token)['username']
    data = request.get_json()
    pokemon_type = data.get('pokemon_type')

    if not pokemon_type:
        registrar_error(username, 'No se ha indicado el tipo de Pokémon')
        return jsonify({'error': 'No se ha indicado el tipo de Pokémon'}), 400

    url = f'https://pokeapi.co/api/v2/type/{pokemon_type}'
    response = requests.get(url)

    if response.status_code != 200:
        registrar_error(username, f'No se pudo obtener la información para el tipo {pokemon_type}')
        return jsonify({'error': 'No se pudo obtener la información de los Pokémon'}), 404

    pokemon_names = [item['pokemon']['name'] for item in response.json()['pokemon']]
    if not pokemon_names:
        registrar_error(username, f'No se encontraron Pokémon para el tipo {pokemon_type}')
        return jsonify({'error': 'No se encontraron Pokémon para el tipo especificado'}), 404

    pokemon_name = random.choice(pokemon_names)
    pokemon_info = obtener_info_pokemon(pokemon_name)

    if not pokemon_info:
        registrar_error(username, f'No se pudo encontrar el Pokémon {pokemon_name}')
        return jsonify({'error': 'No se pudo encontrar el Pokémon'}), 404

    registrar_accion(username, f'Ruleta de Pokémon: {pokemon_name}')
    tipos_str = ' / '.join([item['type']['name'] for item in pokemon_info['types']])
    info = {'name': pokemon_info['name'], 'types': tipos_str, 'id': pokemon_info['id']}
    return jsonify(info)

# Ruta para el Pokémon con nombre más largo (requiere JWT)
@app.route('/nombre-mas-largo', methods=['POST'])
def nombremaslargo():
    token = obtener_token()
    if not token or not verificar_token(token):
        registrar_error('Desconocido', 'Token no proporcionado o inválido en nombre más largo')
        return jsonify({'error': 'Token no proporcionado o inválido'}), 403

    username = verificar_token(token)['username']
    data = request.get_json()
    pokemon_type = data.get('pokemon_type')

    if not pokemon_type:
        registrar_error(username, 'No se ha indicado el tipo de Pokémon')
        return jsonify({'error': 'No se ha indicado el tipo de Pokémon'}), 400

    url = f'https://pokeapi.co/api/v2/type/{pokemon_type}'
    response = requests.get(url)

    if response.status_code != 200:
        registrar_error(username, f'No se pudo obtener la información para el tipo {pokemon_type}')
        return jsonify({'error': 'No se pudo obtener la información de los Pokémon'}), 404

    pokemon_names = [item['pokemon']['name'] for item in response.json()['pokemon']]
    if not pokemon_names:
        registrar_error(username, f'No se encontraron Pokémon para el tipo {pokemon_type}')
        return jsonify({'error': 'No se encontraron Pokémon para el tipo especificado'}), 404

    pokemon_name = max(pokemon_names, key=len)
    pokemon_info = obtener_info_pokemon(pokemon_name)

    if not pokemon_info:
        registrar_error(username, f'No se pudo encontrar el Pokémon {pokemon_name}')
        return jsonify({'error': 'No se pudo encontrar el Pokémon'}), 404

    registrar_accion(username, f'Nombre más largo: {pokemon_name}')
    tipos_str = ' / '.join([item['type']['name'] for item in pokemon_info['types']])
    info = {'name': pokemon_info['name'], 'types': tipos_str, 'id': pokemon_info['id']}
    return jsonify(info)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
