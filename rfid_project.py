import sqlite3
from datetime import datetime
import serial
import time
import customtkinter as ctk
import threading
import os
#banco = "database_iot.db"
#os.remove(banco)
ctk.set_appearance_mode("dark")
janela = ctk.CTk()
janela.geometry("1200x700")
janela.resizable(False, False)
janela.title("Sistema de Acesso - RFID")
janela.config(background="#13161F")

situacao_var = ctk.StringVar(value="Verificando...")

porta_arduino = "COM11"
baud_rate = 9600

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

def carregar_tags():
    with sqlite3.connect("database_iot.db") as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT tag FROM usuarios")
        return {
            linha[0].strip().upper()
            for linha in cursor.fetchall()
            if linha[0]
        }
        
def loop_leitura_rfid():
    global registro_primeiro
    iniciar_banco()
    arduino = None
    conexao = sqlite3.connect("database_iot.db")
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT * FROM registros ORDER BY id DESC LIMIT 1;")
        registro_primeiro = cursor.fetchone()
    finally:
        conexao.close()
    while True:
        if arduino is None:
            try:
                arduino = serial.Serial(port=porta_arduino, baudrate=baud_rate, timeout=1)
                time.sleep(2)
                print(f"Conectado à porta {porta_arduino}")
                situacao_var.set("Conectado ●")
            except Exception as erro:
                print(f"Erro ao conectar ao Arduino: {erro}")
                situacao_var.set("Não Conectado ●")
                time.sleep(2)
                continue

        try:
            if arduino.in_waiting > 0:
                raw_bytes = arduino.readline()
                dados_lidos = raw_bytes.decode('utf-8', errors='ignore').strip().upper()
                if dados_lidos:
                    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    if dados_lidos in carregar_tags():
                        acesso = "ACESSO LIBERADO"
                        arduino.write(b'1')
                    else:
                        acesso = "ACESSO RECUSADO"
                        arduino.write(b'0')

                    with sqlite3.connect('database_iot.db') as conexao:
                        cursor = conexao.cursor()
                        cursor.execute(
                            "INSERT INTO registros (uid, acesso, data_hora) VALUES(?,?,?)",
                            (dados_lidos, acesso, agora)
                        )
                        conexao.commit()
            else:
                time.sleep(0.05)
                
        except (serial.SerialException, serial.SerialTimeoutException):
            if arduino:
                try:
                    arduino.close()
                except Exception:
                    pass
            arduino = None
            situacao_var.set("Não Conectado ●")

thread_rfid = threading.Thread(target=loop_leitura_rfid, daemon=True)
thread_rfid.start()

    

# ---------------------- Interface Gráfica ----------------------

