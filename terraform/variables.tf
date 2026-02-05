variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "The GCP Region"
  type        = string
  # WARNING: Keep as us-central1, us-west1, or us-east1 for Free Tier eligibility of e2-micro.
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "bucket_name" {
  description = "The name of the GCS bucket for strategy files. Must be globally unique."
  type        = string
  default     = "quant-dashboard-files-unique-id" 
}
