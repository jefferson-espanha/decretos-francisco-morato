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
    # 1. Tenta carregar do banco Neon
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            df = pd.read_sql("SELECT * FROM decretos", engine)
            if not df.empty:
                return df.fillna('').to_dict('records')
        except Exception as e:
            print(f"Erro ao ler do Neon: {e}. Carregando do Google Drive...")

    # 2. Fallback direto do Google Sheets lendo por posição
    url = "https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv"
    try:
        df = pd.read_csv(url)
        df = df.iloc[:, :7]
        df.columns = [
            'exercicio_decreto',
            'decreto_numero',
            'data_elaboracao',
            'orgao_elaboracao',
            'link_decreto',
            'complemento_informacoes',
            'processo_sei'
        ]
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

            # Renderizador seguro de links: trata URLs completas (https://) e nomes de PDF
            tabela.add_slot('body-cell-link_decreto', '''
                <q-td :props="props">
                    <template v-if="props.value">
                        <a v-if="props.value.startsWith('http')" :href="props.value" target="_blank" class="text-blue-600 underline font-medium hover:text-blue-800">
                            Abrir ↗
                        </a>
                        <a v-else :href="'https://drive.google.com/drive/search?q=' + encodeURIComponent(props.value)" target="_blank" class="text-blue-600 underline font-medium hover:text-blue-800">
                            {{ props.value }} ↗
                        </a>
                    </template>
                    <span v-else class="text-gray-400">-</span>
                </q-td>
            ''')

            search_input.bind_value_to(tabela, 'filter')
        else:
            ui.label('⚠️ Não foi possível carregar a tabela. Verifique o compartilhamento da planilha.').classes('text-red-500 font-bold p-4 bg-red-50 rounded-md')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host='0.0.0.0', port=PORT, reload=False)
