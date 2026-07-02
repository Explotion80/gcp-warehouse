# --- Tozsamosc dla skryptu ingestii ---
resource "google_service_account" "ingestion" {
  account_id   = "nbp-ingestion"
  display_name = "NBP ingestion pipeline"
  description  = "Writes raw NBP JSON to GCS and loads it into BigQuery raw layer"
}

# --- Least privilege: kazda rola na najnizszym mozliwym poziomie ---

# Zapis surowych plikow — tylko ten jeden bucket
resource "google_storage_bucket_iam_member" "ingestion_bucket_writer" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion.email}"
}

# Uruchamianie load jobow — rola projektowa (joby zyja na poziomie projektu),
# ale sama w sobie nie daje dostepu do zadnych danych
resource "google_project_iam_member" "ingestion_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

# Zapis do tabel — tylko dataset raw; staging i marts sa poza zasiegiem
resource "google_bigquery_dataset_iam_member" "ingestion_raw_writer" {
  dataset_id = google_bigquery_dataset.layers["raw"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}