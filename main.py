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
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            df = pd.read_sql("SELECT * FROM decretos", engine)
            if not df.empty:
                # Trata formatação de datas
                if 'data_elaboracao' in df.columns:
                    df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
                return df.fillna('').to_dict('records')
        except Exception as e:
            print(f"Erro ao ler do Neon: {e}. Carregando do Drive...")

    # Fallback direto do Google Drive
    url = "https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv"
    try:
        df = pd.read_csv(url).iloc[:, :7]
        df.columns = [
            'exercicio_decreto', 'decreto_numero', 'data_elaboracao',
            'orgao_elaboracao', 'link_decreto', 'complemento_informacoes', 'processo_sei'
        ]
        
        # Corrige extração de ano e decreto se estiverem grudados
        df['exercicio_decreto'] = df['exercicio_decreto'].astype(str).str.strip()
        df['decreto_numero'] = df['exercicio_decreto'].apply(lambda x: x[4:] if len(x) > 4 else '')
        df['exercicio_decreto'] = df['exercicio_decreto'].apply(lambda x: x[:4] if len(x) >= 4 else x)
        
        df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
        return df.fillna('').to_dict('records')
    except Exception as e:
        print(f"Erro ao carregar do Drive: {e}")
        return []

@ui.page('/')
def main_page():
    ui.colors(primary='#1e3a8a')
    dados = carregar_dados()

    # Cabeçalho Principal
    with ui.header().classes('bg-blue-900 text-white p-4 flex justify-between items-center shadow-md'):
        ui.label('Prefeitura de Francisco Morato — Decretos').classes('text-xl font-bold')
        
        # Botão para abrir o Modal de Novo Decreto
        ui.button('➕ Adicionar Decreto', on_click=lambda: modal_cadastro.open()).classes('bg-green-600 hover:bg-green-700 text-white font-bold')

    with ui.column().classes('w-full p-6 max-w-7xl mx-auto'):
        ui.label('Consulta Pública de Decretos Municipais').classes('text-2xl font-bold text-gray-800 mb-1')
        ui.label('Pesquise por nome, rua, lote, número do decreto, órgão ou processo SEI.').classes('text-gray-600 mb-6')

        # Extrai lista de anos únicos para o filtro dropdown
        anos_disponiveis = sorted(list(set(str(d.get('exercicio_decreto', '')).strip() for d in dados if d.get('exercicio_decreto'))), reverse=True)
        opcoes_ano = ['Todos os Anos'] + anos_disponiveis

        # Barra de Filtros
        with ui.row().classes('w-full gap-4 mb-4 items-center'):
            search_input = ui.input(placeholder='🔍 Digite para pesquisar em toda a tabela...').classes('flex-1 shadow-sm')
            select_ano = ui.select(options=opcoes_ano, value='Todos os Anos', label='Filtrar por Ano').classes('w-48 shadow-sm')

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

            tabela = ui.table(
                columns=colunas,
                rows=dados,
                row_key='exercicio_decreto',
                pagination=15
            ).classes('w-full shadow-lg rounded-lg border')

            # Renderização de Links Seguros
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

            # Lógica Combinada dos Filtros (Busca Geral + Filtro por Ano)
            def aplicar_filtros():
                texto_busca = search_input.value.lower() if search_input.value else ''
                ano_sel = select_ano.value

                def filtrar_linha(row):
                    # Filtro por ano
                    if ano_sel != 'Todos os Anos' and str(row.get('exercicio_decreto', '')).strip() != ano_sel:
                        return False
                    
                    # Filtro por texto
                    if texto_busca:
                        valores = ' '.join(str(v) for v in row.values()).lower()
                        return texto_busca in valores
                    return True

                tabela.rows = [d for d in dados if filtrar_linha(d)]

            search_input.on('update:model-value', aplicar_filtros)
            select_ano.on('update:model-value', aplicar_filtros)

        # MODAL / DIÁLOGO DE CADASTRO DE DECRETO
        with ui.dialog() as modal_cadastro, ui.card().classes('w-full max-w-lg p-6'):
            ui.label('Cadastrar Novo Decreto').classes('text-xl font-bold mb-4 text-blue-900')
            
            in_exercicio = ui.input('Ano (Exercicio)', placeholder='Ex: 2026').classes('w-full')
            in_numero = ui.input('Número do Decreto "G"', placeholder='Ex: 105').classes('w-full')
            in_data = ui.input('Data (DD/MM/AAAA)', placeholder='Ex: 14/10/2026').classes('w-full')
            in_orgao = ui.input('Órgão de Elaboração', placeholder='Ex: Coordenadoria de Assuntos de Secretaria').classes('w-full')
            in_sei = ui.input('Processo SEI', placeholder='Ex: 3516309.433.00006204/2026-15').classes('w-full')
            in_complemento = ui.textarea('Complemento / Informações (Ruas, Lotes, Nomes)', placeholder='Digite o resumo ou detalhes').classes('w-full')
            in_link = ui.input('Link ou Nome do Arquivo do Decreto', placeholder='Ex: Decreto 105 G - ...pdf ou URL do Drive').classes('w-full')

            def salvar_decreto():
                novo_registro = {
                    'exercicio_decreto': in_exercicio.value,
                    'decreto_numero': in_numero.value,
                    'data_elaboracao': in_data.value,
                    'orgao_elaboracao': in_orgao.value,
                    'processo_sei': in_sei.value,
                    'complemento_informacoes': in_complemento.value,
                    'link_decreto': in_link.value
                }

                # Salva no banco PostgreSQL Neon
                if DATABASE_URL:
                    try:
                        engine = create_engine(DATABASE_URL)
                        df_novo = pd.DataFrame([novo_registro])
                        df_novo.to_sql('decretos', engine, if_exists='append', index=False)
                        ui.notify('Decreto cadastrado com sucesso no banco Neon!', type='positive')
                    except Exception as err:
                        ui.notify(f'Erro ao salvar no banco: {err}', type='negative')

                # Adiciona localmente na tabela NiceGUI na hora
                dados.insert(0, novo_registro)
                tabela.rows = dados
                modal_cadastro.close()

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=modal_cadastro.close).classes('bg-gray-400 text-white')
                ui.button('Salvar Decreto', on_click=salvar_decreto).classes('bg-blue-900 text-white font-bold')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host='0.0.0.0', port=PORT, reload=False)
