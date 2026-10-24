import flet as ft
#def pagina 2 de cadastro de tag
##def pag2(page: ft.page):
    #page.title
    #print("pagina 2")

# pagina principal do monitor
def main(page: ft.Page):

    page.theme_mode = ft.ThemeMode.DARK
    page.title = "Pymonitor"
    page.font = {
        "JetBrains Mono": "font/statc/JetBrainsMono-Regular.ttf"
    }
    page.vertical_alignment =   ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

#variaveis do app
    txt_painel = ft.Text('Painel de Entrada', size=20, weight="Bold")
    txt_registro = ft.Text('Ultimos Acesso', size=15)
    d_uid = ft.Text('UID', font_family="JetBrains Mono")
    d_status = ft.Text('Status', font_family="JetBrains Mono")
    d_dth = ft.Text('Data Hora', font_family="JetBrains Mono")

#estilização e posicionamento
    
    title_painel = ft.Container(
        content=txt_painel,
        alignment=ft.alignment.center,
        padding=50
    )

    linha_principal = ft.Row(
         controls=[
            d_uid,
            d_status,
            d_dth
        ],
        alignment=ft.MainAxisAlignment.SPACE_EVENLY
     )
    painel_fundo = ft.Container(
        
        content= ft.Column(
            controls=[
            txt_registro,
            linha_principal
            ],
        
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.top_center,
        width=250,
        height=200,
        bgcolor=ft.colors.BLACK12,
        border_radius=10,
        padding=40  
    )

    camadas = ft.Stack(

        controls=[
            painel_fundo,  
        ],      
    )
    #btn_add = ft.ElevatedButton("Cadastrar Tag", on_click=pag2)
    

# adiciona variavel ao front
    page.add(
        title_painel,
        camadas
        #btn_add 
    )
ft.app(target=main)