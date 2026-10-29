from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
def iniciar_banco():    
    conexao = sqlite3.connect('database_iot.db')
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            acesso TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tag TEXT NOT NULL
        )
    """)
    conexao.commit()
    conexao.close()
#=======================================================================
app = Flask(__name__)
CORS(app)
iniciar_banco()

@app.route('/api/leitura',methods=['POST'])
def processarLEitura():
    dados = request.get_json()
    uidRFID = dados.get("uid")
    conexao = sqlite3.connect('database_iot.db')
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE tag = ?",(uidRFID,))
    usuario = cursor.fetchone()

    if usuario:
        status = "liberado"
    else:
        status = "negado"
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO registros(uid,acesso,data_hora) VALUES (?,?,?)", (uidRFID,status,data_atual))
    conexao.commit()
    conexao.close()
    return jsonify({"status": status, "uid": uidRFID)

#=========================================================================

if __name__  == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
