import os
import pandas as pd
from sqlalchemy import create_engine

# Link de exportação em CSV da planilha no Google Drive
SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ZfuaBX3ar5_oihkDfnJcaY6AUyJoWVY12Yzh4oiHIY0/export?format=csv"

RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if not RAW_DATABASE_URL:
    raise ValueError("ERRO: A variável 'DATABASE_URL' não foi configurada nos Secrets!")

if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

def importar_sheets():
    print("Baixando planilha do Google Drive...")
    df = pd.read_csv(SHEETS_URL)

    # Remove espaços extras do início e fim dos nomes das colunas
    df.columns = [str(col).strip() for col in df.columns]

    # Mapeamento completo das 7 colunas exatas
    col_map = {
        'Exercicio': 'exercicio_decreto',
        'Decreto “G”': 'decreto_numero',
        'Decreto "G"': 'decreto_numero',
        'Data': 'data_elaboracao',
        'Elaboração': 'orgao_elaboracao',
        'Link do Decreto': 'link_decreto',
        'Complemento de informações de decreto - Nomes, Ruas, Lotes, quadras': 'complemento_informacoes',
        'PROCESSO SEI': 'processo_sei'
    }

    df = df.rename(columns=col_map)

    # Seleciona apenas as colunas mapeadas
    colunas_finais = [
        'exercicio_decreto',
        'decreto_numero',
        'data_elaboracao',
        'orgao_elaboracao',
        'link_decreto',
        'complemento_informacoes',
        'processo_sei'
    ]

    colunas_existentes = [c for c in colunas_finais if c in df.columns]
    df = df[colunas_existentes]

    # Tratamento de tipos
    if 'exercicio_decreto' in df.columns:
        df['exercicio_decreto'] = pd.to_numeric(df['exercicio_decreto'], errors='coerce')

    print(f"Total de {len(df)} registros processados com as colunas: {list(df.columns)}")
    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    # if_exists='replace' atualiza toda a estrutura do banco com as novas colunas
    print("Substituindo dados antigos na tabela 'decretos'...")
    df.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Importação concluída com sucesso!")

if __name__ == "__main__":
    importar_sheets()
