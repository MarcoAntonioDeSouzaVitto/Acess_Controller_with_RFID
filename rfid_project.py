import sqlite3
from datetime import datetime
import serial
import time
import customtkinter as ctk
import threading

ctk.set_appearance_mode("dark")
janela = ctk.CTk()
janela.geometry("1200x800")
janela.resizable(False, False)
janela.title("Sistema de Acesso - RFID")
janela.config(background="#13161F")

situacao_var = ctk.StringVar(value="Verificando...")

porta_arduino = "COM3"
baud_rate = 9600
TAGS = {"05 65 B0 E3 64 03 E9",
        "C4 72 CD CF"}

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
    iniciar_banco()
    arduino = None
    tags_validas = {tag.strip().upper() for tag in TAGS}
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

                    conexao = sqlite3.connect('database_iot.db')
                    cursor = conexao.cursor()
                    cursor.execute(
                        "INSERT INTO registros (uid, acesso, data_hora) VALUES(?,?,?)",
                        (dados_lidos, acesso, agora)
                    )
                    conexao.commit()
                    conexao.close()
            else:
                time.sleep(0.1)
                
        except (serial.SerialException, serial.SerialTimeoutException):
            try:
                arduino.close()
            except:
                pass
            arduino = None
            situacao_var.set("Não Conectado ●")

thread_rfid = threading.Thread(target=loop_leitura_rfid, daemon=True)
thread_rfid.start()




# ---------------------- Interface Gráfica ----------------------

def tela_login():
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

    atualizar_cor_status()

    screen = ctk.CTkFrame(janela, fg_color="#5ed97c", corner_radius=25, bg_color="#0f1123")
    screen.place(relx=0.56, rely=0.34, relwidth=0.5, relheight=0.35, anchor="center")

    registros = ctk.CTkFrame(janela, fg_color="#262a35", corner_radius=25, bg_color="#0f1123")
    registros.place(relx=0.56, rely=0.75, relwidth=0.48, relheight=0.4, anchor="center")

def tela_historico():
    for elemento in janela.winfo_children():
        elemento.destroy()

    frame_menu = ctk.CTkFrame(janela, fg_color="#1c1f28")
    frame_menu.place(relx=0.05, rely=0.5, relwidth=0.16, relheight=1, anchor="center")

    ctk.CTkLabel(janela, text="Histórico de Acesso & Relatórios", font=("Arial", 24, "bold"), bg_color="#0f1123").place(relx=0.32, rely=0.06, anchor="center")

    historico = ctk.CTkButton(janela, text="🕒 Histórico", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_historico)
    historico.place(relx=0.064, rely=0.24, anchor="center", relwidth=0.12, relheight=0.07)

    dashboard = ctk.CTkButton(janela, text="🪟 Painel", font=("Arial", 18, "bold"), corner_radius=10,
                              hover_color="#313541", fg_color="#1c1f28", text_color="#575a63", command=tela_login)
    dashboard.place(relx=0.064, rely=0.15, anchor="center", relwidth=0.12, relheight=0.07)

tela_login()
janela.mainloop()
