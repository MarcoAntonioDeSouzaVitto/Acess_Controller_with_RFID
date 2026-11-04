import asyncio
import threading
import socket
import flet as ft
import requests
import time
import socketio

# O app tenta descobrir automaticamente o servidor na mesma rede Wi-Fi.
# Se a descoberta falhar, SERVER_URL pode ser preenchido manualmente como fallback.
SERVER_URL = ""
SERVER_PORT = 5000
DISCOVERY_PORT = 5001
DISCOVERY_REQUEST = b"MONITORRFID_DISCOVER"
DISCOVERY_RESPONSE_PREFIX = "MONITORRFID_SERVER|"


def _destinos_broadcast():
    """Broadcast geral + broadcast da sub-rede (ex.: 192.168.0.255).

    No Android o 255.255.255.255 costuma ser descartado em alguns celulares e
    roteadores; o broadcast da sub-rede costuma passar.
    """
    destinos = ["255.255.255.255"]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # UDP connect não envia nada; só descobre qual interface está em uso
            s.connect(("10.255.255.255", 1))
            ip_local = s.getsockname()[0]
        finally:
            s.close()
        partes = ip_local.split(".")
        if len(partes) == 4 and ip_local != "0.0.0.0":
            destinos.append(".".join(partes[:3] + ["255"]))
    except OSError:
        pass
    return destinos


def descobrir_servidor(tentativas=5, espera=1.0):
    """Procura o app.py por UDP broadcast na rede local, com várias tentativas."""
    global SERVER_URL

    if SERVER_URL:
        return SERVER_URL

    destinos = _destinos_broadcast()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        for _ in range(tentativas):
            for destino in destinos:
                try:
                    sock.sendto(DISCOVERY_REQUEST, (destino, DISCOVERY_PORT))
                except OSError:
                    pass

            fim = time.monotonic() + espera
            while True:
                restante = fim - time.monotonic()
                if restante <= 0:
                    break
                sock.settimeout(restante)
                try:
                    dados, _ = sock.recvfrom(1024)
                except OSError:  # timeout: manda o broadcast de novo
                    break

                texto = dados.decode("utf-8", errors="ignore").strip()
                if not texto.startswith(DISCOVERY_RESPONSE_PREFIX):
                    continue

                partes = texto.split("|")
                if len(partes) != 3:
                    continue

                ip = partes[1].strip()
                try:
                    porta = int(partes[2])
                except ValueError:
                    porta = SERVER_PORT

                if ip:
                    SERVER_URL = f"http://{ip}:{porta}"
                    return SERVER_URL
    finally:
        sock.close()

    return ""


def esquecer_servidor():
    """Apaga o IP guardado, para a próxima chamada descobrir de novo."""
    global SERVER_URL
    SERVER_URL = ""



