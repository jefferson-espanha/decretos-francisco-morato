import os
import pandas as pd
from sqlalchemy import create_engine

# Link de exportação direta do seu Google Sheets em CSV
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

    # Limpa espaços em branco nas bordas dos nomes das colunas
    df.columns = [str(col).strip() for col in df.columns]

    # Mapeamento com base exata na sua amostra
    col_map = {
        'Exercicio': 'exercicio_decreto',
        'ExercicioDecreto': 'exercicio_decreto',
        'Decreto “G”': 'decreto_numero',
        'Decreto "G"': 'decreto_numero',
        'Data': 'data_elaboracao',
        'DataElaboração': 'data_elaboracao',
        'Elaboração': 'orgao_elaboracao',
        'Link do Decreto': 'link_decreto',
        'Complemento de informações de decreto - Nomes, Ruas, Lotes, quadras': 'complemento_informacoes',
        'PROCESSO SEI': 'processo_sei'
    }

    df = df.rename(columns=col_map)

    # Mantém apenas as colunas mapeadas que pertencem ao banco
    colunas_banco = [
        'exercicio_decreto',
        'decreto_numero',
        'data_elaboracao',
        'orgao_elaboracao',
        'link_decreto',
        'complemento_informacoes',
        'processo_sei'
    ]

    colunas_existentes = [c for c in colunas_banco if c in df.columns]
    df = df[colunas_existentes]

    # Preenche valores vazios para evitar erro no banco
    df = df.fillna('')

    print(f"Total de {len(df)} registros validados com as colunas: {list(df.columns)}")
    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    # 'replace' recria a tabela no Neon com a estrutura exata das 7 colunas
    print("Substituindo a tabela 'decretos' no Neon...")
    df.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Importação concluída com sucesso!")

if __name__ == "__main__":
    importar_sheets()
