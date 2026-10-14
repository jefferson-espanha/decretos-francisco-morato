import os
import pandas as pd
from sqlalchemy import create_engine

# Link de exportação em CSV do seu Google Sheets
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

    print("Colunas originais encontradas na planilha:")
    for i, col in enumerate(df.columns):
        print(f"  Coluna {i}: '{col}'")

    # Mapeamento flexível via palavra-chave para não perder nenhuma coluna
    col_map = {}
    for col in df.columns:
        c_str = str(col).strip()
        c_lower = c_str.lower()

        if 'exercicio' in c_lower or 'ano' in c_lower:
            col_map[col] = 'exercicio_decreto'
        elif 'decreto' in c_lower and ('g' in c_lower or '“' in c_str or '"' in c_str or 'num' in c_lower):
            col_map[col] = 'decreto_numero'
        elif 'data' in c_lower:
            col_map[col] = 'data_elaboracao'
        elif 'elabora' in c_lower:
            col_map[col] = 'orgao_elaboracao'
        elif 'link' in c_lower:
            col_map[col] = 'link_decreto'
        elif 'complemento' in c_lower or 'informaco' in c_lower or 'ruas' in c_lower or 'nomes' in c_lower:
            col_map[col] = 'complemento_informacoes'
        elif 'sei' in c_lower:
            col_map[col] = 'processo_sei'

    df = df.rename(columns=col_map)

    # Colunas oficiais do banco Neon
    colunas_banco = [
        'exercicio_decreto',
        'decreto_numero',
        'data_elaboracao',
        'orgao_elaboracao',
        'link_decreto',
        'complemento_informacoes',
        'processo_sei'
    ]

    # Mantém apenas as colunas que foram mapeadas com sucesso
    colunas_finais = [c for c in colunas_banco if c in df.columns]
    df = df[colunas_finais]

    # Preenche valores nulos para garantir que nada venha como 'None'
    df = df.fillna('')

    print(f"Colunas prontas para envio: {list(df.columns)}")
    print(f"Total de {len(df)} linhas extraídas com sucesso.")

    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    print("Substituindo dados na tabela 'decretos'...")
    df.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Sincronização concluída com sucesso!")

if __name__ == "__main__":
    importar_sheets()
