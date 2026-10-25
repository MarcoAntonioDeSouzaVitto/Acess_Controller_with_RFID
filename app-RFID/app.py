import flet as ft

# pagina principal do monitor
def main(page: ft.Page):

    page.bgcolor = "#000000"
    page.title = "Pymonitor"
    page.vertical_alignment =   ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

#simulação para a formatação dos dados
    lista_dados = ft.ListView()

    lista_acessos = [
        ["A3 B2 C5 D1",     "Liberado",  "25/10/2026 16:15"],
        ["F8 4E 92 A0",     "Negado",    "25/10/2026 16:18"],
        ["12 C3 D4 E5",     "Liberado",  "25/10/2026 16:20"],
        ["7B 9A 2C 4D",     "Negado",    "25/10/2026 16:24"]
    ]

    for acessos in lista_acessos:
           uid = acessos[0] 
           status = acessos[1]
           dth = acessos[2]
           
           lista_dados.controls.append(
            ft.Container(
                content=ft.Row (
                    controls=[
                     ft.Text(uid, color="#d6d6d6", expand=1, size=12, text_align=ft.TextAlign.CENTER),
                     ft.Text(status, color="#d6d6d6", expand=2, size=13, text_align=ft.TextAlign.CENTER),
                     ft.Text(dth, color="#d6d6d6", expand=1, size=13, text_align=ft.TextAlign.CENTER)
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            bgcolor="#434343",
            border_radius=3,
            padding=3,
            margin=3
        )
    )

#variaveis do app
    txt_painel = ft.Text('Painel de Entrada', 
                         size=20, weight="Bold", color="#d6d6d6")
    txt_registro = ft.Text('Ultimos Acesso', 
                           size=15, weight="bold", color="#d6d6d6")

    t_uid = ft.Text('UID',
                    expand=1,text_align=ft.TextAlign.CENTER, size=14, weight="Bold", color="#d6d6d6")
    t_status = ft.Text('Status', 
                       expand=2,text_align=ft.TextAlign.CENTER, size=14, weight="Bold", color="#d6d6d6")
    t_dth = ft.Text('Data Hora', 
                    expand=1, text_align=ft.TextAlign.CENTER, size=14, weight="Bold", color="#d6d6d6")

#estilização e posicionamento
    
    title_painel = ft.Container(
        content=txt_painel,
        alignment=ft.alignment.center,
        padding=50
    )

    linha_principal = ft.Container(

        content= ft.Row(
            controls=[
                t_uid,
                t_status,
                t_dth
            ],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#434343",
            border_radius=3,
            margin=3,
        )
    
    painel_fundo = ft.Container(
        
        content= ft.Column(
            controls=[
            txt_registro,
            linha_principal,
            lista_dados
            ],
        
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.top_center,
        bgcolor="#242424",
        margin=1,
        border_radius=5,
    )
    
    camadas = ft.Stack(

        controls=[
            painel_fundo 
        ]
    )

# adiciona variavel ao front
    page.add(
        title_painel,
        camadas
    )

ft.app(target=main)