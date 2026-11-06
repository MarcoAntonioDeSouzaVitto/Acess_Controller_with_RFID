from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
import time
import os
import socket
from flask_socketio import SocketIO, emit, join_room
ultimo_sinal = None
DISCOVERY_PORT = 5001
HTTP_PORT = 5000
DISCOVERY_REQUEST = b"MONITORRFID_DISCOVER"

try:
    from zoneinfo import ZoneInfo
    FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")
except Exception:
    FUSO_BRASIL = timezone(timedelta(hours=-3))

def agora_brasil():
    """Data e hora atuais no Brasil, no mesmo formato que o banco ja usa."""
    return datetime.now(FUSO_BRASIL).strftime('%Y-%m-%d %H:%M:%S')

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)
socketio = SocketIO(app)

databd = Path(__file__).resolve().parent / "database_iot.db"

def conectar_banco():
    conexao = sqlite3.connect(databd, timeout=15)
    conexao.row_factory = sqlite3.Row
    return conexao

def iniciar_banco():
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            senha TEXT NOT NULL,
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
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas = [c["name"] for c in cursor.fetchall()]
    if "senha" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN senha TEXT NOT NULL DEFAULT ''")
        cursor.execute("UPDATE usuarios SET senha = '1234' WHERE lower(trim(nome)) = 'admin' AND senha = ''")
        cursor.execute("UPDATE usuarios SET senha = uid WHERE senha = ''")

    conexao.commit()
    conexao.close()

#======================
# LOGIN (navegador: cookie de sessão / app Flet: token)
# Cada usuário vê só os próprios acessos (+ tentativas de cartão desconhecido); o admin vê tudo.

def adm_server():
    """Garante que exista a conta admin (senha 1234)."""
    iniciar_banco()
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, nome, senha FROM usuarios WHERE lower(trim(nome)) = ? ORDER BY id LIMIT 1",
        ("admin",)
    )
    admin = cursor.fetchone()
    if admin is None:
        cursor.execute(
            "INSERT INTO usuarios (nome, senha, uid) VALUES (?, ?, ?)",
            ("admin", "1234", "ADMIN-CARD")
        )
        conexao.commit()
    elif not admin["senha"]:
        cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", ("1234", admin["id"]))
        conexao.commit()
    conexao.close()

adm_server()

tokens_validos = {}  # token -> sessão (login pelo app Flet)
sessoes_sid = {}     # sid da conexão socket -> sessão

