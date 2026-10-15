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
janela.geometry("1200x800")
janela.resizable(False, False)
janela.title("Sistema de Acesso - RFID")
janela.config(background="#13161F")

situacao_var = ctk.StringVar(value="Verificando...")

porta_arduino = "COM3"
baud_rate = 9600
TAGS = {"05 65 B0 E3 64 03 E9","33 4D 33 AD"}

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
    conexao.commit()
    conexao.close()

def loop_leitura_rfid():
    global registro_primeiro
    iniciar_banco()
    arduino = None
    tags_validas = {tag.strip().upper() for tag in TAGS}
    conexao = sqlite3.connect("database_iot.db")
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM registros ORDER BY id DESC LIMIT 1;")
    registro_primeiro = cursor.fetchone()
    while True:
        if arduino is None:
            try:
                arduino = serial.Serial(port=porta_arduino, baudrate=baud_rate, timeout=1)
                time.sleep(2)
                print(f"Conectado à porta {porta_arduino}")
                situacao_var.set("Conectado ●")
            except Exception:
                situacao_var.set("Não Conectado ●")
                time.sleep(2)
                continue

        try:
            if arduino.in_waiting > 0:
                raw_bytes = arduino.readline()
                dados_lidos = raw_bytes.decode('utf-8', errors='ignore').strip().upper()
                if dados_lidos:
                    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    if dados_lidos in TAGS:
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

    status_label = ctk.CTkLabel(janela, text="Status de Conexão do Arduino: ", bg_color="#0f1123", font=("Arial", 20, "bold"))
    status_label.place(relx=0.50, rely=0.125, anchor="center")

    situacao_label = ctk.CTkLabel(janela, textvariable=situacao_var, bg_color="#0f1123", font=("Arial", 20, "bold"))
    situacao_label.place(relx=0.69, rely=0.126, anchor="center")

    def atualizar_cor_status():
        if situacao_var.get() == "Conectado ●":
            situacao_label.configure(text_color="#00ff1e")
        else:
            situacao_label.configure(text_color="red")
        janela.after(500, atualizar_cor_status)
    timer_status = janela.after(500, atualizar_cor_status)
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

    def atualizar_tabela():
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
tela_login()
janela.mainloop()
