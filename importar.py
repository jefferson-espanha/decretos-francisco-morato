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
    print("Baixando planilha do Google Drive...")
    df = pd.read_csv(SHEETS_URL)

    print(f"Colunas brutas lidas: {list(df.columns)}")

    # Pega apenas as primeiras 7 colunas (posições 0 a 6)
    df = df.iloc[:, :7]

    # Renomeia estritamente pela ordem física das colunas na planilha
    df.columns = [
        'exercicio_decreto',
        'decreto_numero',
        'data_elaboracao',
        'orgao_elaboracao',
        'link_decreto',
        'complemento_informacoes',
        'processo_sei'
    ]

    # Preenche valores nulos com texto vazio
    df = df.fillna('')

    print(f"Total de {len(df)} linhas formatadas com sucesso.")
    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    print("Substituindo dados na tabela 'decretos'...")
    df.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Sincronização concluída com sucesso!")

if __name__ == "__main__":
    importar_sheets()
