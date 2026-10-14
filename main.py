import os
import re
import pandas as pd
from sqlalchemy import create_engine
from nicegui import ui

RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

PORT = int(os.environ.get('PORT', 8080))

def limpar_ano(val):
    if pd.isna(val) or val == '':
        return ''
    s = str(val).replace('.0', '').strip()
    match = re.search(r'\d{4}', s)
    return match.group(0) if match else s

def extrair_numero(row):
    num_col = str(row.get('decreto_numero', '')).replace('.0', '').strip()
    if num_col and num_col != 'nan' and num_col != '':
        return num_col
    link = str(row.get('link_decreto', '')).strip()
    match = re.match(r'^(\d+)', link)
    return match.group(1) if match else ''

def carregar_dados():
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            df = pd.read_sql("SELECT * FROM decretos", engine)
            if not df.empty:
                df['exercicio_decreto'] = df['exercicio_decreto'].apply(limpar_ano)
                df['decreto_numero'] = df.apply(extrair_numero, axis=1)
                if 'data_elaboracao' in df.columns:
                    df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
                return df.fillna('').to_dict('records')
        except Exception as e:
            print(f"Erro ao ler Neon: {e}")

    # Fallback Google Drive
    url = "https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv"
    try:
        df = pd.read_csv(url).iloc[:, :7]
        df.columns = [
            'exercicio_decreto', 'decreto_numero', 'data_elaboracao',
            'orgao_elaboracao', 'link_decreto', 'complemento_informacoes', 'processo_sei'
        ]
        df['exercicio_decreto'] = df['exercicio_decreto'].apply(limpar_ano)
        df['decreto_numero'] = df.apply(extrair_numero, axis=1)
        df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
        df = df.drop(columns=['complemento_informacoes'], errors='ignore')
        return df.fillna('').to_dict('records')
    except Exception as e:
        print(f"Erro Drive: {e}")
        return []

