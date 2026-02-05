output "instance_ip" {
  description = "The public IP of the Quant Dashboard VM"
  value       = google_compute_instance.default.network_interface.0.access_config.0.nat_ip
}

output "bucket_url" {
  description = "The URL of the created GCS bucket"
  value       = google_storage_bucket.strategy_data.url
}
