locals {
    datasets = {
        raw     = "Raw NBP API responses loaded as-is from GCS"
        staging = "Cleaned and typed exchange rates"
        marts   = "Analytics-ready tables - partitioned by rate date"
    }
}

resource "google_bigquery_dataset" "layers" {
    for_each = local.datasets

    dataset_id = "nbp_${each.key}"
    description = each.value
    location   = var.region

    delete_contents_on_destroy = true
}