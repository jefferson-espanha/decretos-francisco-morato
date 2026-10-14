import os
import re
import unicodedata
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

URL_PLANILHA = 'https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv'
ARQUIVO_ASSUNTOS_LINKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'decreto_assuntos_links.csv')

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
        linha['assunto_decreto'] = texto_limpo(linha.get('assunto_decreto', ''))
        if not linha['assunto_decreto']:
            complemento = texto_limpo(linha.get('complemento_informacoes', ''))
            if complemento.startswith('ASSUNTO: '):
                linha['assunto_decreto'] = complemento.removeprefix('ASSUNTO: ').strip()

        for campo in COLUNAS_DADOS:
            linha.setdefault(campo, '')
            if campo not in ('exercicio_decreto', 'decreto_numero', 'data_elaboracao'):
                linha[campo] = texto_limpo(linha.get(campo, ''))

        # Chave única da interface, independente de ano/número repetidos.
        linha['_row_key'] = uuid.uuid4().hex
        normalizados.append(linha)
    return normalizados


def normalizar_cabecalho(valor):
    sem_acento = unicodedata.normalize('NFKD', str(valor))
    sem_acento = ''.join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', sem_acento.lower()).strip()


def carregar_planilha():
    """Lê a planilha pelo nome dos cabeçalhos, não pela posição das colunas."""
    df = pd.read_csv(URL_PLANILHA, dtype=str)
    cabecalhos = {normalizar_cabecalho(coluna): coluna for coluna in df.columns}

    def encontrar_coluna(*nomes, inicio=None):
        for nome in nomes:
            chave = normalizar_cabecalho(nome)
            if chave in cabecalhos:
                return cabecalhos[chave]
        if inicio:
            chave_inicio = normalizar_cabecalho(inicio)
            for chave, coluna in cabecalhos.items():
                if chave.startswith(chave_inicio):
                    return coluna
        return None

    fontes = {
        'exercicio_decreto': encontrar_coluna('Exercicio', 'Exercício', 'Ano'),
        'decreto_numero': encontrar_coluna('Decreto G', 'Decreto Numero', 'Número do Decreto G'),
        'data_elaboracao': encontrar_coluna('Data', 'Data Elaboracao'),
        'orgao_elaboracao': encontrar_coluna('Elaboracao', 'Orgao Elaboracao'),
        'processo_sei': encontrar_coluna('Processo SEI'),
        'link_decreto': encontrar_coluna('Link do Decreto', 'Link Decreto'),
        'complemento_informacoes': encontrar_coluna(inicio='Complemento'),
    }

    resultado = pd.DataFrame(index=df.index)
    for campo, coluna in fontes.items():
        resultado[campo] = df[coluna] if coluna else ''
    registros = normalizar_registros(resultado.to_dict('records'))
    return [
        registro for registro in registros
        if registro['exercicio_decreto'] and registro['decreto_numero']
    ]


def carregar_banco():
    if not DATABASE_URL:
        return []
    try:
        engine = create_engine(DATABASE_URL)
        df = pd.read_sql('SELECT * FROM decretos', engine)
        return normalizar_registros(df.to_dict('records')) if not df.empty else []
    except Exception as e:
        print(f'Erro ao ler do Neon: {e}')
        return []


def aplicar_assuntos_e_links(registros):
    """Aplica assunto e link individual, usando ano+número como chave."""
    try:
        df = pd.read_csv(ARQUIVO_ASSUNTOS_LINKS, dtype=str).fillna('')
        mapa = {
            (normalizar_ano(linha['exercicio_decreto']), normalizar_numero(linha['decreto_numero'])):
                (texto_limpo(linha['assunto_decreto']), texto_limpo(linha['link_decreto']))
            for _, linha in df.iterrows()
        }
    except Exception as e:
        print(f'Erro ao carregar assuntos/links individuais: {e}')
        mapa = {}

    for registro in registros:
        chave = (
            normalizar_ano(registro.get('exercicio_decreto', '')),
            normalizar_numero(registro.get('decreto_numero', '')),
        )
        link_existente = texto_limpo(registro.get('link_decreto', ''))
        if not registro.get('assunto_decreto') and link_existente and not link_existente.lower().startswith(('http://', 'https://')):
            registro['assunto_decreto'] = link_existente

        assunto_mapa, link_mapa = mapa.get(chave, ('', ''))
        if assunto_mapa:
            registro['assunto_decreto'] = assunto_mapa
        if link_mapa.lower().startswith(('http://', 'https://')):
            registro['link_decreto'] = link_mapa
        elif not link_existente.lower().startswith(('http://', 'https://')):
            # Nome de arquivo não é URL: não transforma o texto em busca ampla do Drive.
            registro['link_decreto'] = ''

    return registros


