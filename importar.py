import os
import re
import pandas as pd
from sqlalchemy import create_engine, text
from nicegui import ui

RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

PORT = int(os.environ.get('PORT', 8080))

def carregar_dados():
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            df = pd.read_sql("SELECT * FROM decretos ORDER BY id ASC", engine)
            if not df.empty:
                return df.fillna('').to_dict('records')
        except Exception as e:
            print(f"Erro ao ler banco Neon: {e}")

    # Fallback caso o banco falhe
    url = "https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv"
    try:
        df = pd.read_csv(url).iloc[:, :6]
        df.columns = ['col0', 'col1', 'col2', 'col3', 'col4', 'col5']
        
        registros = []
        for idx, r in df.iterrows():
            col0 = str(r['col0']).replace('.0', '').strip()
            ano = col0[:4] if len(col0) >= 4 else col0
            num = str(r['col1']).replace('.0', '').strip()
            if not num or num == 'nan':
                if len(col0) > 4:
                    num = col0[4:]
                else:
                    link_s = str(r['col5']).strip()
                    m = re.search(r'Decreto\s+(\d+)', link_s, re.IGNORECASE)
                    num = str(int(m.group(1))) if m else ''

            registros.append({
                'id': idx + 1,
                'exercicio_decreto': ano,
                'decreto_numero': num,
                'data_elaboracao': str(r['col2']),
                'orgao_elaboracao': str(r['col3']),
                'processo_sei': str(r['col4']),
                'link_decreto': str(r['col5'])
            })
        return registros
    except Exception as e:
        print(f"Erro ao carregar Google Drive: {e}")
        return []

