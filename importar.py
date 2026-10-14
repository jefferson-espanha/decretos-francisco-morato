import os
import re
import pandas as pd
from sqlalchemy import create_engine

SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv"

RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if not RAW_DATABASE_URL:
    raise ValueError("ERRO: Variável DATABASE_URL não encontrada nos Secrets!")

if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

def extrair_numero_decreto(row):
    # Se já existir número na coluna 1
    val1 = str(row.get('col1', '')).replace('.0', '').strip()
    if val1 and val1 != 'nan':
        return val1

    # Tenta extrair do início do texto/link (ex: "32Altera...", "1 Nomeação...")
    link = str(row.get('col5', '')).strip()
    match = re.match(r'^(\d+)', link)
    if match:
        return match.group(1)

    # Tenta extrair do final da coluna 0 (ex: 19841 -> 1)
    col0 = str(row.get('col0', '')).replace('.0', '').strip()
    if len(col0) > 4:
        return col0[4:]

    return ''

def extrair_ano(row):
    col0 = str(row.get('col0', '')).replace('.0', '').strip()
    if len(col0) >= 4:
        return col0[:4]
    return col0

def importar_sheets():
    print("Baixando planilha do Google Drive...")
    df = pd.read_csv(SHEETS_URL)

    # Seleciona as 6 primeiras colunas físicas
    df = df.iloc[:, :6]
    df.columns = ['col0', 'col1', 'col2', 'col3', 'col4', 'col5']

    # Processa colunas
    df['exercicio_decreto'] = df.apply(extrair_ano, axis=1)
    df['decreto_numero'] = df.apply(extrair_numero_decreto, axis=1)
    df['data_elaboracao'] = pd.to_datetime(df['col2'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
    df['orgao_elaboracao'] = df['col3'].fillna('').astype(str).str.strip()
    df['processo_sei'] = df['col4'].fillna('').astype(str).str.strip()
    df['link_decreto'] = df['col5'].fillna('').astype(str).str.strip()

    df_final = df[[
        'exercicio_decreto',
        'decreto_numero',
        'data_elaboracao',
        'orgao_elaboracao',
        'processo_sei',
        'link_decreto'
    ]].copy()

    df_final = df_final.fillna('')

    # Cria ID para a chave primária do banco
    df_final.reset_index(inplace=True)
    df_final.rename(columns={'index': 'id'}, inplace=True)
    df_final['id'] = df_final['id'] + 1

    print(f"Total de {len(df_final)} registros processados.")
    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    print("Recriando a tabela 'decretos' no Neon com o novo esquema...")
    df_final.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Tabela recriada e populada com sucesso!")

if __name__ == "__main__":
    importar_sheets()
