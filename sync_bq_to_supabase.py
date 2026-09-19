import os
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery
from sqlalchemy import create_engine, text

# Credenciales GCP
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp_keys.json"
PROJECT_ID = os.getenv("PROJECT_ID")
RAW_ID = os.getenv("RAW_ID")

load_dotenv()

def sync_data():
    print("🚀 Iniciando proceso de sincronización BigQuery -> Supabase...")

    bq_client = bigquery.Client(location="US", project=PROJECT_ID)
    
    # Define la consulta a tu dataset en BigQuery
    bq_query = """
        SELECT 
            pes_id,
            pes_name,
            position,
            rating_range,
            pes_rating,
            pes_age,
            team_name,
            nation_name,
            market_value_real,
            release_clause
        FROM `pes-fantasy-project.liga_fantasia_raw.fct_jugadores_consolidados`
    """
    
    print("📥 Extrayendo tabla dim_players desde BigQuery...")
    df_players = bq_client.query(bq_query).to_dataframe()
    print(f"✅ Se obtuvieron {len(df_players)} registros desde BigQuery.")

    # 2. Conexión a Supabase (Postgres)
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")

    connection_string = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_string)

    # 3. Cargar datos a Supabase sin sobrescribir la asignación de mánagers
    print("📤 Actualizando catálogo en Supabase...")
    
    with engine.begin() as conn:
        for _, row in df_players.iterrows():
            upsert_query = text("""
                INSERT INTO dim_players (
                    pes_id, pes_name, position, rating_range, pes_rating, 
                    pes_age, team_name, nat_name, market_value_real, release_clause
                ) VALUES (
                    :pes_id, :pes_name, :position, :rating_range, :pes_rating, 
                    :pes_age, :team_name, :nation_name, :market_value_real, :release_clause
                )
                ON CONFLICT (pes_id) DO UPDATE SET
                    pes_name = EXCLUDED.pes_name,
                    position = EXCLUDED.position,
                    rating_range = EXCLUDED.rating_range,
                    pes_rating = EXCLUDED.pes_rating,
                    pes_age = EXCLUDED.pes_age,
                    team_name = EXCLUDED.team_name,
                    nat_name = EXCLUDED.nat_name,
                    market_value_real = EXCLUDED.market_value_real,
                    release_clause = EXCLUDED.release_clause;
            """)
            
            # Reemplazar valores NaN por None para evitar errores de tipo en PostgreSQL
            params = row.where(pd.notnull(row), None).to_dict()
            conn.execute(upsert_query, params)

    print("✨ Sincronización completada con éxito. ¡Catálogo de jugadores actualizado!")

if __name__ == "__main__":
    sync_data()