import os
import pandas as pd
from sqlalchemy import create_engine

# Pega a URL do banco que cadastramos nos Secrets do GitHub
DATABASE_URL = os.environ.get('DATABASE_URL')

def subir_csv():
    if not DATABASE_URL:
        raise ValueError("A variável DATABASE_URL não foi encontrada nos Secrets!")

    print("Lendo a planilha decretos.csv...")
    try:
        df = pd.read_csv("decretos.csv", encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv("decretos.csv", encoding='latin1')

    # Mapeamento para garantir as colunas exatas da tabela do Neon
    df = df.rename(columns={
        'ExercicioDecreto': 'exercicio_decreto',
        '“G”DataElaboração': 'data_elaboracao',
        'Link do Decreto': 'link_decreto',
        'Complemento de informações de decreto - Nomes, Ruas, Lotes, quadras': 'complemento_informacoes',
        'PROCESSO SEI': 'processo_sei'
    })

    if 'data_elaboracao' in df.columns:
        df['data_elaboracao'] = pd.to_datetime(df['data_elaboracao'], dayfirst=True, errors='coerce')

    engine = create_engine(DATABASE_URL)
    
    print(f"Enviando {len(df)} linhas para a tabela decretos no Neon...")
    df.to_sql('decretos', engine, if_exists='append', index=False)
    print("Importação concluída com sucesso pelo GitHub Actions!")

if __name__ == "__main__":
    subir_csv()
