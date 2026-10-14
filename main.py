import os
import pandas as pd
from sqlalchemy import create_engine
from nicegui import ui

# 1. Configuração e tratamento do protocolo de conexão do PostgreSQL
RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

PORT = int(os.environ.get('PORT', 8080))

# 2. Busca de dados no Neon
def buscar_decretos():
    if not DATABASE_URL:
        return []
    try:
        engine = create_engine(DATABASE_URL)
        df = pd.read_sql("SELECT * FROM decretos ORDER BY exercicio_decreto DESC", engine)
        
        # Formatação amigável de datas
        if 'data_elaboracao' in df.columns:
            df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao']).dt.strftime('%d/%m/%Y')
            
        return df.fillna('').to_dict('records')
    except Exception as e:
        print(f"Erro ao conectar com o banco de dados: {e}")
        return []

# 3. Interface Visual do NiceGUI
@ui.page('/')
def main_page():
    ui.colors(primary='#1e3a8a')
    
    # Cabeçalho Principal
    with ui.header().classes('bg-blue-900 text-white p-4 flex justify-between items-center shadow-md'):
        ui.label('Prefeitura de Francisco Morato — Decretos').classes('text-xl font-bold')

    with ui.column().classes('w-full p-6 max-w-7xl mx-auto'):
        ui.label('Consulta Pública de Decretos Municipais').classes('text-2xl font-bold text-gray-800 mb-1')
        ui.label('Pesquise por complemento, ruas, lotes, quadras ou processo SEI.').classes('text-gray-600 mb-6')

        dados = buscar_decretos()

        if dados:
            colunas = [
                {'name': 'exercicio_decreto', 'label': 'Ano', 'field': 'exercicio_decreto', 'sortable': True, 'align': 'center'},
                {'name': 'data_elaboracao', 'label': 'Data de Elaboração', 'field': 'data_elaboracao', 'sortable': True, 'align': 'center'},
                {'name': 'processo_sei', 'label': 'Processo SEI', 'field': 'processo_sei', 'sortable': True, 'align': 'left'},
                {'name': 'complemento_informacoes', 'label': 'Informações / Complemento', 'field': 'complemento_informacoes', 'align': 'left', 'classes': 'max-w-md break-words'},
                {'name': 'link_decreto', 'label': 'Decreto (Link)', 'field': 'link_decreto', 'align': 'center'}
            ]

            # Campo de Busca Geral
            search_input = ui.input(placeholder='🔍 Digite para pesquisar...').classes('w-full mb-4 shadow-sm')

            # Tabela de Dados Interativa
            tabela = ui.table(
                columns=colunas,
                rows=dados,
                row_key='id',
                pagination=15
            ).classes('w-full shadow-lg rounded-lg border')

            # Slot personalizado para renderizar o link do decreto como botão/ancora clicável
            tabela.add_slot('body-cell-link_decreto', '''
                <q-td :props="props">
                    <a v-if="props.value" :href="props.value" target="_blank" class="text-blue-600 underline font-medium hover:text-blue-800">
                        Abrir Documento ↗
                    </a>
                    <span v-else class="text-gray-400">Indisponível</span>
                </q-td>
            ''')

            # Conecta o filtro de entrada à tabela NiceGUI
            search_input.bind_value_to(tabela, 'filter')
        else:
            ui.label('⚠️ Nenhum registro encontrado ou falha na conexão com o Neon.').classes('text-red-500 font-bold p-4 bg-red-50 rounded-md')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host='0.0.0.0', port=PORT, reload=False)
