import os
import random
import pymysql
from flask import Flask, request, jsonify

app = Flask(__name__)

# Credenciales desde variables de entorno (corrige B105)
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "legacydb")

debug_mode = os.getenv("DEBUG") == "True"


def get_connection():
    """Centraliza la conexion a la BD para no repetir codigo en cada ruta."""
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)


@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "API Segura"})


@app.route("/buscar", methods=["GET"])
def buscar():
    usuario_id = request.args.get("id", "1")
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # Consulta parametrizada (corrige B608)
            cursor.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
            resultado = cursor.fetchall()
        conn.close()
        return jsonify({"id": usuario_id, "resultado": resultado})
    except Exception as e:
        return jsonify({"id": usuario_id, "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    try:
        if random.random() < 0.3:  # nosec B311 - simulacion de fallo, no uso criptografico
            resultado = 1 / 0
        return jsonify({"status": "ok"})
    except ZeroDivisionError:
        return jsonify({"status": "fallo intermitente simulado"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5050))
    # host 0.0.0.0 justificado: necesario para exponer el puerto dentro del contenedor Docker
    app.run(host="0.0.0.0", port=port, debug=debug_mode)  # nosec B104
