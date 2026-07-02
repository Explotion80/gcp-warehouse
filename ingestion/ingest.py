"""NBP exchange rates ingestion: API -> GCS (raw JSON) -> BigQuery raw layer."""

import json
import sys
from datetime import date
from typing import Optional

import google.auth
import requests
from google.auth import impersonated_credentials
from google.cloud import bigquery, storage

# --- Konfiguracja (na razie stale; przy wiekszym projekcie: zmienne srodowiskowe) ---
PROJECT_ID = "nbp-warehouse"
BUCKET_NAME = "nbp-warehouse-raw"
DATASET_ID = "nbp_raw"
TABLE_ID = "exchange_rates_table_a"
SA_EMAIL = "nbp-ingestion@nbp-warehouse.iam.gserviceaccount.com"
NBP_API_URL = "https://api.nbp.pl/api/exchangerates/tables/a/{rate_date}/?format=json"
LOCATION = "europe-central2"  # musi zgadzac sie z lokalizacja datasetow i bucketa

def get_credentials() -> impersonated_credentials.Credentials:
    """Buduje poswiadczenia SA przez impersonacje (bez klucza na dysku)."""
    source_credentials, _ = google.auth.default()
    return impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=SA_EMAIL,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


def fetch_table(rate_date: str) -> Optional[list]:
    """Pobiera tabele A dla danej daty. None = brak notowan (weekend/swieto)."""
    url = NBP_API_URL.format(rate_date=rate_date)
    response = requests.get(url, timeout=30)

    if response.status_code == 404:  # NBP nie publikuje tabel w dni wolne
        return None

    response.raise_for_status()  # inne bledy (5xx itd.) maja przerwac skrypt
    return response.json()

def upload_to_gcs(credentials, rate_date: str, data: list) -> str:
    """Zapisuje tabele jako NDJSON do data lake. Ta sama data = nadpisanie (idempotencja)."""
    client = storage.Client(project=PROJECT_ID, credentials=credentials)
    blob = client.bucket(BUCKET_NAME).blob(f"raw/table_a/{rate_date}.json")

    # NDJSON: jeden obiekt JSON = jedna linia (format wymagany przez load job BQ)
    ndjson = "\n".join(json.dumps(row, ensure_ascii=False) for row in data)
    blob.upload_from_string(ndjson, content_type="application/json")
    return f"gs://{BUCKET_NAME}/{blob.name}"


def load_to_bigquery(credentials) -> int:
    """Przeladowuje CALY lake do tabeli raw (WRITE_TRUNCATE = pelna idempotencja)."""
    client = bigquery.Client(project=PROJECT_ID, credentials=credentials, location=LOCATION)

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,  # OK dla warstwy raw; jawne typy naklada staging (Faza 3)
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    uri = f"gs://{BUCKET_NAME}/raw/table_a/*.json"  # wildcard: wszystkie dni naraz
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    job = client.load_table_from_uri(uri, table_ref, job_config=job_config)
    job.result()  # load job jest asynchroniczny; czekamy i tu wybuchnie ewentualny blad

    return client.get_table(table_ref).num_rows


if __name__ == "__main__":
    rate_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    data = fetch_table(rate_date)
    if data is None:
        print(f"[{rate_date}] Brak notowan (weekend/swieto) - nic do zrobienia.")
        sys.exit(0)

    credentials = get_credentials()
    gcs_path = upload_to_gcs(credentials, rate_date, data)
    print(f"[{rate_date}] Zapisano surowiec: {gcs_path}")

    total_rows = load_to_bigquery(credentials)
    print(f"[{rate_date}] Tabela {DATASET_ID}.{TABLE_ID} przeladowana, wierszy: {total_rows}")