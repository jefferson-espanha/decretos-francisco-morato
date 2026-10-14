import os
import pandas as pd
from sqlalchemy import create_engine

RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if not RAW_DATABASE_URL:
    raise ValueError("ERRO: Variável DATABASE_URL não encontrada nos Secrets!")

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

    # Normaliza nomes removendo espaços extras
    df.columns = [str(col).strip() for col in df.columns]

    # Mapeamento estrito para as colunas do Neon
    col_map = {
        'Exercicio': 'exercicio_decreto',
        'Data': 'data_elaboracao',
        'Link do Decreto': 'link_decreto',
        'complemento_informacoes': 'complemento_informacoes',
        'processo_sei': 'processo_sei',
        'PROCESSO SEI': 'processo_sei'
    }

    df = df.rename(columns=col_map)

    # FILTRO RIGOROSO: Mantém APENAS as colunas que existem no Neon
    colunas_banco = [
        'exercicio_decreto', 
        'data_elaboracao', 
        'link_decreto', 
        'complemento_informacoes', 
        'processo_sei'
    ]

    colunas_finais = [c for c in colunas_banco if c in df.columns]
    df = df[colunas_finais]

    # Conversão de tipos de dados
    if 'exercicio_decreto' in df.columns:
        df['exercicio_decreto'] = pd.to_numeric(df['exercicio_decreto'], errors='coerce')

    if 'data_elaboracao' in df.columns:
        df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce')

    print(f"Colunas que serão enviadas: {list(df.columns)}")
    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)
    
    print(f"Enviando {len(df)} registros para o Neon...")
    df.to_sql('decretos', engine, if_exists='append', index=False)
    print("Importação concluída com sucesso!")

if __name__ == "__main__":
    subir_csv()
