# data lake - surowce odpowiedzi api nbp jako json, zanim trafia do bq
resource "google_storage_bucket" "raw" {
    name = "${var.project_id}-raw"
    location = var.region

    # jedna warstwa uprawnien IAM zamiast per-plikowych ACL
    uniform_bucket_level_access = true

    # projekt treningowy: destroy usunie bucket razem z zawartoscia
    force_destroy = true

    lifecycle_rule {
        condition {
            age = 365
        }
        action {
            type = "SetStorageClass"
            storage_class = "COLDLINE"
        }
    }
}