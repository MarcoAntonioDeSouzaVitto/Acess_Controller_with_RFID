import sqlite3


conexao = sqlite3.connect("database_iot.db")
cursor = conexao.cursor()

usuarios = [
        ("A1B2C3D4", "João Silva"),
        ("E5F6A7B8", "Maria Oliveira"),
        ("C9D0E1F2", "Pedro Santos"),
        ("A3B4C5D6", "Ana Costa"),
        ("E7F8A9B0", "Lucas Pereira"),
        ("C1D2E3F4", "Julia Almeida"),
        ("A5B6C7D8", "Gabriel Souza"),
        ("E9F0A1B2", "Beatriz Lima"),
        ("C3D4E5F6", "Rafael Ferreira"),
        ("A7B8C9D0", "Camila Rodrigues"),
        ("E1F2A3B4", "Matheus Gomes"),
        ("C5D6E7F8", "Larissa Martins"),
        ("A9B0C1D2", "Felipe Ribeiro"),
        ("E3F4A5B6", "Isabela Carvalho"),
        ("C7D8E9F0", "Bruno Araújo"),
        ("A2B3C4D5", "Mariana Cardoso"),
        ("E6F7A8B9", "Thiago Barbosa"),
        ("C0D1E2F3", "Letícia Nunes"),
        ("A4B5C6D7", "Vinícius Mendes"),
        ("E8F9A0B1", "Amanda Teixeira")
    ]

cursor.executemany(
        "INSERT INTO usuarios (uid, nome) VALUES (?, ?)",
        usuarios
)

conexao.commit()
conexao.close()

print("Banco recriado e cartões cadastrados!")