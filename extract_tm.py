import requests
import pandas as pd
from bs4 import BeautifulSoup
import time

def scrape_transfermarkt_top_500(pages_to_scrape=20):
    # NOTA: Mi extractor para el top financiero mundial de Transfermarkt mapeado por red
    tm_players = []
    base_url = "https://www.transfermarkt.com/spieler-statistik/wertvollstespieler/marktwertetop"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.transfermarkt.com/spieler-statistik/wertvollstespieler/marktwertetop",
        "X-Requested-With": "XMLHttpRequest"
    }

    print(f"🚀 Iniciando raspado financiero de Transfermarkt. Escaneando {pages_to_scrape} páginas.")
    print("=========================================================================")

    for current_page in range(1, pages_to_scrape + 1):
        # PRINTS DE VALIDACIÓN VIVOS: Alerta en consola de qué página asíncrona se está atacando
        print(f"💰 Conectando con bloque AJAX - Página {current_page}/{pages_to_scrape}...")
        
        params = {
            "ajax": "yw1",
            "page": current_page
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ Transfermarkt bloqueó la petición en la página {current_page}. Status: {response.status_code}")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            player_rows = soup.find_all('tr', class_=['odd', 'even'])
            
            if not player_rows:
                print(f"🏁 No se detectaron más filas de tabla en la página {current_page}.")
                break
                
            page_matches = 0
            for row in player_rows:
                # 1. Extracción del nombre
                name_cell = row.find('td', class_='hauptlink')
                if not name_cell or not name_cell.find('a'):
                    continue
                player_name = name_cell.find('a').text.strip()
                
                # 2. Extracción del valor de mercado
                value_cell = row.find('td', class_='rechts hauptlink')
                if not value_cell:
                    continue
                
                raw_value = value_cell.text.strip()
                clean_value = raw_value.replace('€', '').replace('m', '').strip()
                
                try:
                    market_value_m = float(clean_value)
                except ValueError:
                    market_value_m = 0.0
                    
                # 3. Lógica económica base: Factor multiplicador 1.3x para cláusulas de la liga
                release_clause_m = round(market_value_m * 1.3, 2)
                
                tm_players.append({
                    "TM_Name": player_name,
                    "MarketValue_Real": market_value_m,
                    "ReleaseClause": release_clause_m
                })
                page_matches += 1
            
            # PRINTS DE VALIDACIÓN VIVOS: Confirmar cuántos jugadores financieros se procesaron con éxito en la página
            print(f"✅ Página {current_page} mapeada con éxito. Se extrajeron {page_matches} perfiles financieros.")
            
            # Delay alto obligatorio para cuidar nuestra IP de un baneo automático de Transfermarkt
            time.sleep(2.5)
            
        except Exception as e:
            print(f"❌ Fallo crítico en el procesamiento AJAX de la página {current_page}: {str(e)}")
            break
            
    df_tm = pd.DataFrame(tm_players)
    return df_tm

if __name__ == "__main__":
    # Extracción por defecto apuntando a las 100 páginas reales del top de valuación mundial
    df_resultado_tm = scrape_transfermarkt_top_500(pages_to_scrape=100)
    
    if not df_resultado_tm.empty:
        print("=========================================================================")
        print(f"✅ Extracción de Transfermarkt finalizada. Archivo 'raw_transfermarkt.csv' guardado con {len(df_resultado_tm)} registros.")
        df_resultado_tm.to_csv("raw_transfermarkt.csv", index=False)