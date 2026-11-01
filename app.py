from flask import Flask, render_template, request, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

databd = Path(__file__).resolve().parent / "database_iot.db"

def conectar_banco():
    conexao = sqlite3.connect(databd)
    conexao.row_factory = sqlite3.Row
    return conexao

def iniciar_banco():
    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            uid TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            acesso TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """)

    conexao.commit()
    conexao.close()

#======================
@app.route("/")
def inicioSite():
    return render_template("first_page.html")

@app.route("/second_page")
def menu():
    return render_template("second_page.html")

@app.route("/historico")
def historico():
    return render_template("historico.html")

#=================================

@app.route("/api/registros")
def listar_registros():
    ultimo_id = request.args.get("ultimo_id", type=int)
    conexao = conectar_banco()
    cursor = conexao.cursor()
    if ultimo_id is None:
        cursor.execute("""
            SELECT * FROM (SELECT id, uid, acesso, data_hora FROM registros ORDER BY id DESC LIMIT 5) ORDER BY id ASC""")
    else:
        cursor.execute("""SELECT id,uid,acesso,data_hora FROM registros WHERE id > ? ORDER BY id ASC""",(ultimo_id,))
    registrosBanco = cursor.fetchall()
    conexao.close()

    return jsonify([dict(registro) for registro in registrosBanco])

#=================================

@app.route("/api/leitura", methods=['POST'])
def itens_lidos():
    conexao = conectar_banco()
    cursor = conexao.cursor()
    dados = request.get_json()
    if not dados:
        return jsonify({"status":"error","message":"Nenhum dado Json fornecido"}), 400
    uid = dados.get("uid")
    cursor.execute("SELECT uid FROM usuarios WHERE uid = ?",(uid,))
    consulta = cursor.fetchall()
    if consulta:
        acesso = "Liberado"
    else:
        acesso = "Negado"
    datahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO registros(uid, acesso, data_hora) VALUES(?,?,?)",(uid,acesso,datahora))
    conexao.commit()
    conexao.close()
    return jsonify({"uid":uid, "acesso":acesso,"data_hora":datahora}),200
    
if __name__ == "__main__":
    iniciar_banco()
    app.run(host="0.0.0.0", port=5000, debug=True)