@ui.page('/')
def main_page():
    ui.colors(primary='#1e3a8a')
    dados = carregar_dados()

    with ui.header().classes('bg-blue-900 text-white p-4 flex justify-between items-center shadow-md'):
        ui.label('Prefeitura de Francisco Morato — Decretos').classes('text-xl font-bold')

    with ui.column().classes('w-full p-6 max-w-7xl mx-auto'):
        ui.label('Consulta Pública de Decretos Municipais').classes('text-2xl font-bold text-gray-800 mb-1')
        ui.label('Pesquise por nome, número do decreto, órgão ou processo SEI. Dê dois cliques em uma linha para editar.').classes('text-gray-600 mb-4')

        # PAINEL FIXO DE CADASTRO
        with ui.expansion('➕ Cadastrar Novo Decreto', icon='add').classes('w-full bg-blue-50 border border-blue-200 rounded-lg mb-6 p-2'):
            with ui.grid(columns=3).classes('w-full gap-4 p-2'):
                add_ano = ui.input('Ano', placeholder='Ex: 2026')
                add_num = ui.input('Número Decreto "G"', placeholder='Ex: 105')
                add_data = ui.input('Data (DD/MM/AAAA)', placeholder='Ex: 14/10/2026')
                add_orgao = ui.input('Órgão de Elaboração', placeholder='Ex: Coordenadoria...')
                add_sei = ui.input('Processo SEI', placeholder='Ex: 17129/2025')
                add_link = ui.input('Link / Nome do Arquivo', placeholder='Ex: 10 Nomeação...pdf')

            def salvar_novo():
                novo = {
                    'exercicio_decreto': add_ano.value,
                    'decreto_numero': add_num.value,
                    'data_elaboracao': add_data.value,
                    'orgao_elaboracao': add_orgao.value,
                    'processo_sei': add_sei.value,
                    'link_decreto': add_link.value
                }
                if DATABASE_URL:
                    try:
                        engine = create_engine(DATABASE_URL)
                        pd.DataFrame([novo]).to_sql('decretos', engine, if_exists='append', index=False)
                        ui.notify('Decreto cadastrado!', type='positive')
                    except Exception as err:
                        ui.notify(f'Erro: {err}', type='negative')

                dados.insert(0, novo)
                tabela.rows = dados
                add_ano.value = add_num.value = add_data.value = add_orgao.value = add_sei.value = add_link.value = ''

            ui.button('Salvar Decreto', on_click=salvar_novo).classes('bg-green-700 text-white font-bold mt-2')

        # FILTROS
        anos_disponiveis = sorted(list(set(str(d.get('exercicio_decreto', '')).strip() for d in dados if d.get('exercicio_decreto'))), reverse=True)
        opcoes_ano = ['Todos os Anos'] + anos_disponiveis

        with ui.row().classes('w-full gap-4 mb-4 items-center'):
            search_input = ui.input(placeholder='🔍 Digite para pesquisar...').classes('flex-1 shadow-sm')
            select_ano = ui.select(options=opcoes_ano, value='Todos os Anos', label='Filtrar por Ano').classes('w-48 shadow-sm')

        # COLUNAS (Sem complemento e com Link responsivo)
        colunas = [
            {'name': 'exercicio_decreto', 'label': 'Ano', 'field': 'exercicio_decreto', 'sortable': True, 'align': 'center', 'classes': 'w-20'},
            {'name': 'decreto_numero', 'label': 'Decreto “G”', 'field': 'decreto_numero', 'sortable': True, 'align': 'center', 'classes': 'w-28 font-bold'},
            {'name': 'data_elaboracao', 'label': 'Data', 'field': 'data_elaboracao', 'sortable': True, 'align': 'center', 'classes': 'w-32'},
            {'name': 'orgao_elaboracao', 'label': 'Elaboração', 'field': 'orgao_elaboracao', 'align': 'left', 'classes': 'w-48'},
            {'name': 'processo_sei', 'label': 'Processo SEI', 'field': 'processo_sei', 'align': 'left', 'classes': 'w-40'},
            {'name': 'link_decreto', 'label': 'Link / Documento', 'field': 'link_decreto', 'align': 'left', 'classes': 'break-words max-w-xl'}
        ]

        tabela = ui.table(
            columns=colunas,
            rows=dados,
            row_key='link_decreto',
            pagination=15
        ).classes('w-full shadow-lg rounded-lg border')

        # RENDERIZADOR DE LINK AUTO-AJUSTÁVEL
        tabela.add_slot('body-cell-link_decreto', '''
            <q-td :props="props" class="whitespace-normal break-all">
                <template v-if="props.value">
                    <a v-if="props.value.startsWith('http')" :href="props.value" target="_blank" class="text-blue-600 underline font-medium hover:text-blue-800">
                        {{ props.value }} ↗
                    </a>
                    <a v-else :href="'https://drive.google.com/drive/search?q=' + encodeURIComponent(props.value)" target="_blank" class="text-blue-600 underline font-medium hover:text-blue-800">
                        {{ props.value }} ↗
                    </a>
                </template>
                <span v-else class="text-gray-400">-</span>
            </q-td>
        ''')

        # MODAL DE EDIÇÃO AO DAR DUPLO CLIQUE
        with ui.dialog() as modal_edicao, ui.card().classes('w-full max-w-lg p-6'):
            ui.label('Editar Decreto').classes('text-xl font-bold mb-4 text-blue-900')
            edit_ano = ui.input('Ano')
            edit_num = ui.input('Número Decreto "G"')
            edit_data = ui.input('Data')
            edit_orgao = ui.input('Órgão de Elaboração')
            edit_sei = ui.input('Processo SEI')
            edit_link = ui.input('Link / Nome do Arquivo')
            linha_selecionada = {}

            def salvar_edicao():
                linha_selecionada['exercicio_decreto'] = edit_ano.value
                linha_selecionada['decreto_numero'] = edit_num.value
                linha_selecionada['data_elaboracao'] = edit_data.value
                linha_selecionada['orgao_elaboracao'] = edit_orgao.value
                linha_selecionada['processo_sei'] = edit_sei.value
                linha_selecionada['link_decreto'] = edit_link.value
                tabela.update()
                modal_edicao.close()
                ui.notify('Decreto atualizado na visualização!', type='positive')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=modal_edicao.close).classes('bg-gray-400 text-white')
                ui.button('Salvar Alterações', on_click=salvar_edicao).classes('bg-blue-900 text-white font-bold')

        def on_row_dblclick(e):
            nonlocal linha_selecionada
            linha_selecionada = e.args[1]
            edit_ano.value = linha_selecionada.get('exercicio_decreto', '')
            edit_num.value = linha_selecionada.get('decreto_numero', '')
            edit_data.value = linha_selecionada.get('data_elaboracao', '')
            edit_orgao.value = linha_selecionada.get('orgao_elaboracao', '')
            edit_sei.value = linha_selecionada.get('processo_sei', '')
            edit_link.value = linha_selecionada.get('link_decreto', '')
            modal_edicao.open()

        tabela.on('row-dblclick', on_row_dblclick)

        # LÓGICA DE FILTRAGEM
        def aplicar_filtros():
            texto_busca = search_input.value.lower() if search_input.value else ''
            ano_sel = select_ano.value

            def filtrar_linha(row):
                if ano_sel != 'Todos os Anos' and str(row.get('exercicio_decreto', '')).strip() != ano_sel:
                    return False
                if texto_busca:
                    valores = ' '.join(str(v) for v in row.values()).lower()
                    return texto_busca in valores
                return True

            tabela.rows = [d for d in dados if filtrar_linha(d)]

        search_input.on('update:model-value', aplicar_filtros)
        select_ano.on('update:model-value', aplicar_filtros)

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host='0.0.0.0', port=PORT, reload=False)
