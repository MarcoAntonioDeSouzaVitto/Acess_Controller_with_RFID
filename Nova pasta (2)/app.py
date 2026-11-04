from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
from pathlib import Path
from datetime import datetime
import time
import os
import secrets
import socket
from functools import wraps
from flask_socketio import SocketIO, emit, join_room
ultimo_sinal = None

# Descoberta do servidor na rede local.
# O app Android envia MONITORRFID_DISCOVER por UDP/5001 e o servidor responde
# com o endereço HTTP que deve ser usado no login e no Socket.IO.
DISCOVERY_PORT = 5001
HTTP_PORT = 5000
DISCOVERY_REQUEST = b"MONITORRFID_DISCOVER"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
socketio = SocketIO(app)  # só aceita sockets da própria página (mesma origem)

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
    #cursor.execute("""
        #CREATE TABLE IF NOT EXISTS conta (
                #id INTEGER PRIMARY KEY AUTOINCREMENT,
                #nome TEXT NOT NULL,
                #senha TEXT NOT NULL
        #)
    #""")

    
    conexao.commit()
    conexao.close()
#======================
# LOGIN E PERMISSÕES
#
#  - root (admin): ROOT_USUARIO / ROOT_SENHA -> vê os acessos de todos e usa o /controle
#  - usuário cadastrado no /controle: entra com o ID dele (coluna ID da tabela do
#    controle) e, como senha, o UID do cartão. Vê só os próprios acessos
#    + as tentativas de cartão desconhecido (Negado).
def adm_server():
    """Garante que exista uma conta admin e retorna o nome realmente cadastrado."""
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
        nome_admin = "admin"
    else:
        nome_admin = admin["nome"]
        if not admin["senha"]:
            cursor.execute(
                "UPDATE usuarios SET senha = ? WHERE id = ?",
                ("1234", admin["id"])
            )
            conexao.commit()

    conexao.close()
    return nome_admin

ROOT_ADM = adm_server()

tokens_validos = {}  # token -> sessão (login pelo app Flet)
sessoes_sid = {}     # sid da conexão socket -> sessão

def igual(a, b):
    return secrets.compare_digest(str(a).encode(), str(b).encode())

def autenticar(usuario, senha):
    usuario = str(usuario or "").strip()
    senha = str(senha or "")

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
        if linha["senha"] is not None and igual(senha, linha["senha"]):
            papel = "admin" if str(linha["nome"]).strip().lower() == "admin" else "usuario"
            return {
                "id": linha["id"],
                "uid": linha["uid"],
                "nome": linha["nome"],
                "papel": papel
            }

        return None

    if usuario.isdigit():
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, nome, uid FROM usuarios WHERE id = ?",
            (int(usuario),)
        )
        linha = cursor.fetchone()
        conexao.close()
        if linha and igual(senha, linha["uid"]):
            return {
                "id": linha["id"], "uid": linha["uid"],
                "nome": linha["nome"], "papel": "usuario"
            }
    return None


def sessao_logada(auth=None):
    """Sessão do navegador (cookie) ou do app Flet (token)."""
    sessao = session.get("sessao")
    if not sessao:
        token = auth.get("token") if isinstance(auth, dict) else None
        sessao = tokens_validos.get(token)
    if sessao and sessao.get("papel") in ("usuario", "admin"):
        # Se a conta foi removida no /controle, o login deixa de valer.
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT 1 FROM usuarios WHERE id = ? AND uid = ?",
            (sessao["id"], sessao["uid"])
        )
        existe = cursor.fetchone()
        conexao.close()
        if not existe:
            return None
    return sessao

def login_obrigatorio(f):
    @wraps(f)
    def interno(*args, **kwargs):
        if not sessao_logada():
            if request.path.startswith("/api/"):
                return jsonify({"erro": "não autenticado"}), 401
            return redirect("/first_page")
        return f(*args, **kwargs)
    return interno

