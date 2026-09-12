import pandas as pd
import pydoc
from sqlalchemy import create_engine, text

def load_clean_players_to_sql(csv_path="clean_fantasy_players.csv"):
    # Configuración de los parámetros de conexión local a SQL Server
    server = "LOCALHOST\\SQLEXPRESS"
    database = "DB_PES_Fantasy"
    
    # Engine compatible con SQLAlchemy utilizando el driver pyodbc y autenticación de Windows
    connection_string = f"mssql+pyodbc://@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    engine = create_engine(connection_string)
    
    try:
        print(f" Cargando datos desde {csv_path}...")
        df = pd.read_csv(csv_path)
        
        # Mapeo manual para asegurar compatibilidad con el esquema snake_case de SQL Server
        mapping = {
            "PES_ID": "pes_id",
            "PES_Name": "pes_name",
            "Position": "position",
            "PES_Rating": "pes_rating",
            "Min_Rating": "min_rating",
            "Max_Rating": "max_rating",
            "Rating_Range": "rating_range",
            "PES_Age": "pes_age",
            "Team_Name": "team_name",
            "Nat_Name": "nat_name",
            "Market_Value_Real": "market_value_real",
            "Release_Clause": "release_clause"
        }
        df = df.rename(columns=mapping)
        
        # Inicialización de mánager en NULL para el estado inicial de agentes libres
        df["manager_id"] = None
        
        # Reseteo de tablas para garantizar un proceso de carga limpio e idempotente
        print(" Limpiando registros previos en 'dim_players'...")
        with engine.begin() as conn:
            # Vaciado secuencial para no violar restricciones de integridad referencial (FK)
            conn.execute(text("DELETE FROM fact_transactions;"))
            conn.execute(text("DELETE FROM dim_players;"))
        
        # Inserción masiva por bloques para optimizar el uso de memoria en el servidor
        print(f" Inyectando {len(df)} jugadores en la base de datos...")
        df.to_sql(
            name="dim_players",
            con=engine,
            if_exists="append",  
            index=False,         
            chunksize=500        
        )
        
        print(" ¡Proceso completado con éxito! Base de datos sincronizada.")
        
    except FileNotFoundError:
        print(f" Error: No se encontró el archivo {csv_path}. Ejecuta primero 'merge_data.py'.")
    except Exception as e:
        print(f" Error crítico durante la carga a la base de datos: {e}")

if __name__ == "__main__":
    load_clean_players_to_sql()