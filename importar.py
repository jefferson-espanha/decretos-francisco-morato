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

def limpar_ano(val):
    if pd.isna(val) or val == '':
        return ''
    s = str(val).replace('.0', '').strip()
    match = re.search(r'\d{4}', s)
    return match.group(0) if match else s

def extrair_numero(row):
    num_col = str(row.get('decreto_numero', '')).replace('.0', '').strip()
    if num_col and num_col != 'nan':
        return num_col

    # Se estiver no link (ex: "10 Nomeação do Conselho...")
    link = str(row.get('link_decreto', '')).strip()
    match = re.match(r'^(\d+)', link)
    if match:
        return match.group(1)
    
    return ''

def importar_sheets():
    print("Baixando planilha do Google Drive...")
    df = pd.read_csv(SHEETS_URL)

    # Pega as colunas na ordem original
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

    # Limpeza e extração
    df['exercicio_decreto'] = df['exercicio_decreto'].apply(limpar_ano)
    df['decreto_numero'] = df.apply(extrair_numero, axis=1)
    df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')

    # Remove a coluna de complemento da gravação
    df = df.drop(columns=['complemento_informacoes'], errors='ignore')
    df = df.fillna('')

    print(f"Total de {len(df)} linhas processadas.")
    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    print("Substituindo dados na tabela 'decretos'...")
    df.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Sincronização concluída com sucesso!")

if __name__ == "__main__":
    importar_sheets()