def tela_login():
    global timer_rfid, timer_tabela, timer_status, registro_primeiro
    cancelar_timers()
    for elemento in janela.winfo_children():
        elemento.destroy()

    frame_menu = ctk.CTkFrame(janela, fg_color="#1c1f28")
    frame_menu.place(relx=0.05, rely=0.5, relwidth=0.16, relheight=1, anchor="center")


    ctk.CTkLabel(janela, text="Painel de Monitoramento", font=("Arial", 24, "bold"), bg_color="#0f1123").place(relx=0.56, rely=0.045, anchor="center")

    historico = ctk.CTkButton(janela, text="🕒 Histórico", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_historico)
    historico.place(relx=0.064, rely=0.24, anchor="center", relwidth=0.12, relheight=0.07)

    dashboard = ctk.CTkButton(janela, text="🪟 Painel", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_login)
    dashboard.place(relx=0.064, rely=0.15, anchor="center", relwidth=0.12, relheight=0.07)

    adm = ctk.CTkButton(janela, text="🔒 Admin",font=("Arial", 18, "bold"),corner_radius=10,
                        hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=admin_page)
    adm.place(relx=0.064, rely=0.9, anchor="center", relwidth=0.12, relheight=0.07)

    status_label = ctk.CTkLabel(janela, text="Status de Conexão do Arduino: ", bg_color="#0f1123", font=("Arial", 20, "bold"))
    status_label.place(relx=0.50, rely=0.125, anchor="center")

    situacao_label = ctk.CTkLabel(janela, textvariable=situacao_var, bg_color="#0f1123", font=("Arial", 20, "bold"))
    situacao_label.place(relx=0.69, rely=0.126, anchor="center")

    def atualizar_cor_status():
        try:
            if situacao_var.get() == "Conectado ●":
                situacao_label.configure(text_color="#00ff1e")
            else:
                situacao_label.configure(text_color="red")
            global timer_status
            timer_status = janela.after(500, atualizar_cor_status)
        except Exception:
            pass
    atualizar_cor_status()

    screen = ctk.CTkFrame(janela, fg_color="#5ed97c", corner_radius=25, bg_color="#0f1123")
    screen.place(relx=0.56, rely=0.34, relwidth=0.52, relheight=0.32, anchor="center")

    registros = ctk.CTkFrame(janela, fg_color="#1b1e27", corner_radius=25, bg_color="#0f1123")
    registros.place(relx=0.56, rely=0.75, relwidth=0.52, relheight=0.36, anchor="center")

    frame_registro = ctk.CTkFrame(janela, fg_color="#262a35", bg_color="#0f1123")
    frame_registro.place(relx=0.56, rely=0.585, relwidth=0.52, relheight=0.07, anchor="center")

    texto_registros = ctk.CTkLabel(janela,text="UID                  Status                        Tempo",font=("Arial", 24),bg_color="#262a35")
    texto_registros.place(relx=0.555, rely=0.585, anchor="center")

    acess_label = ctk.CTkLabel(janela, text ="", bg_color="#5ed97c", text_color="black", font=("arial",22))
    acess_label.place(relx=0.455, rely=0.455, anchor="center")

    acess_status_label = ctk.CTkLabel(janela,text="", bg_color="#5ed97c", text_color="black", font=("arial",45,"bold"))
    acess_status_label.place(relx=0.56, rely=0.30, anchor="center")

    acess_hour = ctk.CTkLabel(janela,text="", bg_color="#5ed97c", text_color="black", font=("arial",22))
    acess_hour.place(relx=0.71, rely=0.455, anchor="center")

    table_acess = ctk.CTkLabel(janela,text="", bg_color="#1b1e27", text_color="white", font=("Consolas",20), justify="left")
    table_acess.place(relx=0.56, rely=0.775, anchor="center")

    frame_div1 = ctk.CTkFrame(janela, bg_color="#2c2f3a")
    frame_div1.place(relx=0.44, rely=0.762, relwidth=0.001, relheight=0.334, anchor="center")
    frame_div2 = ctk.CTkFrame(janela, bg_color="#2c2f3a")
    frame_div2.place(relx=0.6125, rely=0.762, relwidth=0.001, relheight=0.334, anchor="center")

    ctk.CTkFrame(janela, bg_color="#2c2f3a").place(relx=0.5599, rely=0.69, relwidth=0.52, relheight=0.001, anchor="center")
    ctk.CTkFrame(janela, bg_color="#2c2f3a").place(relx=0.5599, rely=0.75, relwidth=0.52, relheight=0.001, anchor="center")
    ctk.CTkFrame(janela, bg_color="#2c2f3a").place(relx=0.5599, rely=0.807, relwidth=0.52, relheight=0.001, anchor="center")
    ctk.CTkFrame(janela, bg_color="#2c2f3a").place(relx=0.5599, rely=0.864, relwidth=0.52, relheight=0.001, anchor="center")

    def atualizar_rfid():
        try:
            global timer_rfid
            with sqlite3.connect("database_iot.db") as conexao:
                cursor = conexao.cursor()
                cursor.execute("SELECT uid,acesso,data_hora FROM registros ORDER BY id DESC LIMIT 1;")
                ultimo = cursor.fetchone()

            if ultimo:
                acess_label.configure(text=str(f"UID do cartão: {ultimo[0]}"))
                acess_status_label.configure(text=str(f"{ultimo[1]}"))
                acess_hour.configure(text=str(f"{ultimo[2]}"))

                if ultimo[1] == "ACESSO RECUSADO":
                    screen.configure(fg_color="#d34545")
                    acess_label.configure(bg_color="#d34545")
                    acess_status_label.configure(bg_color="#d34545")
                    acess_hour.configure(bg_color="#d34545")
                if ultimo[1] == "ACESSO LIBERADO":
                    screen.configure(fg_color="#64db66")
                    acess_label.configure(bg_color="#64db66")
                    acess_status_label.configure(bg_color="#64db66")
                    acess_hour.configure(bg_color="#64db66")
            timer_rfid = janela.after(1000, atualizar_rfid)
        except Exception:
            pass

    def atualizar_tabela():
        try:
            global  timer_tabela
            with sqlite3.connect("database_iot.db") as conexao:
                cursor = conexao.cursor()
                cursor.execute("SELECT uid,acesso,data_hora FROM registros ORDER BY id DESC LIMIT 5;")
                funcio = cursor.fetchall()
            if funcio:
                texto = ""
                for linha in funcio:
                    texto += f"{str(linha[0]):<12}   {str(linha[1]):<11}   {str(linha[2]):<19}\n\n"
                table_acess.configure(text=texto.strip())
            timer_tabela = janela.after(1000, atualizar_tabela)    
        except Exception:
            pass
    atualizar_rfid()
    atualizar_tabela()