@ui.page('/')
def main_page():
    ui.colors(primary='#1e3a8a')
    dados = carregar_dados()

    with ui.header().classes('bg-blue-900 text-white p-4 flex justify-between items-center shadow-md'):
        ui.label('Prefeitura de Francisco Morato — Decretos').classes('text-xl font-bold')

    with ui.column().classes('w-full p-6 max-w-7xl mx-auto'):
        ui.label('Consulta Pública de Decretos Municipais').classes('text-2xl font-bold text-gray-800 mb-1')
        ui.label('Pesquise por ano, número do decreto, órgão ou processo SEI. Dê dois cliques para editar uma linha.').classes('text-gray-600 mb-4')

        # PAINEL FIXO PARA ADICIONAR NOVO DECRETO
        with ui.expansion('➕ Cadastrar Novo Decreto', icon='add').classes('w-full bg-blue-50 border border-blue-200 rounded-lg mb-6 p-2'):
            with ui.grid(columns=3).classes('w-full gap-4 p-2'):
                add_ano = ui.input('Ano', placeholder='Ex: 2026')
                add_num = ui.input('Número Decreto "G"', placeholder='Ex: 105')
                add_data = ui.input('Data (DD/MM/AAAA)', placeholder='Ex: 14/10/2026')
                add_orgao = ui.input('Órgão de Elaboração', placeholder='Ex: Coordenadoria...')
                add_sei = ui.input('Processo SEI', placeholder='Ex: 17129/2025')
                add_link = ui.input('Link / Nome do Arquivo', placeholder='Ex: Decreto 105 G...pdf')

            def salvar_novo():
                novo_id = (max([d.get('id', 0) for d in dados]) + 1) if dados else 1
                novo = {
                    'id': novo_id,
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
                        with engine.connect() as conn:
                            query = text("""
                                INSERT INTO decretos (id, exercicio_decreto, decreto_numero, data_elaboracao, orgao_elaboracao, processo_sei, link_decreto)
                                VALUES (:id, :exercicio_decreto, :decreto_numero, :data_elaboracao, :orgao_elaboracao, :processo_sei, :link_decreto)
                            """)
                            conn.execute(query, novo)
                            conn.commit()
                        ui.notify('Decreto gravado no Banco Neon!', type='positive')
                    except Exception as err:
                        ui.notify(f'Erro ao salvar: {err}', type='negative')

                dados.insert(0, novo)
                tabela.rows = dados
                add_ano.value = add_num.value = add_data.value = add_orgao.value = add_sei.value = add_link.value = ''

            ui.button('Salvar Decreto', on_click=salvar_novo).classes('bg-green-700 text-white font-bold mt-2')

        # BARRA DE FILTROS
        anos_disponiveis = sorted(list(set(str(d.get('exercicio_decreto', '')).strip() for d in dados if d.get('exercicio_decreto'))), reverse=True)
        opcoes_ano = ['Todos os Anos'] + anos_disponiveis

        with ui.row().classes('w-full gap-4 mb-4 items-center'):
            search_input = ui.input(placeholder='🔍 Digite para pesquisar...').classes('flex-1 shadow-sm')
            select_ano = ui.select(options=opcoes_ano, value='Todos os Anos', label='Filtrar por Ano').classes('w-48 shadow-sm')

        # COLUNAS
        colunas = [
            {'name': 'exercicio_decreto', 'label': 'Ano', 'field': 'exercicio_decreto', 'sortable': True, 'align': 'center', 'classes': 'w-20'},
            {'name': 'decreto_numero', 'label': 'Decreto “G”', 'field': 'decreto_numero', 'sortable': True, 'align': 'center', 'classes': 'w-28 font-bold'},
            {'name': 'data_elaboracao', 'label': 'Data', 'field': 'data_elaboracao', 'sortable': True, 'align': 'center', 'classes': 'w-32'},
            {'name': 'orgao_elaboracao', 'label': 'Elaboração', 'field': 'orgao_elaboracao', 'align': 'left', 'classes': 'w-56'},
            {'name': 'processo_sei', 'label': 'Processo SEI', 'field': 'processo_sei', 'align': 'left', 'classes': 'w-40'},
            {'name': 'link_decreto', 'label': 'Link / Documento', 'field': 'link_decreto', 'align': 'left', 'classes': 'break-words max-w-xl'}
        ]

        tabela = ui.table(
            columns=colunas,
            rows=dados,
            row_key='id',
            pagination=15
        ).classes('w-full shadow-lg rounded-lg border')

        # AUTO-AJUSTE E LINK NATIVO
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

        # MODAL DE EDIÇÃO PERSISTENTE (DUPLO CLIQUE)
        with ui.dialog() as modal_edicao, ui.card().classes('w-full max-w-lg p-6'):
            ui.label('Editar Decreto').classes('text-xl font-bold mb-4 text-blue-900')
            edit_ano = ui.input('Ano')
            edit_num = ui.input('Número Decreto "G"')
            edit_data = ui.input('Data')
            edit_orgao = ui.input('Órgão de Elaboração')
            edit_sei = ui.input('Processo SEI')
            edit_link = ui.input('Link / Nome do Arquivo')
            linha_atual = {}

            def salvar_edicao():
                linha_atual['exercicio_decreto'] = edit_ano.value
                linha_atual['decreto_numero'] = edit_num.value
                linha_atual['data_elaboracao'] = edit_data.value
                linha_atual['orgao_elaboracao'] = edit_orgao.value
                linha_atual['processo_sei'] = edit_sei.value
                linha_atual['link_decreto'] = edit_link.value

                if DATABASE_URL and 'id' in linha_atual:
                    try:
                        engine = create_engine(DATABASE_URL)
                        with engine.connect() as conn:
                            query = text("""
                                UPDATE decretos 
                                SET exercicio_decreto = :exercicio_decreto,
                                    decreto_numero = :decreto_numero,
                                    data_elaboracao = :data_elaboracao,
                                    orgao_elaboracao = :orgao_elaboracao,
                                    processo_sei = :processo_sei,
                                    link_decreto = :link_decreto
                                WHERE id = :id
                            """)
                            conn.execute(query, linha_atual)
                            conn.commit()
                        ui.notify('Atualizado no banco Neon!', type='positive')
                    except Exception as err:
                        ui.notify(f'Erro ao atualizar: {err}', type='negative')

                tabela.update()
                modal_edicao.close()

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=modal_edicao.close).classes('bg-gray-400 text-white')
                ui.button('Salvar Alterações', on_click=salvar_edicao).classes('bg-blue-900 text-white font-bold')

        def on_row_dblclick(e):
            nonlocal linha_atual
            linha_atual = e.args[1]
            edit_ano.value = str(linha_atual.get('exercicio_decreto', ''))
            edit_num.value = str(linha_atual.get('decreto_numero', ''))
            edit_data.value = str(linha_atual.get('data_elaboracao', ''))
            edit_orgao.value = str(linha_atual.get('orgao_elaboracao', ''))
            edit_sei.value = str(linha_atual.get('processo_sei', ''))
            edit_link.value = str(linha_atual.get('link_decreto', ''))
            modal_edicao.open()

        tabela.on('row-dblclick', on_row_dblclick)

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
