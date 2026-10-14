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
    # Se já existir valor na coluna decreto_numero, utiliza
    num_existente = str(row.get('decreto_numero', '')).strip()
    if num_existente and num_existente != 'nan':
        return num_existente
    
    # Se o numero veio grudado com o ano na coluna exercicio (ex: 19841, 198410)
    exercicio_str = str(row.get('exercicio_decreto', '')).strip()
    if len(exercicio_str) > 4:
        ano = exercicio_str[:4]
        num = exercicio_str[4:]
        return num
    return ''

def extrair_ano(row):
    exercicio_str = str(row.get('exercicio_decreto', '')).strip()
    if len(exercicio_str) >= 4:
        return exercicio_str[:4]
    return exercicio_str

def importar_sheets():
    print("Baixando planilha do Google Drive...")
    df = pd.read_csv(SHEETS_URL)

    # Pega as primeiras 7 colunas
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

    # Ajusta ano e número do decreto
    df['decreto_numero'] = df.apply(extrair_numero_decreto, axis=1)
    df['exercicio_decreto'] = df.apply(extrair_ano, axis=1)

    # Formata a data para DD/MM/AAAA
    df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')

    # Preenche nulos
    df = df.fillna('')

    print(f"Total de {len(df)} linhas processadas.")
    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    print("Substituindo dados na tabela 'decretos'...")
    df.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Sincronização concluída com sucesso!")

if __name__ == "__main__":
    importar_sheets()