#-------------------------------------------------------------------
timer_rfid = None
timer_tabela = None
timer_status = None
def cancelar_timers():
    global timer_rfid, timer_tabela, timer_status
    if timer_rfid: janela.after_cancel(timer_rfid); timer_rfid = None
    if timer_tabela: janela.after_cancel(timer_tabela); timer_tabela = None
    if timer_status: janela.after_cancel(timer_status); timer_status = None
pagina = 1
registros_pp = 30
def guia_pagina(pagina):
    offset = (pagina - 1) * registros_pp
    with sqlite3.connect("database_iot.db") as conexao:
        cursor = conexao.cursor()
        cursor.execute("SELECT COUNT(*) FROM registros;")
        total_reg = cursor.fetchone()[0]
        total_pag = max(1, (total_reg + registros_pp - 1) // registros_pp)
        cursor.execute("""SELECT uid, acesso, data_hora FROM registros ORDER BY id desc LIMIT ? OFFSET ?;""",(registros_pp,offset))
        registros = cursor.fetchall()
        return registros, total_pag,total_reg
    
def tela_historico():
    for elemento in janela.winfo_children():
        elemento.destroy()

    global pagina
    pagina = 1
    cancelar_timers()

    frame_menu = ctk.CTkFrame(janela, fg_color="#1c1f28")
    frame_menu.place(relx=0.05, rely=0.5, relwidth=0.16, relheight=1, anchor="center")

    ctk.CTkLabel(janela, text="Histórico de Acesso & Relatórios", font=("Arial", 24, "bold"), bg_color="#0f1123").place(relx=0.32, rely=0.06, anchor="center")

    historico = ctk.CTkButton(janela, text="🕒 Histórico", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_historico)
    historico.place(relx=0.064, rely=0.24, anchor="center", relwidth=0.12, relheight=0.07)

    dashboard = ctk.CTkButton(janela, text="🪟 Painel", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_login)
    dashboard.place(relx=0.064, rely=0.15, anchor="center", relwidth=0.12, relheight=0.07)

    adm = ctk.CTkButton(janela, text="🔒 Admin",font=("Arial", 18, "bold"),corner_radius=10,
                        hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=admin_page)
    adm.place(relx=0.064, rely=0.9, anchor="center", relwidth=0.12, relheight=0.07)

    frame_tabela = ctk.CTkFrame(janela, fg_color="#1b1e27", corner_radius=15)
    frame_tabela.place(relx=0.58, rely=0.50, relwidth=0.78, relheight=0.78, anchor="center")
    
    texto_historico = ctk.CTkTextbox(frame_tabela, font=("Consolas", 20), fg_color="#1c1f28", text_color="white", activate_scrollbars=True)
    texto_historico.place(relx=0.05, rely=0.02, relwidth=0.96, relheight=0.88)

    label_status_pagina = ctk.CTkLabel(janela, text="Página 1 de 1", font=("Arial", 16, "bold"), bg_color="#0f1123")
    label_status_pagina.place(relx=0.58, rely=0.92, anchor="center")

    def carregar_pagina():
            global pagina
            
            registros, total_pag, total_reg = guia_pagina(pagina)
            
            texto_historico.configure(state="normal")
            texto_historico.delete("1.0", "end")
            
            if registros:
                cabecalho = f"{'UID':<25} | {'STATUS':<20} | {'DATA / HORA':<20}\n"
                divisoria = "=" * 70 + "\n"
                texto_historico.insert("end", cabecalho + divisoria)
                
                for reg in registros:
                    linha = f"{reg[0]:<25} | {reg[1]:<20} | {reg[2]:<20}\n"
                    texto_historico.insert("end", linha)
            else:
                texto_historico.insert("end", "Nenhum registro cadastrado no banco de dados.")

            texto_historico.configure(state="disabled")

            label_status_pagina.configure(text=f"Página {pagina} de {total_pag}  (Total: {total_reg} registros)")

            btn_anterior.configure(state="normal" if pagina > 1 else "disabled")
            
            btn_proxima.configure(state="normal" if pagina < total_pag else "disabled")

    def proxima_pagina():
            global pagina
            pagina += 1
            carregar_pagina()

    def pagina_anterior():
            global pagina
            if pagina > 1:
                pagina -= 1
                carregar_pagina()

    btn_anterior = ctk.CTkButton(janela, text="◄ Página Anterior", font=("Arial", 14, "bold"),command=pagina_anterior, width=160, height=35)
    btn_anterior.place(relx=0.40, rely=0.92, anchor="center")

    btn_proxima = ctk.CTkButton(janela, text="Próxima Página ►", font=("Arial", 14, "bold"),command=proxima_pagina, width=160, height=35)
    btn_proxima.place(relx=0.76, rely=0.92, anchor="center")
    carregar_pagina()


#-------------------------------------------------------------

def admin_page():
    for elemento in janela.winfo_children():
        elemento.destroy()
    frame_menu = ctk.CTkFrame(janela, fg_color="#1c1f28")
    frame_menu.place(relx=0.05, rely=0.5, relwidth=0.16, relheight=1, anchor="center")
    
    historico = ctk.CTkButton(janela, text="🕒 Histórico", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_historico)
    historico.place(relx=0.064, rely=0.24, anchor="center", relwidth=0.12, relheight=0.07)

    dashboard = ctk.CTkButton(janela, text="🪟 Painel", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_login)
    dashboard.place(relx=0.064, rely=0.15, anchor="center", relwidth=0.12, relheight=0.07)

    adm = ctk.CTkButton(janela, text="🔒 Admin",font=("Arial", 18, "bold"), corner_radius=10,
                        hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=admin_page)
    adm.place(relx=0.064, rely=0.9, anchor="center", relwidth=0.12, relheight=0.07)
    ctk.CTkLabel(janela,text="ADMIN ACESS",font=("Arial",24,"bold"),bg_color="#0f1123").place(relx= 0.56,rely=0.05,anchor="center")
    
    def fazer_login():
        texto_id = campo_id.get()
        texto_senha = campo_senha.get()
        if texto_id == "3141592" and texto_senha == "grupo4RFID":
            admin_liberado()
            print("Passou")
        else:
            aviso.configure(text="DADO(S) INCORRETOS")
    
    irt = False
    frame_senha = ctk.CTkFrame(janela,fg_color="#313541",corner_radius=25,bg_color="#0f1123")
    frame_senha.place(relx= 0.34,rely=0.15,relwidth=0.425,relheight = 0.75)

    campo_id = ctk.CTkEntry(frame_senha,corner_radius=12,placeholder_text="Digite o ID",placeholder_text_color="#8F929E",
                border_color="#F19D01",border_width=1,fg_color="#1E222D",text_color="#FFFFFF",font=("Inter",14))
    campo_id.place(relx=0.5,rely=0.43,anchor="center",relwidth=0.7,relheight = 0.1)

    campo_senha = ctk.CTkEntry(frame_senha,corner_radius=12,placeholder_text="Digite a senha",show="⁕",placeholder_text_color="#8F929E",
                border_color="#F19D01",border_width=1,fg_color="#1E222D",text_color="#FFFFFF",font=("Inter",14))
    campo_senha.place(relx=0.5,rely=0.58,anchor="center",relwidth=0.7,relheight = 0.1)

    login_button = ctk.CTkButton(frame_senha,text="Entrar",corner_radius=12,fg_color="#3B82F6",hover_color="#2563EB",
                text_color="#FFFFFF",font=("Inter",13,"bold"),command=fazer_login)
    login_button.place(relx=0.5,rely=0.85,anchor="center",relwidth=0.56,relheight = 0.1)

    def mostrar_campo_senha():
        nonlocal irt
        irt = not irt

        if irt:
            campo_senha.configure(show="")
        else:
            campo_senha.configure(show="⁕")

    mostrar_senha = ctk.CTkButton(frame_senha, text="Mostrar Senha",corner_radius=5,fg_color="#1F2129",hover_color="#111216",
                    text_color="#FFFFFF",font=("Inter",8,"bold"),command=mostrar_campo_senha)
    mostrar_senha.place(relx=0.225,rely=0.67,anchor="center",relwidth=0.15,relheight = 0.05)
    pfp_frame = ctk.CTkFrame(frame_senha,fg_color="#4C4F58",bg_color="#313541",corner_radius=80, border_color="yellow", border_width=1)
    pfp_frame.place(relx=0.5,rely=0.2,anchor="center",relwidth=0.265,relheight = 0.265)
    pfp = ctk.CTkLabel(frame_senha, text = "👤",bg_color="#4C4F58",font=("Arial",100,"bold"))
    pfp.place(relx=0.5025,rely=0.2,anchor="center",relwidth=0.15,relheight = 0.15)
    aviso = ctk.CTkLabel(frame_senha, text="", bg_color="#313541", text_color="RED",font=("Arial",12,"bold"))
    aviso.place(relx=0.5,rely=0.76,anchor="center")

#-------------------------------------------------------------

def admin_liberado():
    for elemento in janela.winfo_children():
        elemento.destroy()
    frame_menu = ctk.CTkFrame(janela, fg_color="#1c1f28")
    frame_menu.place(relx=0.05, rely=0.5, relwidth=0.16, relheight=1, anchor="center")
    def tela_add_user():
        janela_add = ctk.CTkToplevel(janela)
        janela_add.title("Adicionar Usuário")
        janela_add.geometry("350x250")
        campo_nome = ctk.CTkEntry(janela_add, placeholder_text="Nome do Usuário")
        campo_nome.pack(pady=10)
        campo_tag = ctk.CTkEntry(janela_add,placeholder_text="UID  da TAG")
        campo_tag.pack(pady=10)
        def salvar():
            nome = campo_nome.get().strip()
            tag = campo_tag.get().strip()
            if not nome or not tag:
                return
            adicionar_user(nome, tag)
            janela_add.destroy()
            admin_liberado()

        ctk.CTkButton(janela_add, text="Salvar usuário", command=salvar).pack(pady=10)
    def tela_remover_user():
        janela_rem = ctk.CTkToplevel(janela)
        janela_rem.title("Remover usuário")
        janela_rem.geometry("350x200")
        campo_id = ctk.CTkEntry(janela_rem, placeholder_text="ID do usuário")
        campo_id.pack(pady=15)
        def remover():
            try:
                id_usuario = int(campo_id.get())
            except ValueError:
                return
            remover_user(id_usuario)
            janela_rem.destroy()
            admin_liberado()
        ctk.CTkButton(janela_rem, text="Remover usuário", fg_color="#B91C1C", hover_color="#991B1B",command=remover).pack(pady=10)

    
    historico = ctk.CTkButton(janela, text="🕒 Histórico", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_historico)
    historico.place(relx=0.064, rely=0.24, anchor="center", relwidth=0.12, relheight=0.07)

    dashboard = ctk.CTkButton(janela, text="🪟 Painel", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_login)
    dashboard.place(relx=0.064, rely=0.15, anchor="center", relwidth=0.12, relheight=0.07)

    adm = ctk.CTkButton(janela, text="🔒 Admin",font=("Arial", 18, "bold"), corner_radius=10,
                        hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=admin_page)
    adm.place(relx=0.064, rely=0.9, anchor="center", relwidth=0.12, relheight=0.07)
    ctk.CTkLabel(janela,text="ADMIN ACESS",font=("Arial",24,"bold"),bg_color="#0f1123").place(relx= 0.56,rely=0.05,anchor="center")
    ctk.CTkButton(janela, text="+ Adicionar usuário", command=tela_add_user).place(relx=0.35, rely=0.85, relwidth=0.2)
    ctk.CTkButton( janela, text="- Remover usuário", fg_color="#B91C1C", hover_color="#991B1B", command=tela_remover_user).place(relx=0.58, rely=0.85, relwidth=0.2)
    
    def conectar_bd():
        conexao = sqlite3.connect('database_iot.db')
        cursor = conexao.cursor()
        return conexao,cursor


    def listar_users():
        conexao, cursor = conectar_bd()
        cursor.execute("SELECT id, nome, tag FROM usuarios")
        dados = cursor.fetchall()
        for i, usuario in enumerate(dados):
            registros_dados = f"{usuario[0]:<6} | {usuario[1]:<20} | {usuario[2]}"
            label_user = ctk.CTkLabel(janela, text=registros_dados,font=("Consolas",14),anchor="w")
            label_user.place(relx = 0.28,rely=0.15 + i * 0.06,relwidth=0.6, anchor="nw")
        conexao.close()
    listar_users()

    def adicionar_user(nome,tag):
        with sqlite3.connect('database_iot.db') as conexao:
            cursor = conexao.cursor()
            cursor.execute("INSERT INTO usuarios (nome, tag) VALUES (?, ?)",(nome, tag))
    def remover_user(id_usuario):
        with sqlite3.connect('database_iot.db') as conexao:
            cursor = conexao.cursor()
            cursor.execute("DELETE FROM usuarios WHERE id = ?",(id_usuario,))


tela_login()
janela.mainloop()
