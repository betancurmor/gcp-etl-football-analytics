import random
import time
from bs4 import BeautifulSoup
import pandas as pd
import requests
from google.cloud import bigquery
import os
import pandas_gbq

# Autenticacion a GCP
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp_keys.json"

def scrape_transfermarkt_top_500(pages_to_scrape=20):
    tm_players = []
    base_url = "https://www.transfermarkt.com/spieler-statistik/wertvollstespieler/marktwertetop"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": (
            "https://www.transfermarkt.com/spieler-statistik/wertvollstespieler/marktwertetop"
        ),
        "X-Requested-With": "XMLHttpRequest",
    }

    print(
        f"🚀 Iniciando raspado financiero de Transfermarkt. Escaneando"
        f" {pages_to_scrape} páginas."
    )
    print("=========================================================================")

    for current_page in range(1, pages_to_scrape + 1):
        print(
            f"💰 Conectando con bloque AJAX - Página"
            f" {current_page}/{pages_to_scrape}..."
        )

        params = {"ajax": "yw1", "page": current_page}

        # Lógica de reintentos silenciosa para tolerar lags de red
        max_retries = 3
        success = False

        for attempt in range(1, max_retries + 1):
            try:
                # Subimos el timeout a 25s
                response = requests.get(
                    base_url, headers=headers, params=params, timeout=25
                )

                if response.status_code != 200:
                    print(
                        f"❌ Transfermarkt respondió status:"
                        f" {response.status_code} en página {current_page}."
                    )
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                player_rows = soup.find_all("tr", class_=["odd", "even"])

                if not player_rows:
                    print(
                        f"🏁 No se detectaron más filas de tabla en la página"
                        f" {current_page}."
                    )
                    success = True
                    break

                page_matches = 0
                for row in player_rows:
                    name_cell = row.find("td", class_="hauptlink")
                    if not name_cell or not name_cell.find("a"):
                        continue
                    player_name = name_cell.find("a").text.strip()

                    value_cell = row.find("td", class_="rechts hauptlink")
                    if not value_cell:
                        continue

                    raw_value = value_cell.text.strip()
                    clean_value = (
                        raw_value.replace("€", "").replace("m", "").strip()
                    )

                    try:
                        market_value_m = float(clean_value)
                    except ValueError:
                        market_value_m = 0.0

                    tm_players.append(
                        {
                            "tm_name": player_name,
                            "market_value_real": market_value_m                        }
                    )
                    page_matches += 1

                print(
                    f"✅ Página {current_page} mapeada con éxito. Se"
                    f" extrajeron {page_matches} perfiles financieros."
                )
                success = True
                break  # Éxito: salimos del bucle de reintentos

            except Exception as e:
                print(
                    f"⚠️ Timeout/Lags en página {current_page} (Intento"
                    f" {attempt}/{max_retries}). Reintentando..."
                )
                time.sleep(5)

        if not success:
            print(
                f"❌ Se agotaron los reintentos en la página {current_page}."
                " Abortando extracción."
            )
            break

        # Rango aleatorio para evitar patrones de conducta
        time.sleep(random.uniform(8, 13))

    df_tm = pd.DataFrame(tm_players)
    return df_tm

if __name__ == "__main__":
    df_resultado_tm = scrape_transfermarkt_top_500(pages_to_scrape=20)

    if not df_resultado_tm.empty:
        print("=========================================================================")
        print(f"✅ Extracción de Transfermarkt finalizada, se guardaron {len(df_resultado_tm)} registros.")

        # Ingesta a GCP
        pandas_gbq.to_gbq(
            dataframe=df_resultado_tm,
            destination_table= 'pes-fantasy-project.liga_fantasia_raw.stg_transfermarkt',
            project_id='pes-fantasy-project',
            if_exists='replace'
        )