def main(page: ft.Page):
    page.title = "MonitorRFID"
    page.bgcolor = "#0E0E55"
    page.padding = 0
    page.spacing = 0
    page.window.width = 350
    page.window.height = 700
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    sio = socketio.Client(reconnection=True)

    # estado compartilhado entre as telas e os eventos do socket
    estado = {
        "token": None,
        "historico": [],      # lista de dicts {uid, status, data_hora}
        "lista": None,        # ft.ListView da tela home
        "txt_conexao": None,  # ft.Text com o status da conexão
    }

 
    def mostrar_aviso(texto, cor):
        snack_bar = ft.SnackBar(
            content=ft.Text(texto, color="#dedee7"),
            bgcolor=cor,
            duration=1500,
        )
        page.show_dialog(snack_bar)
        page.update()

    def linha_acesso(uid, status, dth):
        liberado = str(status).lower() == "liberado"
        cor_status = "#5ed97c" if liberado else "#ff6b6b"
        
        # Trata o UID para exibição amigável caso seja uma liberação manual do admin
        uid_exibicao = "Painel Admin" if "USUARIO" in str(uid) else uid
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(uid_exibicao, color="#dedee7", expand=1, size=12, text_align=ft.TextAlign.CENTER),
                    ft.Text("Liberado" if liberado else "Negado", color=cor_status, expand=2, size=12, text_align=ft.TextAlign.CENTER),
                    ft.Text(dth, color="#dedee7", expand=1, size=12, text_align=ft.TextAlign.CENTER),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#263A6D",
            border_radius=3,
            padding=3,
            margin=3,
        )


    def renderizar_lista():
        lista = estado["lista"]
        if lista is None:
            return
        lista.controls.clear()
        for r in estado["historico"]:
            lista.controls.append(linha_acesso(r["uid"], r["status"], r["data_hora"]))
        page.update()

    def atualizar_conexao(conectado):
        txt = estado["txt_conexao"]
        if txt is None:
            return
        txt.value = "Servidor: conectado" if conectado else "Servidor: desconectado"
        txt.color = "#2e7d32" if conectado else "#c62828"
        page.update()

    # Socket.IO (cliente)
   
    @sio.on("connect")
    def ao_conectar():
        atualizar_conexao(True)

    @sio.on("disconnect")
    def ao_desconectar():
        atualizar_conexao(False)

    @sio.on("historico")
    def ao_receber_historico(lista):
        estado["historico"] = list(lista)[:5]
        renderizar_lista()

    @sio.on("novo_acesso")
    def ao_novo_acesso(registro):
        estado["historico"].insert(0, registro)
        estado["historico"] = estado["historico"][:5]
        renderizar_lista()

    @sio.on("erro")
    def ao_erro(mensagem):
        mostrar_aviso(str(mensagem), "red")

    def conectar_servidor():
        if sio.connected:
            return

        def _conectar():
            global SERVER_URL
            try:
                if not SERVER_URL:
                    SERVER_URL = descobrir_servidor()

                if not SERVER_URL:
                    atualizar_conexao(False)
                    return

                sio.connect(
                    SERVER_URL,
                    auth={"token": estado["token"]},
                    wait_timeout=5,
                )
            except Exception:
                atualizar_conexao(False)

        threading.Thread(target=_conectar, daemon=True).start()

    def liberar_acesso(e=None):
        if not sio.connected:
            mostrar_aviso("Sem conexão com o servidor. Tentando reconectar...", "red")
            conectar_servidor()
            return
        # o servidor registra e devolve "novo_acesso" para o app E para o front web
        sio.emit("liberar_acesso")

    def sair(e=None):
        if sio.connected:
            sio.disconnect()
        estado["token"] = None
        page.run_task(page.push_route, "/tela_login")

    # ------------------------------------------------------------------
    # telas
    # ------------------------------------------------------------------
    def tela_home(e=None):
        txt_painel = ft.Text(
            "Painel de Entrada",
            size=20,
            weight="bold",
            color="#0E0E55",
        )
        txt_conexao = ft.Text("Servidor: desconectado", size=12, color="#c62828")
        estado["txt_conexao"] = txt_conexao

        txt_registro = ft.Container(
            ft.Text(
                "Ultimos Acessos",
                size=15,
                weight="bold",
                color="#dedee7",
            ),
            alignment=ft.Alignment.CENTER,
        )
        t_uid = ft.Text("UID", expand=1, text_align=ft.TextAlign.CENTER, size=14, weight="bold", color="#dedee7")
        t_status = ft.Text("Status", expand=2, text_align=ft.TextAlign.CENTER, size=14, weight="bold", color="#dedee7")
        t_dth = ft.Text("Data Hora", expand=1, text_align=ft.TextAlign.CENTER, size=14, weight="bold", color="#dedee7")

        title_painel = ft.Container(
            content=ft.Column(
                [txt_painel, txt_conexao],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            alignment=ft.Alignment.CENTER,
            padding=40,
        )

        linha_principal = ft.Container(
            content=ft.Row(
                controls=[t_uid, t_status, t_dth],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            bgcolor="#263A6D",
            border_radius=3,
            padding=3,
        )

        btn_liberar = ft.Container(
            ft.Button(
                on_click=liberar_acesso,
                content="Liberar acesso",
                icon=ft.Icons.LOCK_OPEN_SHARP,
                style=ft.ButtonStyle(
                    side=ft.BorderSide(width=1, color="#CCCFD8"),
                    shape=ft.RoundedRectangleBorder(radius=5),
                ),
                width=310,
                height=50,
                bgcolor="#e5e5f0",
                color="#529d65",
            ),
            alignment=ft.Alignment.CENTER,
        )
        btn_voltar = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color="#263A6D",
                    on_click=sair,
                )
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        lista_dados = ft.ListView(padding=0, spacing=0)
        estado["lista"] = lista_dados
        for r in estado["historico"]:
            lista_dados.controls.append(linha_acesso(r["uid"], r["status"], r["data_hora"]))

        painel_fundo = ft.Container(
            content=ft.Column(
                controls=[txt_registro, linha_principal, lista_dados],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment.TOP_CENTER,
            blur=ft.Blur(sigma_x=10, sigma_y=10, tile_mode=ft.BlurTileMode.MIRROR),
            bgcolor="#0E3155",
            margin=1,
            padding=5,
            border_radius=5,
            width=320,
            height=330,
        )

        page.views.append(
            ft.View(
                route="/tela_home",
                controls=[title_painel, painel_fundo, btn_liberar, btn_voltar],
                bgcolor="#ABDCDC",
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                vertical_alignment=ft.MainAxisAlignment.CENTER,
            )
        )

        # entra na sala do servidor assim que a tela abre
        if sio.connected:
            atualizar_conexao(True)
        else:
            conectar_servidor()

    def tela_login(e=None):
        async def validacao_de_campo():
            if not (campo_email.value and campo_senha.value):
                mostrar_aviso("Preencha todos os campos!", "red")
                return

            servidor = await asyncio.to_thread(descobrir_servidor)
            if not servidor:
                mostrar_aviso("Servidor não encontrado na rede Wi-Fi", "red")
                return

            try:
                # requests é bloqueante, então roda em outra thread
                resp = await asyncio.to_thread(
                    requests.post,
                    f"{servidor}/api/login",
                    json={"usuario": campo_email.value, "senha": campo_senha.value},
                    timeout=5,
                )
            except requests.RequestException:
                mostrar_aviso("Não foi possível conectar ao servidor", "red")
                return

            if resp.status_code == 200:
                estado["token"] = resp.json().get("token")
                mostrar_aviso("Login realizado com sucesso!", "green")
                await asyncio.sleep(1)
                
                page.run_task(page.push_route, "/tela_home")
            else:
                mostrar_aviso("Usuário ou senha incorretos!", "red")

        campo_email = ft.TextField(
            hint_text="Insira seu nome de usuario",
            hint_style=ft.TextStyle(size=10),
            text_align=ft.TextAlign.LEFT,
            color="#090909",
            bgcolor="#f0f0fc",
            width=225,
            cursor_height=20,
            height=38,
            border=ft.OutlineInputBorder(
                border_radius=ft.BorderRadius.all(20),
                side=ft.BorderSide(color="#f0f0fc"),
            ),
        )

        campo_senha = ft.TextField(
            hint_text="Insira sua senha",
            text_align=ft.TextAlign.LEFT,
            password=True,
            color="#090909",
            can_reveal_password=True,
            bgcolor="#f0f0fc",
            hint_style=ft.TextStyle(size=10),
            width=225,
            cursor_height=20,
            height=38,
            border=ft.OutlineInputBorder(
                border_radius=ft.BorderRadius.all(20),
                side=ft.BorderSide(color="#f0f0fc"),
            ),
        )
        painel_login = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("MonitorRFID", size=30, weight="bold", color="#020230"),
                    ft.Container(height=15),
                    ft.Image(src="icons/logo_trans.png", width=65, height=65),
                    ft.Container(height=20),
                    campo_email,
                    campo_senha,
                    ft.Container(height=10),
                    ft.Button(
                        content="Fazer Login",
                        on_click=validacao_de_campo,
                        bgcolor="#f0f0fc",
                        color="#030345",
                        width=150,
                        height=35,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            ),
            width=300,
            height=400,
            padding=30,
            border_radius=12,
            blur=ft.Blur(sigma_x=10, sigma_y=10, tile_mode=ft.BlurTileMode.MIRROR),
            bgcolor="#43F0FDFF",
            alignment=ft.Alignment.CENTER,
        )

        page.views.append(
            ft.View(
                route="/tela_login",
                controls=[painel_login],
                bgcolor="#ABDCDC",
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    def troca_tela():
        page.views.clear()
        if page.route == "/tela_login":
            tela_login()
        elif page.route == "/tela_home":
            tela_home()
        page.update()

    page.on_route_change = lambda: troca_tela()
    page.run_task(page.push_route, "/tela_login")


ft.run(main)
