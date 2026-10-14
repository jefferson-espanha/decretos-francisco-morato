import os
import re
import uuid

import pandas as pd
from sqlalchemy import create_engine
from nicegui import ui

RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if RAW_DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = RAW_DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

PORT = int(os.environ.get('PORT', 8080))

COLUNAS_DADOS = [
    'exercicio_decreto',
    'decreto_numero',
    'data_elaboracao',
    'orgao_elaboracao',
    'link_decreto',
    'complemento_informacoes',
    'processo_sei',
]


def texto_limpo(valor):
    """Converte valores vazios/nulos em texto e remove espaços externos."""
    if valor is None:
        return ''
    try:
        if pd.isna(valor):
            return ''
    except (TypeError, ValueError):
        pass
    return str(valor).strip()


def normalizar_ano(valor):
    """Evita apresentar anos numéricos como 2026.0."""
    ano = texto_limpo(valor)
    if re.fullmatch(r'\d{4}\.0+', ano):
        return ano.split('.', 1)[0]
    return ano


def normalizar_numero(valor):
    """Remove o sufixo decimal .0 de números inteiros vindos da planilha/banco."""
    numero = texto_limpo(valor)
    if re.fullmatch(r'\d+\.0+', numero):
        return numero.split('.', 1)[0]
    return numero


def formatar_data(valor):
    data = texto_limpo(valor)
    if not data:
        return ''
    convertida = pd.to_datetime(data, dayfirst=True, errors='coerce')
    if pd.isna(convertida):
        return data
    return convertida.strftime('%d/%m/%Y')


def normalizar_registros(registros):
    """Normaliza campos sem sobrescrever o número de decreto já fornecido."""
    normalizados = []
    for registro in registros:
        linha = dict(registro)
        ano_original = texto_limpo(linha.get('exercicio_decreto', ''))
        numero_original = texto_limpo(linha.get('decreto_numero', ''))

        # Compatibilidade com planilhas antigas que juntavam ano e número
        # na primeira coluna (por exemplo, 2026105). 2026.0 não é dividido.
        if not numero_original and re.fullmatch(r'\d{5,}', ano_original):
            ano_original, numero_original = ano_original[:4], ano_original[4:]

        linha['exercicio_decreto'] = normalizar_ano(ano_original)
        linha['decreto_numero'] = normalizar_numero(numero_original)
        linha['data_elaboracao'] = formatar_data(linha.get('data_elaboracao', ''))

        for campo in COLUNAS_DADOS:
            linha.setdefault(campo, '')
            if campo not in ('exercicio_decreto', 'decreto_numero', 'data_elaboracao'):
                linha[campo] = texto_limpo(linha.get(campo, ''))

        # Chave única da interface, independente de ano/número repetidos.
        linha['_row_key'] = uuid.uuid4().hex
        normalizados.append(linha)
    return normalizados


def carregar_dados():
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            df = pd.read_sql('SELECT * FROM decretos', engine)
            if not df.empty:
                return normalizar_registros(df.to_dict('records'))
        except Exception as e:
            print(f'Erro ao ler do Neon: {e}. Carregando do Drive...')

    # Fallback direto do Google Drive
    url = 'https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv'
    try:
        df = pd.read_csv(url, dtype=str).iloc[:, :len(COLUNAS_DADOS)].copy()
        while len(df.columns) < len(COLUNAS_DADOS):
            df[f'coluna_extra_{len(df.columns)}'] = ''
        df.columns = COLUNAS_DADOS
        return normalizar_registros(df.to_dict('records'))
    except Exception as e:
        print(f'Erro ao carregar do Drive: {e}')
        return []


