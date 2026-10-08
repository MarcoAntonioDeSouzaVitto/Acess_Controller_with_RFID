import sqlite3
from datetime import datetime
import serial
import time
import customtkinter as ctk

ctk.set_appearance_mode("dark")
janela = ctk.CTk()
janela.geometry("1200x800")
largura_tela = janela.winfo_screenwidth()
height_tela = janela.winfo_screenheight()
janela.resizable(False,False)
janela.title("Sistema de Acesso - RFID")
janela.config(background="#13161F")
situation = "---"
conexao = sqlite3.connect('database_iot.db')
funcio = conexao.cursor()

# Correção: No SQLite usa-se DROP TABLE
funcio.execute("DROP TABLE IF EXISTS registros")

# Correção: Removida a vírgula extra depois de TEXT NOT NULL
funcio.execute("""
    CREATE TABLE IF NOT EXISTS registros(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT NOT NULL,
        acesso TEXT NOT NULL,
        data_hora TEXT NOT NULL
    )
""")
porta_arduino = "COM3"
baud_rate = 9600

try:
    arduino = serial.Serial(porta_arduino, baud_rate, timeout=1)
    time.sleep(2)
    print(f"Conectado com sucesso ao Arduino na porta {porta_arduino}!")
except Exception as e:
    print(f"Erro ao conectar na porta {porta_arduino}. Verifique se a porta está correta ou se o monitor serial do Arduino IDE está fechado.")
    arduino = None



agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

conexao.commit()

def tela_login():
    for elemento in janela.winfo_children():
        elemento.destroy()
    frame_menu = ctk.CTkFrame(janela, fg_color="#1c1f28")
    frame_menu.place(relx=0.05,rely=0.5,relwidth=0.16,relheight=1,anchor= "center")

    ctk.CTkLabel(janela, text="Painel de Monitoramento", font=("Arial",24,"bold"),bg_color="#0f1123").place(relx=0.56,rely = 0.045, anchor="center")
    #------------------
    historico = ctk.CTkButton(janela, text="🕒 Histórico", font=("Arial",18,"bold"), corner_radius=10,
                  hover_color="#313541", fg_color="#1c1f28",text_color="#575a63",command=tela_historico)
    historico.place(relx= 0.064, rely = 0.24, anchor = "center",relwidth=0.12,relheight=0.07)
    #------------------
    dashboard = ctk.CTkButton(janela, text="🪟  Painel", font=("Arial",18,"bold"), corner_radius=10,
                  hover_color="#313541", fg_color="#1c1f28",text_color="#575a63",command=tela_login)
    dashboard.place(relx= 0.064, rely = 0.15, anchor = "center",relwidth=0.12,relheight=0.07)
    #------------------
    status =ctk.CTkLabel(janela, text=f"Status de Conexão do Arduino: ● {situation}",bg_color="#0f1123", font=("Arial",20,"bold"))
    status.place(relx=0.56,rely = 0.125, anchor="center")
    screen = ctk.CTkFrame(janela, fg_color="#5ed97c",corner_radius=25,bg_color="#0f1123")
    screen.place(relx=0.56,rely=0.34,relwidth=0.5,relheight=0.35,anchor= "center")
    registros = ctk.CTkFrame(janela, fg_color="#262a35",corner_radius=25,bg_color="#0f1123")
    registros.place(relx=0.56,rely=0.75,relwidth=0.48,relheight=0.4,anchor= "center")
    
def tela_historico():
    for elemento in janela.winfo_children():
        elemento.destroy()
        frame_menu = ctk.CTkFrame(janela, fg_color="#1c1f28")
    frame_menu.place(relx=0.05,rely=0.5,relwidth=0.16,relheight=1,anchor= "center")

    ctk.CTkLabel(janela, text="Histórico de Acesso & Relatórios", font=("Arial",24,"bold"),bg_color="#0f1123").place(relx=0.32,rely = 0.06, anchor="center")
    #------------------
    historico = ctk.CTkButton(janela, text="🕒 Histórico", font=("Arial",18,"bold"), corner_radius=10,
                  hover_color="#313541", fg_color="#1c1f28",text_color="#575a63",command=tela_historico)
    historico.place(relx= 0.064, rely = 0.24, anchor = "center",relwidth=0.12,relheight=0.07)
    #------------------
    dashboard = ctk.CTkButton(janela, text="🪟  Painel", font=("Arial",18,"bold"), corner_radius=10,
                  hover_color="#313541", fg_color="#1c1f28",text_color="#575a63",command=tela_login)
    dashboard.place(relx= 0.064, rely = 0.15, anchor = "center",relwidth=0.12,relheight=0.07)

tela_login()
janela.mainloop()