def somente_admin(f):
    @wraps(f)
    @login_obrigatorio
    def interno(*args, **kwargs):
        if sessao_logada()["papel"] != "admin":
            if request.path.startswith("/api/"):
                return jsonify({"erro": "sem permissão"}), 403
            return redirect("/second_page")
        return f(*args, **kwargs)
    return interno

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
    """Envia o acesso em tempo real só para quem pode vê-lo."""
    if dono_id is not None:
        # cartão de um usuário: o admin e o próprio usuário
        socketio.emit("novo_acesso", registro, to="admin")
        socketio.emit("novo_acesso", registro, to=f"conta_{dono_id}")
    elif registro["status"].lower() == "negado":
        # cartão desconhecido = tentativa de entrada: todos os logados veem
        socketio.emit("novo_acesso", registro, to="todos")
    else:
        # liberação manual do admin: só o admin
        socketio.emit("novo_acesso", registro, to="admin")
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
    session.clear()  # o link "Sair" cai aqui
    return render_template("first_page.html")

@app.route("/second_page")
@login_obrigatorio
def menu():
    return render_template("second_page.html")

@app.route("/historico")
@login_obrigatorio
def historico():
    return render_template("historico.html")

@app.route("/controle")
@somente_admin
def controledados():
    return render_template("controle.html")
@app.route("/visitante")
def visitantelogin():
    return render_template("visitante.html")

#=================================

@app.route("/api/login", methods=["POST"])
def login():
    """Usado pela first_page (cookie de sessão) e pelo app Flet (token)."""
    dados = request.get_json(silent=True) or {}
    sessao = autenticar(str(dados.get("usuario", "")).strip(), str(dados.get("senha", "")))
    
    if not sessao:
        return jsonify({"ok": False}), 401
    session["sessao"] = sessao
    session.modified = True 
    
    token = secrets.token_hex(16)
    tokens_validos[token] = sessao
    
    return jsonify({
        "ok": True, 
        "token": token, 
        "usuario": sessao["nome"], 
        "papel": sessao["papel"]
    })



#=================================

@app.route("/api/registros")
@login_obrigatorio
def listar_registros():
    ultimo_id = request.args.get("ultimo_id", type=int)
    condicao, params = filtro_visibilidade(sessao_logada())
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
    # avisa o app Flet e a second_page em tempo real
    publicar({"id": novo_id, "uid": uid, "status": acesso, "data_hora": datahora},
             consulta[0]["id"] if consulta else None)
    return jsonify({"uid":uid, "acesso":acesso,"data_hora":datahora}),200

#=================================

registros_limite = 15
@app.route("/api/historico")
@login_obrigatorio
def historicogeral():
    pagina = request.args.get("pagina", default=1, type=int)
    pagina = max(1,pagina)
    offset = (pagina -1) * registros_limite
    condicao, params = filtro_visibilidade(sessao_logada())
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
@somente_admin
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

@app.route("/adicionar_usuario", methods=["POST"])
@somente_admin
def adicionar_usuario():
    nome = request.form.get("nome", "").strip()
    senha = request.form.get("senha", "")
    uidusuario = request.form.get("uiduser", "").strip()

    if not nome or not senha or not uidusuario:
        return redirect("/controle?erro=campos")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "INSERT INTO usuarios (nome, senha, uid) VALUES (?, ?, ?)",
            (nome, senha, uidusuario)
        )
        conexao.commit()
    except sqlite3.IntegrityError:
        conexao.rollback()
        return redirect("/controle?erro=uid")
    finally:
        conexao.close()

    return redirect("/controle?sucesso=1")
#=================================

@app.route("/remover_usuario/<int:id>",methods=["POST"])
@somente_admin
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
    # visitante não está logado: só vê tentativas de cartão desconhecido
    ultimo_id = request.args.get("ultimo_id", default=0,type=int)
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("""SELECT id,uid,acesso FROM registros WHERE id > ? AND lower(acesso) = 'negado' AND 'liberado'AND uid NOT IN (SELECT uid FROM usuarios) ORDER BY id ASC""",(ultimo_id,))
    registrosBanco = cursor.fetchall()
    conexao.close()
    return jsonify([dict(registro) for registro in registrosBanco])

#=================================
# SOCKET.IO (app Flet e second_page)

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
    quem = sessao["id"] if sessao["id"] is not None else "ADMIN"
    uid = f"MANUAL-{quem}"
    datahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO registros(uid, acesso, data_hora) VALUES(?,?,?)",(uid,"Liberado",datahora))
    novo_id = cursor.lastrowid
    conexao.commit()
    conexao.close()
    publicar({"id": novo_id, "uid": uid, "status": "Liberado", "data_hora": datahora}, sessao["id"])

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
        debug=True,
        allow_unsafe_werkzeug=True
    )