def autenticar(usuario, senha):
    usuario = str(usuario or "").strip()
    senha = str(senha or "")

    if not usuario or not senha:
        return None

    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT id, nome, senha, uid
        FROM usuarios
        WHERE lower(trim(nome)) = lower(trim(?))
        ORDER BY id
    """, (usuario,))
    linhas = cursor.fetchall()
    conexao.close()

    for linha in linhas:
        if linha["senha"] and senha == linha["senha"]:
            papel = "admin" if str(linha["nome"]).strip().lower() == "admin" else "usuario"
            return {"id": linha["id"], "uid": linha["uid"], "nome": linha["nome"], "papel": papel}

    # login pelo ID do usuário + UID do cartão como senha
    if usuario.isdigit():
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("SELECT id, nome, uid FROM usuarios WHERE id = ?", (int(usuario),))
        linha = cursor.fetchone()
        conexao.close()
        if linha and senha == linha["uid"]:
            return {"id": linha["id"], "uid": linha["uid"], "nome": linha["nome"], "papel": "usuario"}
    return None
#======================
# FLET: histórico inicial e envio em tempo real
def sessao_logada(auth=None):
    """Sessão do navegador (cookie) ou do app Flet (token)."""
    sessao = session.get("sessao")
    if not sessao:
        token = auth.get("token") if isinstance(auth, dict) else None
        sessao = tokens_validos.get(token)
    if sessao:
        # se a conta foi removida no /controle, o login deixa de valer
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("SELECT 1 FROM usuarios WHERE id = ? AND uid = ?", (sessao["id"], sessao["uid"]))
        existe = cursor.fetchone()
        conexao.close()
        if not existe:
            return None
    return sessao

def filtro_visibilidade(sessao):
    """Condição SQL (sobre a tabela registros) do que esta sessão pode ver."""
    if sessao["papel"] == "admin":
        return "1=1", ()
    return ("(uid IN (?, ?) OR (lower(acesso) = 'negado' AND uid NOT IN (SELECT uid FROM usuarios)))",
            (sessao["uid"], f"MANUAL-{sessao['id']}"))
  
def ultimos_registros(sessao, limite=5):
    condicao, params = filtro_visibilidade(sessao)
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute(
        f"SELECT id, uid, acesso, data_hora FROM registros WHERE {condicao} ORDER BY id DESC LIMIT ?",
        params + (limite,))
    linhas = cursor.fetchall()
    conexao.close()
    # do mais recente para o mais antigo
    return [{"id": l["id"], "uid": l["uid"], "status": l["acesso"], "data_hora": l["data_hora"]} for l in linhas]

def publicar(registro, dono_id):
    """Envia o acesso em tempo real só para as salas que podem vê-lo."""
    if dono_id is not None:
        # cartão de um usuário: o admin e o próprio usuário
        socketio.emit("novo_acesso", registro, to="admin")
        socketio.emit("novo_acesso", registro, to=f"conta_{dono_id}")
    else:
        # cartão desconhecido = tentativa de entrada: todos os logados veem
        socketio.emit("novo_acesso", registro, to="todos")
#======================

@app.route("/api/esp/status", methods=["GET", "POST"])
def status_esp():
    global ultimo_sinal
    if request.method == "POST":
        ultimo_sinal = time.time()
        return jsonify({"mensagem": "Heartbeat recebido"}), 200
    if ultimo_sinal is None:
        return jsonify({"online": False})
    tempo_decorrido = time.time() - ultimo_sinal
    online = tempo_decorrido <= 15
    return jsonify({"online": online, "ultima_comunicacao": round(tempo_decorrido, 1)})
#======================
@app.route("/")
def pagina_inicial():
    return redirect("/first_page")

@app.route("/first_page")
def inicioSite():
    return render_template("first_page.html")

@app.route("/second_page")
def menu():
    return render_template("second_page.html")

@app.route("/historico")
def historico():
    return render_template("historico.html")
@app.route("/controle")
def controledados():
    return render_template("controle.html")
@app.route("/visitante")
def visitantelogin():
    return render_template("visitante.html")
#=================================
@app.route("/api/login", methods=["POST"])
def login():
    """Usado pela first_page e pelo app Flet."""
    dados = request.get_json(silent=True) or {}
    sessao = autenticar(dados.get("usuario", ""), dados.get("senha", ""))

    if not sessao:
        return jsonify({"ok": False}), 401
    session["sessao"] = sessao
    session.modified = True

    token = os.urandom(16).hex()
    tokens_validos[token] = sessao

    return jsonify({
        "ok": True,
        "token": token,
        "usuario": sessao["nome"],
        "papel": sessao["papel"]
    })
#=================================
@app.route("/api/registros")
def listar_registros():
    sessao = sessao_logada()
    if not sessao:
        return jsonify({"erro": "não autenticado"}), 401
    ultimo_id = request.args.get("ultimo_id", type=int)
    condicao, params = filtro_visibilidade(sessao)
    conexao = conectar_banco()
    cursor = conexao.cursor()
    if ultimo_id is None:
        cursor.execute(f"""
            SELECT * FROM (SELECT id, uid, acesso, data_hora FROM registros WHERE {condicao} ORDER BY id DESC LIMIT 5) ORDER BY id ASC""", params)
    else:
        cursor.execute(f"""SELECT id,uid,acesso,data_hora FROM registros WHERE id > ? AND {condicao} ORDER BY id ASC""",(ultimo_id,) + params)
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
    cursor.execute("SELECT id, uid FROM usuarios WHERE uid = ?",(uid,))
    consulta = cursor.fetchall()
    if consulta:
        acesso = "Liberado"
    else:
        acesso = "Negado"
    datahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO registros(uid, acesso, data_hora) VALUES(?,?,?)",(uid,acesso,datahora))
    novo_id = cursor.lastrowid
    conexao.commit()
    conexao.close()
    publicar({"id": novo_id, "uid": uid, "status": acesso, "data_hora": datahora},
             consulta[0]["id"] if consulta else None)
    return jsonify({"uid":uid, "acesso":acesso,"data_hora":datahora}),200
#=================================
registros_limite = 15
@app.route("/api/historico")
def historicogeral():
    pagina = request.args.get("pagina", default=1, type=int)
    pagina = max(1,pagina)
    offset = (pagina -1) * registros_limite
    sessao = sessao_logada()
    if not sessao:
        return jsonify({"erro": "não autenticado"}), 401
    condicao, params = filtro_visibilidade(sessao)
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM registros WHERE {condicao};", params)
    total_registros = cursor.fetchone()[0]
    total_paginas = max(1, (total_registros + registros_limite - 1) // registros_limite)
    cursor.execute(f"SELECT id, uid, acesso, data_hora FROM registros WHERE {condicao} ORDER BY id desc LIMIT ? OFFSET ?;",params + (registros_limite,offset))
    dados = [dict(linha) for linha in cursor.fetchall()]
    conexao.close()
    return jsonify({
        "registros": dados,
        "pagina_atual": pagina,
        "total_paginas": total_paginas,
        "total_registros": total_registros
    })
#=================================
registrosUser_limite = 8
@app.route("/api/controle")
def usuariosRegistrados():
    pagina = request.args.get("pagina", default=1, type=int)
    pagina = max(1,pagina)
    offset = (pagina -1) * registrosUser_limite
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios;")
    total_registrosUSER = cursor.fetchone()[0]
    total_paginas = max(1, (total_registrosUSER + registrosUser_limite - 1) // registrosUser_limite)
    cursor.execute("SELECT id, nome, uid FROM usuarios ORDER BY id asc LIMIT ? OFFSET ?;",(registrosUser_limite,offset))
    dados = [dict(linha) for linha in cursor.fetchall()]
    conexao.close()
    return jsonify({
        "registros": dados,
        "pagina_atual": pagina,
        "total_paginas": total_paginas,
        "total_registros": total_registrosUSER
    })
#=================================
@app.route("/adicionar_usuario",methods=["POST"])
def adicionar_usuario():
    nome = request.form["nome"]
    uidusuario = request.form["uiduser"]
    senha = request.form.get("senha") or uidusuario
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("""INSERT INTO usuarios(nome,senha,uid) VALUES(?,?,?)""",(nome,senha,uidusuario))
    conexao.commit()
    conexao.close()
    return redirect("/controle")
#=================================
@app.route("/remover_usuario/<int:id>",methods=["POST"])
def remover_usuario(id):
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?",(id,))
    conexao.commit()
    conexao.close()
    for t in [t for t, s in tokens_validos.items() if s["id"] == id]:
        del tokens_validos[t]
    return redirect("/controle")
#=================================
@app.route("/api/visitante")
def listarParaVistiante():
    ultimo_id = request.args.get("ultimo_id", default=0,type=int)
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("""SELECT id,uid,acesso FROM registros WHERE id > ? ORDER BY id ASC""",(ultimo_id,))
    registrosBanco = cursor.fetchall()
    conexao.close()
    return jsonify([dict(registro) for registro in registrosBanco])
#=================================
@socketio.on("connect")
def ao_conectar(auth=None):
    sessao = sessao_logada(auth)
    if not sessao:
        return False  # recusa quem não está logado
    sessoes_sid[request.sid] = sessao
    join_room("todos")
    join_room("admin" if sessao["papel"] == "admin" else f"conta_{sessao['id']}")
    emit("historico", ultimos_registros(sessao))

@socketio.on("disconnect")
def ao_desconectar(*args):
    sessoes_sid.pop(request.sid, None)

@socketio.on("liberar_acesso")
def liberar_acesso(dados=None):
    """Botão 'Liberar acesso' do app Flet."""
    sessao = sessoes_sid.get(request.sid)
    if not sessao:
        emit("erro", "Não autorizado. Faça login novamente.")
        return
    uid = f"MANUAL-{sessao['id']}"
    datahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO registros(uid, acesso, data_hora) VALUES(?,?,?)",(uid,"Liberado",datahora))
    novo_id = cursor.lastrowid
    conexao.commit()
    conexao.close()
    publicar({"id": novo_id, "uid": uid, "status": "Liberado", "data_hora": datahora}, sessao["id"])
#=================================
# DESCOBERTA NA REDE LOCAL (app Flet)

def descobrir_ip_local(destino="8.8.8.8"):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((destino, 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass

    try:
        candidatos = socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in candidatos:
            if "." in ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    return None

def servidor_descoberta():
    """Responde a broadcasts UDP com o endereço do servidor HTTP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", DISCOVERY_PORT))
    print(f"Descoberta LAN ativa em UDP/{DISCOVERY_PORT}")

    while True:
        try:
            dados, endereco = sock.recvfrom(1024)
            if dados.strip() != DISCOVERY_REQUEST:
                continue
            ip = descobrir_ip_local(endereco[0])
            if ip:
                resposta = f"MONITORRFID_SERVER|{ip}|{HTTP_PORT}".encode("utf-8")
                sock.sendto(resposta, endereco)
                print(f"Discovery: {endereco[0]} -> {ip}:{HTTP_PORT}")
        except OSError as erro:
            print(f"Discovery UDP encerrado: {erro}")
            break
        except Exception as erro:
            print(f"Erro no discovery UDP: {erro}")

if __name__ == "__main__":
    import threading
    print(f"Banco SQLite em uso: {databd}")
    iniciar_banco()
    
    threading.Thread(target=servidor_descoberta, daemon=True).start()

    socketio.run(
        app,
        host="0.0.0.0",
        port=HTTP_PORT,
        debug=False,
        allow_unsafe_werkzeug=True
    )
