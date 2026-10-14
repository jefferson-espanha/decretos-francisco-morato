import os
import pandas as pd
from sqlalchemy import create_engine
from nicegui import ui

# 1. Configuração da URL de conexão (trata o protocolo para o SQLAlchemy)
RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

# Configura a porta dinâmica exigida pelo Render
PORT = int(os.environ.get('PORT', 8080))

# 2. Função para buscar os decretos no Neon
def buscar_decretos():
    if not DATABASE_URL:
        return []
    try:
        engine = create_engine(DATABASE_URL)
        # Consulta os dados da tabela
        df = pd.read_sql("SELECT * FROM decretos ORDER BY exercicio_decreto DESC", engine)
        # Converte datas para texto legível
        if 'data_elaboracao' in df.columns:
            df['data_elaboracao'] = df['data_elaboracao'].dt.strftime('%d/%m/%Y')
        return df.fillna('').to_dict('records')
    except Exception as e:
        print(f"Erro ao conectar no banco: {e}")
        return []

# 3. Montagem da Interface NiceGUI
@ui.page('/')
def main_page():
    ui.colors(primary='#1e3a8a') # Azul institucional
    
    with ui.header().classes('bg-blue-900 text-white p-4 flex justify-between items-center'):
        ui.label('Prefeitura de Francisco Morato — Decretos').classes('text-xl font-bold')

    with ui.column().classes('w-full p-6 max-w-7xl mx-auto'):
        ui.label('Consulta Pública de Decretos Municipal').classes('text-2xl font-bold text-gray-800 mb-2')
        ui.label('Pesquise por nome, rua, lote, quadra ou processo SEI.').classes('text-gray-600 mb-4')

        dados = buscar_decretos()

        if dados:
            colunas = [
                {'name': 'exercicio_decreto', 'label': 'Ano', 'field': 'exercicio_decreto', 'sortable': True},
                {'name': 'data_elaboracao', 'label': 'Data', 'field': 'data_elaboracao', 'sortable': True},
                {'name': 'processo_sei', 'label': 'Processo SEI', 'field': 'processo_sei', 'sortable': True},
                {'name': 'complemento_informacoes', 'label': 'Complemento / Informações', 'field': 'complemento_informacoes', 'classes': 'max-w-md break-words'},
                {'name': 'link_decreto', 'label': 'Link', 'field': 'link_decreto'}
            ]

            # Campo de Pesquisa Geral
            search_input = ui.input(placeholder='Buscar por qualquer termo...').classes('w-full mb-4')

            # Tabela Quasar/NiceGUI com busca integrada
            tabela = ui.table(
                columns=colunas,
                rows=dados,
                row_key='id',
                pagination=15
            ).classes('w-full shadow-lg rounded-lg')

            # Conecta o campo de entrada ao filtro da tabela
            search_input.bind_value_to(tabela, 'filter')
        else:
            ui.label('Nenhum decreto encontrado ou falha na conexão com o banco de dados.').classes('text-red-500 font-bold')

# Necessário para execução em produção no Render
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host='0.0.0.0', port=PORT, reload=False)
