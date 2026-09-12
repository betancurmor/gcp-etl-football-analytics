import requests
import pandas as pd
import time
import json

def scrape_pesmaster_api_paginated(max_players=3000):
    # NOTA: Mi pipeline masivo para extraer el catálogo extendido de jugadores con variables demográficas
    players_list = []
    base_url = "https://www.pesmaster.com/es/efootball-2022/search/api.php"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.pesmaster.com/es/efootball-2022/search/?type=0"
    }
    
    current_start = 0
    batch_size = 40  # Tamaño del bloque por llamada AJAX en el scroll
    
    # PRINTS DE VALIDACIÓN VIVOS: Monitoreo del inicio de la carga masiva
    print(f"🚀 Iniciando extracción masiva en PES Master. Objetivo: {max_players} jugadores.")
    print("=========================================================================")
    
    while len(players_list) < max_players:
        current_page = (current_start // batch_size) + 1
        
        params = {
            "game": "2022",
            "type": "0",
            "page": current_page
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=15)
            if response.status_code != 200:
                print(f"❌ Error de red en Página {current_page}. Status Code: {response.status_code}")
                break
                
            raw_text = response.text.strip()
            if not raw_text:
                print(f"🏁 Respuesta vacía del servidor en Página {current_page}. Fin de datos.")
                break
                
            data = json.loads(raw_text)
            players_data = data.get("data", []) if isinstance(data, dict) else data
            
            if not players_data:
                print(f"🏁 No se encontraron más registros en la clave 'data' de la Página {current_page}.")
                break
            
            # PRINTS DE VALIDACIÓN VIVOS: Reportar el procesamiento de la página actual y cuántos llevo acumulados
            print(f"📦 [Página {current_page}] Procesando bloque de {len(players_data)} jugadores (Acumulados: {len(players_list)})...")
                
            for player in players_data:
                p_name = player.get("name")
                p_age = player.get("age")
                
                if not p_name or p_age is None:
                    continue
                
                # REGLA 1: Filtrar menores de 17 años (Clones/Regens artificiales del juego)
                try:
                    age_int = int(p_age)
                    if age_int < 17:
                        continue
                except ValueError:
                    continue
                
                # REGLA 2: Excluir nombres genéricos corruptos
                if "PLAYER" in str(p_name).upper():
                    continue
                
                p_id = player.get("id")
                p_pos = player.get("pos", "N/A")
                p_ovr = player.get("ovr")
                p_team = player.get("team_name", "Agente Libre")
                p_nat = player.get("nat_name", "Internacional")
                
                if p_ovr:
                    players_list.append({
                        "PES_ID": int(p_id) if p_id else len(players_list) + 1,
                        "PES_Name": str(p_name).strip(),
                        "Position": str(p_pos).strip(),
                        "PES_Rating": int(p_ovr),
                        "PES_Age": age_int,
                        "Team_Name": str(p_team).strip(),
                        "Nat_Name": str(p_nat).strip()
                    })
            
            current_start += batch_size
            time.sleep(3)  # Delay preventivo anti-bloqueos
            
        except Exception as e:
            print(f"❌ Falla crítica procesando el lote de la Página {current_page}: {str(e)}")
            break
            
    df_pes = pd.DataFrame(players_list)
    if not df_pes.empty:
        df_pes = df_pes.drop_duplicates(subset=["PES_ID"]).head(max_players)
        
    return df_pes

if __name__ == "__main__":
    # Extracción masiva apuntando a las 100 páginas completas de PES Master (3000 jugadores aprox.)
    df_resultado = scrape_pesmaster_api_paginated(max_players=3000)
    
    if not df_resultado.empty:
        print("=========================================================================")
        print(f"✅ Extracción masiva terminada. Archivo 'raw_pes_master.csv' generado con {len(df_resultado)} registros.")
        df_resultado.to_csv("raw_pes_master.csv", index=False)