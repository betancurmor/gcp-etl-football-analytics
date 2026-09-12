import pandas as pd
import random
from thefuzz import fuzz
from thefuzz import process

def advanced_clean_and_merge_with_audit(pes_csv="raw_pes_master.csv", tm_csv="raw_transfermarkt.csv", threshold=65):
    # NOTA: Pipeline personal para unificar datos, limpiar clones y estructurar rangos dinámicos aleatorios con persistencia de OVR
    try:
        df_pes = pd.read_csv(pes_csv)
        df_tm = pd.read_csv(tm_csv)
    except FileNotFoundError as e:
        print(f"Error de origen de datos: {e}")
        return

    # -------------------------------------------------------------------------
    # TRATAMIENTO DE DUPLICADOS (Criterio: Preservar versión con menor OVR)
    # -------------------------------------------------------------------------
    df_pes = df_pes.sort_values(by="PES_Rating", ascending=True)
    df_pes = df_pes.drop_duplicates(subset=["PES_Name"], keep="first")
    df_pes = df_pes.sort_values(by="PES_Rating", ascending=False).reset_index(drop=True)

    df_pes["MarketValue_Real"] = 0.0
    df_pes["ReleaseClause"] = 0.0
    
    tm_names = df_tm["TM_Name"].tolist()
    no_matches_list = []

    # -------------------------------------------------------------------------
    # FUZZY MERGE VECTORIAL CON MONITOREO EN TIEMPO REAL
    # -------------------------------------------------------------------------
    print("\n🚀 Iniciando comparación y cálculo de variables de mercado...")
    for idx, pes_row in df_pes.iterrows():
        pes_name = pes_row["PES_Name"]
        pes_rating = pes_row["PES_Rating"]
        
        best_match, similarity = process.extractOne(pes_name, tm_names, scorer=fuzz.token_set_ratio)
        
        if similarity >= threshold:
            tm_row = df_tm[df_tm["TM_Name"] == best_match].iloc[0]
            df_pes.at[idx, "MarketValue_Real"] = tm_row["MarketValue_Real"]
            df_pes.at[idx, "ReleaseClause"] = tm_row["ReleaseClause"]
            print(f"🤝 [Match] '{pes_name}' <=> '{best_match}' ({round(similarity, 1)}%)")
        else:
            if pes_rating >= 85:
                estimated_val = 25.0 if pes_rating > 87 else 18.0
            else:
                estimated_val = round(((pes_rating - 60) ** 2) / 25, 1) if pes_rating > 60 else 0.5
                
            df_pes.at[idx, "MarketValue_Real"] = estimated_val
            df_pes.at[idx, "ReleaseClause"] = round(estimated_val * 1.25, 1)
            
            print(f"⚠️ [Fórmula] '{pes_name}' sin match (Mejor intento: '{best_match}' al {round(similarity, 1)}%)")
            
            no_matches_list.append({
                "PES_ID": pes_row["PES_ID"],
                "PES_Name": pes_name,
                "Position": pes_row["Position"],
                "PES_Rating": pes_rating,
                "Est_Value": estimated_val,
                "Best_TM_Attempt": best_match,
                "Confidence": f"{round(similarity, 1)}%"
            })

    # -------------------------------------------------------------------------
    # NOTA: MECÁNICA DE NIEBLA DE GUERRA ALEATORIA ASIMÉTRICA
    # -------------------------------------------------------------------------
    min_ratings = []
    max_ratings = []
    rating_ranges = []
    
    for idx, row in df_pes.iterrows():
        base_rating = row["PES_Rating"]
        
        # Parámetros aleatorios independientes entre 2 y 6 para romper el promedio lineal
        offset_down = random.randint(2, 6)
        offset_up = random.randint(2, 6)
        
        calc_min = base_rating - offset_down
        calc_max = base_rating + offset_up
        
        min_ratings.append(calc_min)
        max_ratings.append(calc_max)
        rating_ranges.append(f"{calc_min} - {calc_max}")
        
    df_pes["Min_Rating"] = min_ratings
    df_pes["Max_Rating"] = max_ratings
    df_pes["Rating_Range"] = rating_ranges

    # NOTA: Homologación de encabezados económicos a snake_case estricto
    df_pes = df_pes.rename(columns={
        "MarketValue_Real": "Market_Value_Real",
        "ReleaseClause": "Release_Clause"
    })

    # -------------------------------------------------------------------------
    # ESTRUCTURACIÓN FINAL COMPLETA (TODAS LAS COLUMNAS PROTEGIDAS Y ACTUALIZADAS)
    # -------------------------------------------------------------------------
    df_final = df_pes[[
        "PES_ID", 
        "PES_Name", 
        "Position", 
        "PES_Rating",         # Metadato técnico interno
        "Min_Rating",         # Piso del rango
        "Max_Rating",         # Techo del rango
        "Rating_Range",       # Visualización para el bot de Telegram
        "PES_Age",            # Edad original
        "Team_Name",          # Club original
        "Nat_Name",           # Nacionalidad
        "Market_Value_Real",  # Valor de mercado homologado
        "Release_Clause"      # Cláusula de rescisión homologada
    ]].copy()
    
    # -------------------------------------------------------------------------
    # NOTA: FILTROS DE PURGA DE AUDITORÍA (REGLAS DE CONTROL MAYO 2026)
    # -------------------------------------------------------------------------
    inicial_count = len(df_final)
    df_final = df_final[~df_final["PES_ID"].astype(str).str.startswith("1757")]
    clones_purgados = inicial_count - len(df_final)
    
    post_clones_count = len(df_final)
    retirados_lista = ["S. AGÜERO", "TONI KROOS"]
    df_final = df_final[~df_final["PES_Name"].str.upper().isin(retirados_lista)]
    retirados_purgados = post_clones_count - len(df_final)
    
    df_no_matches = pd.DataFrame(no_matches_list)
    if not df_no_matches.empty:
        df_no_matches = df_no_matches[~df_no_matches["PES_ID"].astype(str).str.startswith("1757")]
        df_no_matches = df_no_matches[~df_no_matches["PES_Name"].str.upper().isin(retirados_lista)]

    # -------------------------------------------------------------------------
    # REPORTES RESUMEN EN CONSOLA (DOBLE CHECK FINAL)
    # -------------------------------------------------------------------------
    print(f"\n🧼 --- CONTROL DE CALIDAD: {clones_purgados} fakes eliminados y {retirados_purgados} leyendas retiradas purgadas ---")

    if not df_no_matches.empty:
        print("\n⚠️ TABLA DE EXCEPCIONES FILTRADA (VALUACIONES ALGORÍTMICAS REALES):")
        print("=========================================================================================")
        print(df_no_matches.sort_values(by="PES_Rating", ascending=False).head(20).to_string(index=False))
        print("=========================================================================================")
    
    print("\n✅ DATASET CONSOLIDADO COMPLETO Y DEPURADO (SQL READY):")
    print("=========================================================================================")
    # Impresión de control con las nuevas columnas estructuradas correctamente
    print(df_final[["PES_ID", "PES_Name", "Position", "PES_Rating", "Rating_Range", "PES_Age", "Team_Name", "Market_Value_Real", "Release_Clause"]].head(25).to_string(index=False))
    print("=========================================================================================")
    
    df_final.to_csv("clean_fantasy_players.csv", index=False)
    print(f"Población final depurada lista para inyección: {len(df_final)} jugadores.")
    return df_final

if __name__ == "__main__":
    df_master_limpio = advanced_clean_and_merge_with_audit()