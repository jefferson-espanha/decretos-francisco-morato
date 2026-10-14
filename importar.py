import os
import re
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

def processar_linha(row):
    # Trata Ano e Número do Decreto
    val_exercicio = str(row.get('col0', '')).replace('.0', '').strip()
    val_decreto = str(row.get('col1', '')).replace('.0', '').strip()
    
    ano = ''
    num = val_decreto

    if len(val_exercicio) >= 4:
        ano = val_exercicio[:4]
        # Se a segunda coluna veio em branco, extrai o número do restante da primeira coluna
        if not num and len(val_exercicio) > 4:
            num = val_exercicio[4:]
    else:
        ano = val_exercicio

    # Se ainda não encontrou o número, tenta pegar do início do nome do arquivo
    if not num:
        link_str = str(row.get('col5', '')).strip()
        match = re.search(r'Decreto\s+(\d+)', link_str, re.IGNORECASE)
        if match:
            num = match.group(1)
        else:
            match_num = re.match(r'^(\d+)', link_str)
            if match_num:
                num = match_num.group(1)

    return pd.Series([ano, num])

def importar_sheets():
    print("Baixando planilha do Google Drive...")
    df = pd.read_csv(SHEETS_URL)

    # Pega as primeiras 6 colunas reais
    df = df.iloc[:, :6]
    df.columns = ['col0', 'col1', 'col2', 'col3', 'col4', 'col5']

    # Extrai Ano e Número do Decreto
    df[['exercicio_decreto', 'decreto_numero']] = df.apply(processar_linha, axis=1)

    # Mapeia as colunas finais
    df['data_elaboracao'] = pd.to_datetime(df['col2'], dayfirst=True, errors='coerce').dt.strftime('%d/%m/%Y')
    df['orgao_elaboracao'] = df['col3'].astype(str).str.strip()
    df['processo_sei'] = df['col4'].astype(str).str.strip()
    df['link_decreto'] = df['col5'].astype(str).str.strip()

    # Seleciona apenas as colunas formatadas
    df_final = df[[
        'exercicio_decreto',
        'decreto_numero',
        'data_elaboracao',
        'orgao_elaboracao',
        'processo_sei',
        'link_decreto'
    ]].copy()

    df_final = df_final.fillna('')

    # Adiciona chave ID para persistência no banco
    df_final.reset_index(inplace=True)
    df_final.rename(columns={'index': 'id'}, inplace=True)
    df_final['id'] = df_final['id'] + 1

    print(f"Total de {len(df_final)} decretos processados com sucesso.")
    print("Conectando ao Neon PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    print("Substituindo dados na tabela 'decretos'...")
    df_final.to_sql('decretos', engine, if_exists='replace', index=False)
    print("Sincronização concluída com sucesso!")

if __name__ == "__main__":
    importar_sheets()