@ui.page('/')
def main_page():
    ui.colors(primary='#1e3a8a')
    dados = carregar_dados()

    with ui.header().classes('bg-blue-900 text-white p-4 flex justify-between items-center shadow-md'):
        ui.label('Prefeitura de Francisco Morato — Decretos').classes('text-xl font-bold')
        ui.button(
            '➕ Adicionar Decreto',
            on_click=lambda: modal_cadastro.open(),
        ).classes('bg-green-600 hover:bg-green-700 text-white font-bold')

    with ui.column().classes('w-full p-6 max-w-7xl mx-auto'):
        ui.label('Consulta Pública de Decretos Municipais').classes(
            'text-2xl font-bold text-gray-800 mb-1'
        )
        ui.label(
            'Pesquise por nome, rua, lote, número do decreto, órgão ou processo SEI.'
        ).classes('text-gray-600 mb-6')

        anos_disponiveis = sorted(
            {
                normalizar_ano(d.get('exercicio_decreto', ''))
                for d in dados
                if normalizar_ano(d.get('exercicio_decreto', ''))
            },
            reverse=True,
        )
        opcoes_ano = ['Todos os Anos'] + anos_disponiveis

        with ui.row().classes('w-full gap-4 mb-4 items-center'):
            search_input = ui.input(
                placeholder='🔍 Digite para pesquisar em toda a tabela...'
            ).classes('flex-1 shadow-sm')
            select_ano = ui.select(
                options=opcoes_ano,
                value='Todos os Anos',
                label='Filtrar por Ano',
            ).classes('w-48 shadow-sm')

        colunas = [
            {
                'name': 'exercicio_decreto',
                'label': 'Ano',
                'field': 'exercicio_decreto',
                'sortable': True,
                'align': 'center',
                'style': 'min-width: 85px;',
                'headerStyle': 'min-width: 85px;',
            },
            {
                'name': 'decreto_numero',
                'label': 'Decreto “G”',
                'field': 'decreto_numero',
                'sortable': True,
                'align': 'center',
                'style': 'min-width: 115px;',
                'headerStyle': 'min-width: 115px;',
            },
            {
                'name': 'data_elaboracao',
                'label': 'Data',
                'field': 'data_elaboracao',
                'sortable': True,
                'align': 'center',
                'style': 'min-width: 115px;',
                'headerStyle': 'min-width: 115px;',
            },
            {
                'name': 'orgao_elaboracao',
                'label': 'Elaboração',
                'field': 'orgao_elaboracao',
                'align': 'left',
                'style': 'min-width: 190px; white-space: normal;',
                'headerStyle': 'min-width: 190px;',
            },
            {
                'name': 'processo_sei',
                'label': 'Processo SEI',
                'field': 'processo_sei',
                'align': 'left',
                'style': 'min-width: 190px; white-space: normal;',
                'headerStyle': 'min-width: 190px;',
            },
            {
                'name': 'link_decreto',
                'label': 'Link',
                'field': 'link_decreto',
                'align': 'center',
                'style': 'min-width: 280px; width: 30%; white-space: normal;',
                'headerStyle': 'min-width: 280px; width: 30%;',
            },
        ]

        tabela = ui.table(
            columns=colunas,
            rows=dados,
            row_key='_row_key',
            pagination=15,
        ).classes('w-full shadow-lg rounded-lg border').props(
            'table-style="width: 100%; table-layout: auto;"'
        )

        tabela.add_slot('body-cell-link_decreto', '''
            <q-td :props="props" style="min-width: 280px; white-space: normal; overflow-wrap: anywhere;">
                <template v-if="props.value">
                    <a v-if="String(props.value).startsWith('http')"
                       :href="props.value" target="_blank" rel="noopener noreferrer"
                       class="text-blue-600 underline font-medium hover:text-blue-800">
                        Abrir ↗
                    </a>
                    <a v-else
                       :href="'https://drive.google.com/drive/search?q=' + encodeURIComponent(props.value)"
                       target="_blank" rel="noopener noreferrer"
                       class="text-blue-600 underline font-medium hover:text-blue-800">
                        {{ props.value }} ↗
                    </a>
                </template>
                <span v-else class="text-gray-400">-</span>
            </q-td>
        ''')

        campos_busca = (
            'exercicio_decreto',
            'decreto_numero',
            'data_elaboracao',
            'orgao_elaboracao',
            'processo_sei',
            'link_decreto',
        )

        def aplicar_filtros():
            texto_busca = (search_input.value or '').strip().lower()
            ano_sel = select_ano.value

            def filtrar_linha(row):
                if ano_sel != 'Todos os Anos' and normalizar_ano(
                    row.get('exercicio_decreto', '')
                ) != ano_sel:
                    return False
                if texto_busca:
                    valores = ' '.join(texto_limpo(row.get(campo, '')) for campo in campos_busca)
                    return texto_busca in valores.lower()
                return True

            tabela.rows = [linha for linha in dados if filtrar_linha(linha)]

        search_input.on('update:model-value', aplicar_filtros)
        select_ano.on('update:model-value', aplicar_filtros)

        with ui.dialog() as modal_cadastro, ui.card().classes('w-full max-w-lg p-6'):
            ui.label('Cadastrar Novo Decreto').classes('text-xl font-bold mb-4 text-blue-900')

            in_exercicio = ui.input('Ano (Exercício)', placeholder='Ex: 2026').classes('w-full')
            in_numero = ui.input('Número do Decreto "G"', placeholder='Ex: 105').classes('w-full')
            in_data = ui.input('Data (DD/MM/AAAA)', placeholder='Ex: 14/10/2026').classes('w-full')
            in_orgao = ui.input(
                'Órgão de Elaboração',
                placeholder='Ex: Coordenadoria de Assuntos de Secretaria',
            ).classes('w-full')
            in_sei = ui.input(
                'Processo SEI',
                placeholder='Ex: 3516309.433.00006204/2026-15',
            ).classes('w-full')
            in_link = ui.input(
                'Link ou Nome do Arquivo do Decreto',
                placeholder='Ex: Decreto 105 G - ...pdf ou URL do Drive',
            ).classes('w-full')

            def salvar_decreto():
                novo_registro = {
                    'exercicio_decreto': normalizar_ano(in_exercicio.value),
                    'decreto_numero': normalizar_numero(in_numero.value),
                    'data_elaboracao': formatar_data(in_data.value),
                    'orgao_elaboracao': texto_limpo(in_orgao.value),
                    'processo_sei': texto_limpo(in_sei.value),
                    # Mantém compatibilidade com o esquema existente sem exibir
                    # nem solicitar este campo no formulário.
                    'complemento_informacoes': '',
                    'link_decreto': texto_limpo(in_link.value),
                    '_row_key': uuid.uuid4().hex,
                }

                if DATABASE_URL:
                    try:
                        engine = create_engine(DATABASE_URL)
                        registro_banco = {
                            chave: valor
                            for chave, valor in novo_registro.items()
                            if chave != '_row_key'
                        }
                        pd.DataFrame([registro_banco]).to_sql(
                            'decretos', engine, if_exists='append', index=False
                        )
                        ui.notify('Decreto cadastrado com sucesso no banco Neon!', type='positive')
                    except Exception as err:
                        ui.notify(f'Erro ao salvar no banco: {err}', type='negative')
                        return

                dados.insert(0, novo_registro)
                if novo_registro['exercicio_decreto'] not in opcoes_ano:
                    opcoes_ano.append(novo_registro['exercicio_decreto'])
                    opcoes_ano[1:] = sorted(opcoes_ano[1:], reverse=True)
                    select_ano.options = opcoes_ano
                    select_ano.update()
                aplicar_filtros()
                modal_cadastro.close()

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=modal_cadastro.close).classes('bg-gray-400 text-white')
                ui.button('Salvar Decreto', on_click=salvar_decreto).classes(
                    'bg-blue-900 text-white font-bold'
                )


if __name__ in {'__main__', '__mp_main__'}:
    ui.run(host='0.0.0.0', port=PORT, reload=False)
