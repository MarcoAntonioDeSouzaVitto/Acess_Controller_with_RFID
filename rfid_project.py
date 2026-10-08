import sqlite3
from datetime import datetime
import serial
import time
import customtkinter as ctk
ctk.set_appearance_mode("dark")
janela = ctk.CTk()
conexao = sqlite3.connect('database_iot.db')
funcio = conexao.cursor()
funcio.execute("DROP DATABASE IF EXISTS database_iot.db")
funcio.execute("""
    CREATE TABLE IF NOT EXISTS registros(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT NOT NULL,
        acesso TEXT NOT NULL,
        data_hora TEXT NOT NULL,
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
    exit()


"""try:
    while True:
        if arduino.in_waiting > 0:"""



agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

conexao.commit()