def carregar_dados():
    # A planilha oficial contém Exercicio e Decreto “G” em colunas distintas.
    # Ela é usada como referência quando o banco tem números vazios.
    try:
        dados_planilha = carregar_planilha()
    except Exception as e:
        print(f'Erro ao carregar do Drive: {e}')
        dados_planilha = []

    dados_banco = carregar_banco()
    if not dados_planilha:
        return aplicar_assuntos_e_links(dados_banco)
    if not dados_banco:
        return aplicar_assuntos_e_links(dados_planilha)

    por_ano_numero = {
        (linha['exercicio_decreto'], linha['decreto_numero']): i
        for i, linha in enumerate(dados_planilha)
        if linha['exercicio_decreto'] and linha['decreto_numero']
    }
    por_ano_data = {}
    for i, linha in enumerate(dados_planilha):
        chave = (linha['exercicio_decreto'], linha['data_elaboracao'])
        if all(chave):
            por_ano_data.setdefault(chave, []).append(i)

    for registro in dados_banco:
        ano = registro['exercicio_decreto']
        numero = registro['decreto_numero']
        indice = por_ano_numero.get((ano, numero)) if numero else None

        if indice is None and ano and registro['data_elaboracao']:
            candidatos = por_ano_data.get((ano, registro['data_elaboracao']), [])
            for campo in ('orgao_elaboracao', 'link_decreto', 'processo_sei'):
                valor = registro.get(campo, '')
                if valor:
                    filtrados = [i for i in candidatos if dados_planilha[i].get(campo) == valor]
                    if filtrados:
                        candidatos = filtrados
            if len(candidatos) == 1:
                indice = candidatos[0]

        if indice is not None:
            destino = dados_planilha[indice]
            for campo in COLUNAS_DADOS:
                # O ano e o número da planilha são a referência canônica.
                if campo in ('exercicio_decreto', 'decreto_numero'):
                    continue
                if registro.get(campo):
                    destino[campo] = registro[campo]
        elif numero:
            # Mantém decretos cadastrados no banco que ainda não estão na planilha.
            registro['_row_key'] = uuid.uuid4().hex
            dados_planilha.append(registro)
            por_ano_numero[(ano, numero)] = len(dados_planilha) - 1

    return aplicar_assuntos_e_links(dados_planilha)


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
                'name': 'assunto_decreto',
                'label': 'Assunto do Decreto',
                'field': 'assunto_decreto',
                'align': 'left',
                'style': 'min-width: 320px; max-width: 520px; white-space: normal; overflow-wrap: anywhere;',
                'headerStyle': 'min-width: 320px;',
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
                'label': 'Link do Decreto',
                'field': 'link_decreto',
                'align': 'center',
                'style': 'min-width: 115px; width: 120px;',
                'headerStyle': 'min-width: 115px; width: 120px;',
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
            <q-td :props="props" style="min-width: 115px; text-align: center;">
                <a v-if="props.value && String(props.value).startsWith('http')"
                   :href="props.value" target="_blank" rel="noopener noreferrer"
                   class="inline-block rounded bg-blue-700 px-3 py-1 font-medium text-white hover:bg-blue-800">
                    Abrir ↗
                </a>
                <span v-else class="text-gray-400">-</span>
            </q-td>
        ''')

        campos_busca = (
            'exercicio_decreto',
            'decreto_numero',
            'data_elaboracao',
            'assunto_decreto',
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
            in_assunto = ui.input(
                'Assunto do Decreto',
                placeholder='Digite o assunto; este campo será apenas texto',
            ).classes('w-full')
            in_link = ui.input(
                'Link direto do Decreto (Google Drive)',
                placeholder='Cole o link compartilhável do PDF',
            ).classes('w-full')

            def salvar_decreto():
                assunto = texto_limpo(in_assunto.value)
                novo_registro = {
                    'exercicio_decreto': normalizar_ano(in_exercicio.value),
                    'decreto_numero': normalizar_numero(in_numero.value),
                    'data_elaboracao': formatar_data(in_data.value),
                    'orgao_elaboracao': texto_limpo(in_orgao.value),
                    'processo_sei': texto_limpo(in_sei.value),
                    'assunto_decreto': assunto,
                    # Mantém compatibilidade com o esquema existente sem exibir
                    # nem solicitar este campo no formulário.
                    'complemento_informacoes': f'ASSUNTO: {assunto}' if assunto else '',
                    'link_decreto': texto_limpo(in_link.value),
                    '_row_key': uuid.uuid4().hex,
                }

                if DATABASE_URL:
                    try:
                        engine = create_engine(DATABASE_URL)
                        registro_banco = {
                            chave: valor
                            for chave, valor in novo_registro.items()
                            if chave not in ('_row_key', 'assunto_decreto')
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
