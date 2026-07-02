variable "project_id" {
    type        = string
    description = "GCP project ID where resources will be created"
}

variable "region" {
    type        = string
    description = "GCP region where resources will be created"
    default     = "europe-central2"
}