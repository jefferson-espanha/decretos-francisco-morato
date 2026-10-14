import os
import pandas as pd
from sqlalchemy import create_engine
from nicegui import ui

RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

PORT = int(os.environ.get('PORT', 8080))

def carregar_dados():
    # 1. Tenta buscar no banco de dados Neon
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            df = pd.read_sql("SELECT * FROM decretos", engine)
            if not df.empty:
                return df.fillna('').to_dict('records')
        except Exception as e:
            print(f"Erro ao conectar ao Neon: {e}. Carregando do Google Drive...")

    # 2. Fallback direto do Google Sheets
    url = "https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv"
    try:
        df = pd.read_csv(url)
        col_map = {}
        for col in df.columns:
            c_str = str(col).strip()
            c_lower = c_str.lower()
            if 'exercicio' in c_lower or 'ano' in c_lower:
                col_map[col] = 'exercicio_decreto'
            elif 'decreto' in c_lower and ('g' in c_lower or '“' in c_str or '"' in c_str):
                col_map[col] = 'decreto_numero'
            elif 'data' in c_lower:
                col_map[col] = 'data_elaboracao'
            elif 'elabora' in c_lower:
                col_map[col] = 'orgao_elaboracao'
            elif 'link' in c_lower:
                col_map[col] = 'link_decreto'
            elif 'complemento' in c_lower or 'informaco' in c_lower or 'ruas' in c_lower:
                col_map[col] = 'complemento_informacoes'
            elif 'sei' in c_lower:
                col_map[col] = 'processo_sei'

        df = df.rename(columns=col_map)
        return df.fillna('').to_dict('records')
    except Exception as e:
        print(f"Erro ao carregar dados do Google Sheets: {e}")
        return []

@ui.page('/')
def main_page():
    ui.colors(primary='#1e3a8a')
    
    with ui.header().classes('bg-blue-900 text-white p-4 flex justify-between items-center shadow-md'):
        ui.label('Prefeitura de Francisco Morato — Decretos').classes('text-xl font-bold')

    with ui.column().classes('w-full p-6 max-w-7xl mx-auto'):
        ui.label('Consulta Pública de Decretos Municipais').classes('text-2xl font-bold text-gray-800 mb-1')
        ui.label('Pesquise por nome, rua, lote, número do decreto, órgão ou processo SEI.').classes('text-gray-600 mb-6')

        dados = carregar_dados()

        if dados:
            colunas = [
                {'name': 'exercicio_decreto', 'label': 'Ano', 'field': 'exercicio_decreto', 'sortable': True, 'align': 'center'},
                {'name': 'decreto_numero', 'label': 'Decreto “G”', 'field': 'decreto_numero', 'sortable': True, 'align': 'center'},
                {'name': 'data_elaboracao', 'label': 'Data', 'field': 'data_elaboracao', 'sortable': True, 'align': 'center'},
                {'name': 'orgao_elaboracao', 'label': 'Elaboração', 'field': 'orgao_elaboracao', 'align': 'left'},
                {'name': 'processo_sei', 'label': 'Processo SEI', 'field': 'processo_sei', 'align': 'left'},
                {'name': 'complemento_informacoes', 'label': 'Informações / Complemento', 'field': 'complemento_informacoes', 'align': 'left', 'classes': 'max-w-md break-words'},
                {'name': 'link_decreto', 'label': 'Link', 'field': 'link_decreto', 'align': 'center'}
            ]

            search_input = ui.input(placeholder='🔍 Digite para pesquisar em todas as colunas...').classes('w-full mb-4 shadow-sm')

            tabela = ui.table(
                columns=colunas,
                rows=dados,
                row_key='exercicio_decreto',
                pagination=15
            ).classes('w-full shadow-lg rounded-lg border')

            tabela.add_slot('body-cell-link_decreto', '''
                <q-td :props="props">
                    <a v-if="props.value" :href="props.value" target="_blank" class="text-blue-600 underline font-medium hover:text-blue-800">
                        Abrir ↗
                    </a>
                    <span v-else class="text-gray-400">-</span>
                </q-td>
            ''')

            search_input.bind_value_to(tabela, 'filter')
        else:
            ui.label('⚠️ Não foi possível carregar a tabela. Verifique o compartilhamento da planilha.').classes('text-red-500 font-bold p-4 bg-red-50 rounded-md')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host='0.0.0.0', port=PORT, reload=False)
