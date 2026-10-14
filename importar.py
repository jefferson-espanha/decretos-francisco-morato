import os
import pandas as pd
from sqlalchemy import create_engine

# Link de exportação do seu Google Sheets
SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv"

RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if not RAW_DATABASE_URL:
    raise ValueError("ERRO: A variável 'DATABASE_URL' não foi configurada nos Secrets!")

if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

def importar_sheets():
    print("Baixando dados diretamente da planilha do Google Drive...")
    df = pd.read_csv(SHEETS_URL)

    # Limpa espaços nos nomes das colunas
    df.columns = [str(col).strip() for col in df.columns]

    col_map = {
        'Exercicio': 'exercicio_decreto',
        'ExercicioDecreto': 'exercicio_decreto',
        'Data': 'data_elaboracao',
        'DataElaboração': 'data_elaboracao',
        'Link do Decreto': 'link_decreto',
        'Link do Decreto ': 'link_decreto',
        'complemento_informacoes': 'complemento_informacoes',
        'Complemento': 'complemento_informacoes',
        'Complemento de informações de decreto - Nomes, Ruas, Lotes, quadras': 'complemento_informacoes',
        'processo_sei': 'processo_sei',
        'PROCESSO SEI': 'processo_sei'
    }

    df = df.rename(columns=col_map)

    # Mantém SOMENTE as colunas aceitas pelo banco
    colunas_banco = ['exercicio_decreto', 'data_elaboracao', 'link_decreto', 'complemento_informacoes', 'processo_sei']
    df = df[[c for c in colunas_banco if c in df.columns]]

    print(f"Total de {len(df)} registros encontrados.")
    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    # if_exists='replace' recria a tabela e evita erros de colunas extras ou duplicações
    print("Substituindo dados antigos na tabela 'decretos'...")
    df.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Importação da planilha concluída com sucesso!")

if __name__ == "__main__":
    importar_sheets()
