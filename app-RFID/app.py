import flet as ft
import time
def main(page: ft.Page):
    page.title = "MonitorRFID"
    page.bgcolor = "#0E0E55"
    page.padding = 0
    page.spacing = 0
    page.window_width = 350
    page.window_height = 700
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    def tela_home(e=None):

        txt_painel = ft.Text(
            "Painel de Entrada",
            size=20,
            weight="bold",
            color="#0E0E55",
        )
        txt_registro = ft.Text(
            "Ultimos Acessos",
            size=15,
            weight="bold",
            color="#f0f0fc",
        )

        t_uid = ft.Text(
            "UID",
            expand=1,
            text_align=ft.TextAlign.CENTER,
            size=14,
            weight="bold",
            color="#f0f0fc",
        )
        t_status = ft.Text(
            "Status",
            expand=2,
            text_align=ft.TextAlign.CENTER,
            size=14,
            weight="bold",
            color="#f0f0fc",
        )
        t_dth = ft.Text(
            "Data Hora",
            expand=1,
            text_align=ft.TextAlign.CENTER,
            size=14,
            weight="bold",
            color="#f0f0fc",
        )

        title_painel = ft.Container(
            content=txt_painel,
            alignment=ft.alignment.center,
            padding=50,
        )

        linha_principal = ft.Container(
            content=ft.Row(
                controls=[
                    t_uid, 
                    t_status, 
                    t_dth     
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#0E0E55",
            border_radius=3,
            padding=3,
        )
        ft.Container(height=50)
        btn_liberar = ft.Container (
            ft.ElevatedButton(
                text="Liberar acesso",
                icon=ft.icons.LOCK_OPEN_SHARP,
                style=ft.ButtonStyle(
                    side=ft.BorderSide(width=1, color="#b1b1c0"),
                    shape=ft.RoundedRectangleBorder(radius=5)
                ),
                bgcolor="#f0f0fc",
                color="#5ed97c"
            ),
            padding=10,
            alignment=ft.alignment.center
        )
        btn_voltar = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    on_click=lambda _:page.go("/tela_login")      
                )
            ],
            alignment=ft.alignment.bottom_left
        )
        lista_acessos = [
            ["A3 B2 C5 D1", "Liberado", "25/10/2026 16:15"],
            ["F8 4E 92 A0", "Negado", "25/10/2026 16:18"],
            ["12 C3 D4 E5", "Liberado", "25/10/2026 16:20"],
            ["7B 9A 2C 4D", "Negado", "25/10/2026 16:24"],
            ["7B 9A 2C 4D", "Negado", "25/10/2026 16:24"]
        ]
        
        lista_dados = ft.ListView(padding=0, spacing=0)
        for uid, status, dth in lista_acessos:
            if status == "Liberado":
                cor_status = "#5ed97c"
            else:
                cor_status = "#ff6b6b"

            lista_dados.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(uid, color="#f0f0fc", expand=1, size=12, text_align=ft.TextAlign.CENTER),
                            ft.Text(status, color=cor_status, expand=2, size=13, text_align=ft.TextAlign.CENTER),
                            ft.Text(dth, color="#f0f0fc", expand=1, size=13, text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor="#0E0E55",
                    border_radius=3,
                    padding=3,
                    margin=3,
            )
        )
        painel_fundo = ft.Container(
            content=ft.Column(
                controls=[
                    txt_registro,
                    linha_principal,
                    lista_dados
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.top_center,
            bgcolor="#021433",
            margin=1,
            padding=5,
            border_radius=5,
            width=320,
            height= 330
        )
        
        page.views.append(
            ft.View(
                route="/tela_home",
                controls=[
                    title_painel,
                    painel_fundo,
                    btn_liberar,
                    btn_voltar
                ],
                bgcolor = "#ABDCDC",
                horizontal_alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        

    def tela_login(e=None):
   

        def validacao_de_campo(e):
            if campo_email.value and campo_senha.value:
                
                page.snack_bar = ft.SnackBar(content=ft.Text("Login Realizado com sucesso!", color="#f0f0fc"),
                bgcolor="green",
                duration=1000
                )
                page.snack_bar.open = True
                page.update()
                time.sleep(2)
                page.go("/tela_home")
            else:
                page.snack_bar = ft.SnackBar(content=ft.Text("Preencha todos os campos!"),
                    bgcolor="red",
                    duration=1000
                )
                page.snack_bar.open = True
                page.update ()

        campo_email = ft.TextField(label="Insira seu nome de usuario", 
            label_style=ft.TextStyle(size=10),
            bgcolor="#f0f0fc",
            width=200,
            height=38    
        )
        
        campo_senha = ft.TextField(label="Insira sua senha",
            password=True,
            can_reveal_password=True,
            bgcolor="#f0f0fc", 
            label_style=ft.TextStyle(size=10),
            width=200,
            height=38
        )
        painel_login = ft.Container(
            content= ft.Column(
                controls=[

                    ft.Text("Login", 
                    size=30, 
                    weight="bold", 
                    color="#f0f0fc"),

                    ft.Image(
                        src="assets/icons/logo.png",
                        width=60,
                        height=60,
                        fit =ft.ImageFit.CONTAIN
                    ),
                    ft.Container( height=15),
                    campo_email,
                    campo_senha,
                    ft.Container( height=15),
                    ft.ElevatedButton(
                        text="Fazer Login",
                        on_click=validacao_de_campo,
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.alignment.center,
                spacing=10
            ),
            width=300,
            height= 360,
            padding=30,
            border_radius=12,
            bgcolor="#0F3372",
            alignment=ft.alignment.center
        )
        
        page.views.append(
            
            ft.View(
                route="/tela_login",
                controls=[
                    painel_login
                ],
                bgcolor = "#ABDCDC",
                vertical_alignment = ft.MainAxisAlignment.CENTER,
                horizontal_alignment = ft.CrossAxisAlignment.CENTER
            )
        )

        
    def troca_tela():
        page.views.clear()
        if page.route == "/tela_login":
            tela_login()
        elif page.route == "/tela_home":
            tela_home()
        page.update()

    page.on_route_change = lambda _: troca_tela()
    page.go("/tela_login")

ft.app(target=main)
