import os
import pandas as pd
from sqlalchemy import create_engine

# Pega a URL dos secrets do GitHub
RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if not RAW_DATABASE_URL:
    raise ValueError("ERRO: A variável 'DATABASE_URL' não foi configurada nos Secrets do GitHub!")

# Garante o driver psycopg2 para SQLAlchemy
if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

def subir_csv():
    print("Lendo a planilha decretos.csv...")
    try:
        df = pd.read_csv("decretos.csv", encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv("decretos.csv", encoding='latin1')

    # Mapeamento estrito baseado nos nomes reais do seu CSV
    col_map = {
        'Exercicio': 'exercicio_decreto',
        'Data': 'data_elaboracao',
        'Link do Decreto ': 'link_decreto',
        'Link do Decreto': 'link_decreto',
        'complemento_informacoes': 'complemento_informacoes',
        'processo_sei': 'processo_sei',
        'PROCESSO SEI': 'processo_sei'
    }

    # Renomeia as colunas conhecidas
    df = df.rename(columns=col_map)

    # Colunas oficiais que existem no banco Neon
    colunas_banco = [
        'exercicio_decreto', 
        'data_elaboracao', 
        'link_decreto', 
        'complemento_informacoes', 
        'processo_sei'
    ]

    # Mantém SOMENTE as colunas que pertencem ao banco (descarta Unnamed, Decreto "G", etc.)
    colunas_presentes = [col for col in colunas_banco if col in df.columns]
    df = df[colunas_presentes]

    # Tratamento de tipos
    if 'exercicio_decreto' in df.columns:
        df['exercicio_decreto'] = pd.to_numeric(df['exercicio_decreto'], errors='coerce')

    if 'data_elaboracao' in df.columns:
        df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce')

    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)
    
    print(f"Enviando {len(df)} registros selecionados para a tabela 'decretos'...")
    df.to_sql('decretos', engine, if_exists='append', index=False)
    print("Importação concluída com sucesso!")

if __name__ == "__main__":
    subir_csv()
