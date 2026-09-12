from google.cloud import bigquery
import pandas as pd

# ID proyecto GCP
PROJECT_ID = "pes-fantasy-project"
DATASET_ID = "pes_analytics"

def load_df_to_bigquery(df: pd.DataFrame, table_name: str):
    """
    Inyecta un DataFrame de Pandas a una tabla en BigQuery en modo Overwriter (WRITE_TRUNCATE).
    """