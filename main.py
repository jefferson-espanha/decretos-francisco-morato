import os
import pandas as pd
from nicegui import ui

# Link direto para exportar a planilha do Google Drive em CSV
SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv"
PORT = int(os.environ.get('PORT', 8080))

def carregar_dados():
    try:
        # Lê a planilha do Google Sheets
        df = pd.read_csv(SHEETS_URL)
        
        # Limpa o nome das colunas removendo espaços extras
        df.columns = [str(col).strip() for col in df.columns]

        # Mapeia os nomes das colunas da planilha para o padrão da tabela
        col_map = {
            'Exercicio': 'exercicio_decreto',
            'ExercicioDecreto': 'exercicio_decreto',
            'Data': 'data_elaboracao',
            'Link do Decreto': 'link_decreto',
            'Link do Decreto ': 'link_decreto',
            'complemento_informacoes': 'complemento_informacoes',
            'Complemento': 'complemento_informacoes',
            'processo_sei': 'processo_sei',
            'PROCESSO SEI': 'processo_sei'
        }
        df = df.rename(columns=col_map)

        # Seleciona apenas as colunas necessárias
        colunas_desejadas = ['exercicio_decreto', 'data_elaboracao', 'processo_sei', 'complemento_informacoes', 'link_decreto']
        colunas_existentes = [c for c in colunas_desejadas if c in df.columns]
        df = df[colunas_existentes]

        # Tratamento simples de valores nulos
        return df.fillna('').to_dict('records')
    except Exception as e:
        print(f"Erro ao carregar Google Sheets: {e}")
        return []

@ui.page('/')
def main_page():
    ui.colors(primary='#1e3a8a')
    
    with ui.header().classes('bg-blue-900 text-white p-4 flex justify-between items-center shadow-md'):
        ui.label('Prefeitura de Francisco Morato — Decretos').classes('text-xl font-bold')

    with ui.column().classes('w-full p-6 max-w-7xl mx-auto'):
        ui.label('Consulta Pública de Decretos Municipais').classes('text-2xl font-bold text-gray-800 mb-1')
        ui.label('Pesquise por complemento, ruas, lotes, quadras ou processo SEI.').classes('text-gray-600 mb-6')

        dados = carregar_dados()

        if dados:
            colunas = [
                {'name': 'exercicio_decreto', 'label': 'Ano', 'field': 'exercicio_decreto', 'sortable': True, 'align': 'center'},
                {'name': 'data_elaboracao', 'label': 'Data', 'field': 'data_elaboracao', 'sortable': True, 'align': 'center'},
                {'name': 'processo_sei', 'label': 'Processo SEI', 'field': 'processo_sei', 'sortable': True, 'align': 'left'},
                {'name': 'complemento_informacoes', 'label': 'Informações / Complemento', 'field': 'complemento_informacoes', 'align': 'left', 'classes': 'max-w-md break-words'},
                {'name': 'link_decreto', 'label': 'Link do Decreto', 'field': 'link_decreto', 'align': 'center'}
            ]

            search_input = ui.input(placeholder='🔍 Digite para pesquisar...').classes('w-full mb-4 shadow-sm')

            tabela = ui.table(
                columns=colunas,
                rows=dados,
                row_key='exercicio_decreto',
                pagination=15
            ).classes('w-full shadow-lg rounded-lg border')

            # Renderiza os links como botões clicáveis
            tabela.add_slot('body-cell-link_decreto', '''
                <q-td :props="props">
                    <a v-if="props.value" :href="props.value" target="_blank" class="text-blue-600 underline font-medium hover:text-blue-800">
                        Abrir Documento ↗
                    </a>
                    <span v-else class="text-gray-400">-</span>
                </q-td>
            ''')

            search_input.bind_value_to(tabela, 'filter')
        else:
            ui.label('⚠️ Não foi possível carregar os dados da planilha. Verifique se a planilha do Google Drive está pública.').classes('text-red-500 font-bold p-4 bg-red-50 rounded-md')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host='0.0.0.0', port=PORT, reload=False)
