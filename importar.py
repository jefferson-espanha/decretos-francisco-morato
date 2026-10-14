import os
import pandas as pd
from sqlalchemy import create_engine

# Pega a URL dos Secrets e substitui o prefixo para o driver do SQLAlchemy
RAW_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

def subir_csv():
    if not DATABASE_URL:
        raise ValueError("A variável DATABASE_URL não foi configurada nos Secrets do GitHub!")

    print("Lendo a planilha decretos.csv...")
    try:
        df = pd.read_csv("decretos.csv", encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv("decretos.csv", encoding='latin1')

    # Mapeamento para as colunas exatas da tabela do Neon
    df = df.rename(columns={
        'ExercicioDecreto': 'exercicio_decreto',
        '“G”DataElaboração': 'data_elaboracao',
        'Link do Decreto': 'link_decreto',
        'Complemento de informações de decreto - Nomes, Ruas, Lotes, quadras': 'complemento_informacoes',
        'PROCESSO SEI': 'processo_sei'
    })

    # Tratamento da data para formato aceito pelo PostgreSQL (AAAA-MM-DD)
    if 'data_elaboracao' in df.columns:
        df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce')

    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)
    
    print(f"Enviando {len(df)} registros para a tabela 'decretos'...")
    df.to_sql('decretos', engine, if_exists='append', index=False)
    print("Importação concluída com sucesso pelo GitHub Actions!")

if __name__ == "__main__":
    subir_csv()
