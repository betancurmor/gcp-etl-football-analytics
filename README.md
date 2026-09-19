# ⚽ PES Fantasy Bot: Architecture & Cloud Data Pipeline

## 🎯 Objetivo del Proyecto
Desarrollar una arquitectura híbrida **Serverless, ELT y OLTP** para la gestión de una liga de fútbol fantasy en tiempo real mediante un Bot de Telegram.

El proyecto automatiza la ingesta de métricas de mercado y estadísticas de rendimiento en un Data Warehouse en **Google Cloud Platform (GCP)**, sincronizando los datos procesados con un backend transaccional en **Supabase (PostgreSQL)** para servir a los usuarios finales con mínima latencia.

---

## 🏗️ Arquitectura de Datos
1. **Ingesta & Analytics (ELT):** Scripts en Python que ingieren datos en tablas de *Staging* en **BigQuery**. Se ejecutan vistas SQL nativas para lógica de negocio, cláusulas y métricas financieras.
2. **Backend Operativo (OLTP):** Sincronización mediante SQLAlchemy hacia **Supabase (PostgreSQL)** con Connection Pooling (puerto 6543) para permitir transacciones concurrentes instantáneas (fichajes, cláusulas y ventas).
3. **Interfaz de Usuario:** Bot interactivo en **Telegram** (`python-telegram-bot`) que permite a los mánagers gestionar sus plantillas en tiempo real.
4. **Visualización:** Tableros en **Looker Studio** conectados a BigQuery para el seguimiento analítico de la liga.

---

## 🛠️ Tech Stack
* **Lenguajes & Librerías:** Python 3.10+ (`python-telegram-bot`, `pandas`, `SQLAlchemy`, `psycopg2-binary`, `google-cloud-bigquery`, `python-dotenv`)
* **Data Warehouse & Cloud:** Google Cloud Platform (BigQuery)
* **Base de Datos Transaccional:** Supabase / PostgreSQL (Connection Pooling)
* **Visualización:** Looker Studio

---

## 🛠️ Instalación y Configuración

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/betancurmor/gcp-etl-football-analytics](https://github.com/betancurmor/gcp-etl-football-analytics)
   cd PES_Fantasy_Project