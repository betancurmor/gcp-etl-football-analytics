# Modernización de Pipeline ETL: Ingesta Nativa en GCP & Analytics

## 🎯 Objetivo del Proyecto
Migrar una arquitectura de procesamiento de datos local (basada en scripts desacoplados y transformaciones pesadas) hacia una arquitectura **Serverless y ELT en Google Cloud Platform (GCP)**. 

El proyecto automatiza la ingesta de métricas financieras de mercado y estadísticas de rendimiento, consolidando la información en un Data Warehouse centralizado en **BigQuery** para su consumo analítico.

## 🏗️ Arquitectura Propuesta
1. **Ingesta (Extract & Load):** Scripts en Python que extraen información web/API y la ingieren directamente en tablas de *Staging* en BigQuery.
2. **Transformación (Transform):** Vistas SQL nativas en BigQuery para cruce de catálogos, lógica de negocio y cálculo de métricas financieras en tiempo real.
3. **Visualización:** Tablero dinámico en **Looker Studio** para el consumo de KPIs y toma de decisiones.

## 🛠️ Tech Stack
* **Lenguaje:** Python 3.x (`pandas`, `requests`, `google-cloud-bigquery`)
* **Cloud Infrastructure:** Google Cloud Platform (BigQuery, Cloud Functions)
* **Base de Datos / DW:** Google BigQuery (SQL dialect)
* **Visualización:** Looker Studio