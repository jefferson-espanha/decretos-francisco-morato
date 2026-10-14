import os
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

def importar_sheets():
    print("Baixando dados do Google Sheets...")
    df = pd.read_csv(SHEETS_URL)

    # Limpa espaços nos nomes das colunas
    df.columns = [str(col).strip() for col in df.columns]

    col_map = {
        'Exercicio': 'exercicio_decreto',
        'Data': 'data_elaboracao',
        'Link do Decreto': 'link_decreto',
        'complemento_informacoes': 'complemento_informacoes',
        'processo_sei': 'processo_sei',
        'PROCESSO SEI': 'processo_sei'
    }

    df = df.rename(columns=col_map)

    # Filtra apenas as colunas que pertencem ao banco
    colunas_banco = ['exercicio_decreto', 'data_elaboracao', 'link_decreto', 'complemento_informacoes', 'processo_sei']
    df = df[[c for c in colunas_banco if c in df.columns]]

    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    print(f"Enviando {len(df)} registros do Google Sheets para o Neon...")
    # if_exists='replace' recria a tabela limpa sem duplicar nem dar erro de coluna
    df.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Sincronização com o Google Sheets concluída com sucesso!")

if __name__ == "__main__":
    importar_sheets()
