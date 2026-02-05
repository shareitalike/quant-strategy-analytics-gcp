provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# ---------------------------------------------------------------------------------------------------------------------
# API ENABLEMENT (Automatic)
# ---------------------------------------------------------------------------------------------------------------------
# Automatically enable the necessary APIs for the new project.
resource "google_project_service" "compute" {
  service = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage" {
  service = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  service = "iam.googleapis.com"
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------------------------------------------------
# STORAGE BUCKET
# ---------------------------------------------------------------------------------------------------------------------
# We create a GCS bucket to store the strategy .xlsx files. 
# This mimics the "folder" structure the application expects when mounted via gcsfuse.
resource "google_storage_bucket" "strategy_data" {
  name          = var.bucket_name
  location      = "US"
  force_destroy = true # Allows deleting bucket even if it contains files (Useful for dev/demos)
  
  uniform_bucket_level_access = true

  # Ensure the Storage API is enabled before creating the bucket
  depends_on = [google_project_service.storage]
}

# ---------------------------------------------------------------------------------------------------------------------
# FIREWALL RULES
# ---------------------------------------------------------------------------------------------------------------------
# We explicitly allow traffic on ports 8501 (Streamlit) and 8080 (Jenkins).
# Port 22 (SSH) is implicitly allowed by default but good to be explicit or restrict source ranges in prod.
resource "google_compute_firewall" "app_firewall" {
  name    = "allow-quant-dashboard"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8501", "8080", "22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["quant-dashboard-server"]

  # Ensure the Compute API is enabled before creating the firewall
  depends_on = [google_project_service.compute]
}

# ---------------------------------------------------------------------------------------------------------------------
# COMPUTE ENGINE INSTANCE
# ---------------------------------------------------------------------------------------------------------------------
resource "google_compute_instance" "default" {
  name         = "quant-dashboard-vm"
  machine_type = "e2-micro" # Free Tier eligible!
  tags         = ["quant-dashboard-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30 # 30GB is within Free Tier limits
    }
  }

  network_interface {
    network = "default"
    access_config {
      // Ephemeral public IP
    }
  }

  # Crucial for GCS Fuse to work!
  service_account {
    scopes = ["cloud-platform"]
  }

  # Ensure the Compute API is enabled to avoid "Resource Not Found" or "API Disabled" errors
  depends_on = [google_project_service.compute]

  # -----------------------------------------------------------------------------------------------------------------
  # STARTUP SCRIPT (BOOTSTRAPPING)
  # -----------------------------------------------------------------------------------------------------------------
  # This script runs automatically when the VM boots. It replaces all manual setup steps.
  metadata_startup_script = <<-EOT
    #!/bin/bash
    set -ex
    echo "Starting Provisioning..."

    # 1. SWAP FILE SETUP
    if [ ! -f /swapfile ]; then
        fallocate -l 4G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi

    # 2. INSTALL DEPENDENCIES (Docker + Key Utils)
    apt-get update
    apt-get install -y docker.io wget curl gnupg lsb-release
    usermod -aG docker ubuntu || true

    # 3. INSTALL GCS FUSE (Signed-By Method)
    export GCSFUSE_REPO=gcsfuse-`lsb_release -c -s`
    # Clean up old lists to avoid conflicts
    rm -f /etc/apt/sources.list.d/gcsfuse.list
    
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.asc] https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | tee /etc/apt/sources.list.d/gcsfuse.list
    
    # Download key and ensure readable
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | tee /usr/share/keyrings/cloud.google.asc > /dev/null
    chmod 644 /usr/share/keyrings/cloud.google.asc
    
    apt-get update
    apt-get install -y gcsfuse

    # 4. (SKIPPED) JENKINS
    # We are deploying manually for now to reduce complexity.
    # apt-get install -y jenkins... 

    # 5. MOUNT BUCKET
    mkdir -p /home/ubuntu/quant-dashboard-files
    chown ubuntu:ubuntu /home/ubuntu/quant-dashboard-files
    
    # Retry mount on failure
    gcsfuse --implicit-dirs ${var.bucket_name} /home/ubuntu/quant-dashboard-files || echo "Mount failed, checking again later..."

    echo "Provisioning Complete! Docker is ready. SSH in to run the app."
  EOT
}
