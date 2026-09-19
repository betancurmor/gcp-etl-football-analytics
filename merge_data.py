import pandas as pd
import random
from thefuzz import fuzz, process
import pandas_gbq
import os

# Credenciales GCP
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp_keys.json"
PROJECT_ID = os.getenv("PROJECT_ID")
RAW_ID = os.getenv("RAW_ID")

def advanced_clean_and_merge_with_audit(threshold=65):
    # -------------------------------------------------------------------------
    # 1. LECTURA DE TABLAS STAGING DESDE BIGQUERY
    # -------------------------------------------------------------------------    
    print("Leyendo tablas staging desde BigQuery...")
    
    query_pes_master = f"SELECT * FROM `{PROJECT_ID}.{RAW_ID}.stg_pes_master`"
    query_tm = f"SELECT * FROM `{PROJECT_ID}.{RAW_ID}.vw_transfermarkt_transformed`"

    df_pes_master = pandas_gbq.read_gbq(query_pes_master, project_id=PROJECT_ID)
    df_tm = pandas_gbq.read_gbq(query_tm, project_id=PROJECT_ID)
    
    # -------------------------------------------------------------------------
    # TRATAMIENTO DE DUPLICADOS (Criterio: Preservar versión con menor OVR)
    # -------------------------------------------------------------------------
    df_pes_master = df_pes_master.sort_values(by="pes_rating", ascending=True)
    df_pes_master = df_pes_master.drop_duplicates(subset=["pes_name"], keep="first")
    df_pes_master = df_pes_master.sort_values(by="pes_rating", ascending=False).reset_index(drop=True)

    df_pes_master["market_value_real"] = 0.0
    df_pes_master["release_clause"] = 0.0
    
    tm_names = df_tm["tm_name"].tolist()
    no_matches_list = []

    # -------------------------------------------------------------------------
    # FUZZY MERGE VECTORIAL CON MONITOREO EN TIEMPO REAL
    # -------------------------------------------------------------------------
    print("\n🚀 Iniciando comparación y cálculo de variables de mercado...")
    for idx, pes_row in df_pes_master.iterrows():
        pes_name = pes_row["pes_name"]
        pes_rating = pes_row["pes_rating"]
        
        best_match, similarity = process.extractOne(pes_name, tm_names, scorer=fuzz.token_set_ratio)
        
        if similarity >= threshold:
            tm_row = df_tm[df_tm["tm_name"] == best_match].iloc[0]
            df_pes_master.at[idx, "market_value_real"] = tm_row["market_value_real"]
            df_pes_master.at[idx, "release_clause"] = tm_row["release_clause"]
            print(f"🤝 [Match] '{pes_name}' <=> '{best_match}' ({round(similarity, 1)}%)")
        else:
            if pes_rating >= 85:
                estimated_val = 25.0 if pes_rating > 87 else 18.0
            else:
                estimated_val = round(((pes_rating - 60) ** 2) / 25, 1) if pes_rating > 60 else 0.5
                
            df_pes_master.at[idx, "market_value_real"] = estimated_val
            df_pes_master.at[idx, "release_clause"] = round(estimated_val * 1.25, 1)
            
            print(f"⚠️ [Fórmula] '{pes_name}' sin match (Mejor intento: '{best_match}' al {round(similarity, 1)}%)")
            
            no_matches_list.append({
                "pes_id": pes_row["pes_id"],
                "pes_name": pes_name,
                "position": pes_row["position"],
                "pes_rating": pes_rating,
                "est_value": estimated_val,
                "best_tm_attempt": best_match,
                "confidence": f"{round(similarity, 1)}%"
            })

    # -------------------------------------------------------------------------
    # NOTA: MECÁNICA DE NIEBLA DE GUERRA ALEATORIA ASIMÉTRICA
    # -------------------------------------------------------------------------
    min_ratings = []
    max_ratings = []
    rating_ranges = []
    
    for idx, row in df_pes_master.iterrows():
        base_rating = row["pes_rating"]
        
        # Parámetros aleatorios independientes entre 2 y 6 para romper el promedio lineal
        offset_down = random.randint(2, 6)
        offset_up = random.randint(2, 6)
        
        calc_min = base_rating - offset_down
        calc_max = base_rating + offset_up
        
        min_ratings.append(calc_min)
        max_ratings.append(calc_max)
        rating_ranges.append(f"{calc_min} - {calc_max}")
        
    df_pes_master["min_rating"] = min_ratings
    df_pes_master["max_rating"] = max_ratings
    df_pes_master["rating_range"] = rating_ranges

    # NOTA: Homologación de encabezados económicos a snake_case estricto
    df_pes_master = df_pes_master.rename(columns={
        "market_value_real": "market_value_real",
        "release_clause": "release_clause"
    })

    # -------------------------------------------------------------------------
    # ESTRUCTURACIÓN FINAL COMPLETA (TODAS LAS COLUMNAS PROTEGIDAS Y ACTUALIZADAS)
    # -------------------------------------------------------------------------
    df_final = df_pes_master[[
        "pes_id", 
        "pes_name", 
        "position", 
        "pes_rating",         # Metadato técnico interno
        "min_rating",         # Piso del rango
        "max_rating",         # Techo del rango
        "rating_range",       # Visualización para el bot de Telegram
        "pes_age",            # Edad original
        "team_name",          # Club original
        "nation_name",           # Nacionalidad
        "market_value_real",  # Valor de mercado homologado
        "release_clause"      # Cláusula de rescisión homologada
    ]].copy()
    
    # -------------------------------------------------------------------------
    # NOTA: FILTROS DE PURGA DE AUDITORÍA (REGLAS DE CONTROL MAYO 2026)
    # -------------------------------------------------------------------------
    inicial_count = len(df_final)
    df_final = df_final[~df_final["pes_id"].astype(str).str.startswith("1757")]
    clones_purgados = inicial_count - len(df_final)
    
    post_clones_count = len(df_final)
    retirados_lista = ["S. AGÜERO", "TONI KROOS"]
    df_final = df_final[~df_final["pes_name"].str.upper().isin(retirados_lista)]
    df_final = df_final.reset_index(drop=True).sort_values(by="pes_rating", ascending=False)
    retirados_purgados = post_clones_count - len(df_final)
    
    df_no_matches = pd.DataFrame(no_matches_list)
    if not df_no_matches.empty:
        df_no_matches = df_no_matches[~df_no_matches["pes_id"].astype(str).str.startswith("1757")]
        df_no_matches = df_no_matches[~df_no_matches["pes_name"].str.upper().isin(retirados_lista)]

    # -------------------------------------------------------------------------
    # REPORTES RESUMEN EN CONSOLA (DOBLE CHECK FINAL)
    # -------------------------------------------------------------------------
    print(f"\n🧼 --- CONTROL DE CALIDAD: {clones_purgados} fakes eliminados y {retirados_purgados} leyendas retiradas purgadas ---")

    if not df_no_matches.empty:
        print("\n⚠️ TABLA DE EXCEPCIONES FILTRADA (VALUACIONES ALGORÍTMICAS REALES):")
        print("=========================================================================================")
        print(df_no_matches.sort_values(by="pes_rating", ascending=False).head(20).to_string(index=False))
        print("=========================================================================================")
    
    # -------------------------------------------------------------------------
    # CARGA FINAL A BIGQUERY (TABLA DE HECHOS / CONSOLIDADA)
    # -------------------------------------------------------------------------
    print("\n📤 Enviando dataset consolidado a BigQuery...")
    pandas_gbq.to_gbq(
        dataframe=df_final.sort_values(by="pes_rating", ascending=False),
        destination_table=f"{PROJECT_ID}.liga_fantasia_raw.fct_jugadores_consolidados",
        project_id=PROJECT_ID,
        if_exists="replace"
    )

    print(f"\n✅ Proceso finalizado exitosamente.")
    print(f"Población final depurada en BigQuery: {len(df_final)} jugadores.")
    return df_final

if __name__ == "__main__":
    df_master_limpio = advanced_clean_and_merge_with_audit()