# 🚀 Quant Dashboard Deployment Guide (GCP Free Tier)

This guide provides a step-by-step procedure to deploy the Quant Dashboard on a **Google Cloud Platform (GCP) Free Tier** e2-micro instance. It covers infrastructure setup, storage integration, CI/CD with Jenkins, and Docker containerization.

---

## 🏗️ Architecture

```mermaid
graph LR
    User[User] -->|Browser| LB[Streamlit App (Port 8501)]
    subgraph "GCP VM (e2-micro)"
        Jenkins[Jenkins CI/CD] -->|Builds| Docker[Docker Container]
        Docker -->|Reads Data| Fuse[gcsfuse Mount]
    end
    Fuse -->|Network| GCS[(Google Cloud Storage)]
```

---

## 0. Prerequisites
- **GCP Account** (Active).
- **GCP Project** created.
- **GCS Bucket** named `quant-dashboard-files` (or similar) containing your `.xlsx` files.

---

## 1. VM & OS Setup (Crucial for Free Tier)

The `e2-micro` instance has only **1GB RAM**. Running Jenkins and Python apps requires more memory. We strictly need a **Swap File**.

1.  **Create Instance**:
    -   Go to Compute Engine -> VM Instances -> Create Instance.
    -   Name: `quant-dashboard-vm`
    -   Region: `us-central1` (or your preferred free tier region).
    -   Machine Type: `e2-micro`.
    -   Boot Disk: **Ubuntu 22.04 LTS** (Standard Persistent Disk, 30GB).
    -   Firewall: Allow HTTP/HTTPS.

2.  **SSH into VM**: Click "SSH" in the GCP Console.

3.  **⚡ Create Swap File (DO NOT SKIP)**:
    ```bash
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    ```
    *Explanation: This uses disk space as "emergency RAM", preventing crashes when Jenkins builds Docker images.*

---

## 2. Storage Setup (GCS Fuse)

Instead of rewriting the app to use the GCS API, we "mount" the bucket as a folder.

1.  **Install gcsfuse**:
    ```bash
    export GCSFUSE_REPO=gcsfuse-`lsb_release -c -s`
    echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
    sudo apt-get update
    sudo apt-get install gcsfuse
    ```

2.  **Authenticate**:
    ```bash
    gcloud auth application-default login
    ```
    *(Follow the link, copy the code, and paste it back into the terminal)*

3.  **Create Mount Point & Mount**:
    ```bash
    mkdir -p /home/USER_NAME/quant-dashboard-files
    # Replace BUCKET_NAME and USER_NAME
    gcsfuse --implicit-dirs BUCKET_NAME /home/USER_NAME/quant-dashboard-files
    ```
    *Note: Replace `USER_NAME` with your actual username (run `whoami` to check).*

---

## 3. Tool Installation

1.  **Install Docker**:
    ```bash
    sudo apt-get update
    sudo apt-get install -y docker.io
    sudo usermod -aG docker $USER
    # You might need to re-login for group changes to take effect
    ```

2.  **Install Java (for Jenkins)**:
    ```bash
    sudo apt-get install -y openjdk-17-jre
    ```

3.  **Install Jenkins**:
    ```bash
    curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | sudo tee \
      /usr/share/keyrings/jenkins-keyring.asc > /dev/null
    echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
      https://pkg.jenkins.io/debian-stable binary/ | sudo tee \
      /etc/apt/sources.list.d/jenkins.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y jenkins
    ```

4.  **Grant Jenkins Docker Permissions**:
    ```bash
    sudo usermod -aG docker jenkins
    sudo systemctl restart jenkins
    ```

---

## 4. Pipeline Configuration

1.  **Access Jenkins**:
    -   Open `http://YOUR_VM_EXTERNAL_IP:8080`.
    -   *If it doesn't open, go to GCP Firewall rules and allow TCP port 8080.*
    -   Get initial password: `sudo cat /var/lib/jenkins/secrets/initialAdminPassword`.

2.  **Setup**:
    -   Install "Suggested Plugins".
    -   Create Admin User.

3.  **Create Job**:
    -   New Item -> "QuantPipeline" -> **Pipeline**.
    -   **Definition**: Pipeline script from SCM.
    -   **SCM**: Git.
    -   **Repository URL**: [Your GitHub Repo URL].
    -   **Branch**: `*/main`.
    -   **Script Path**: `Jenkinsfile`.
    -   Save.

4.  **Environment Variable Setup in Jenkins**:
    -   Ideally, you edit the `Jenkinsfile` on the repo with the correct `HOST_DATA_PATH`.
    -   Ensure `HOST_DATA_PATH` in `Jenkinsfile` matches `/home/USER_NAME/quant-dashboard-files`.

---

## 5. Deployment & Interview Explanation

**Run the Job**: Click "Build Now" in Jenkins.

### 🧠 Interview Ready Explanations

**Q: Why did you use `gcsfuse` instead of the GCS Python Client?**
A: "This is a **Lift and Shift** strategy. We wanted to migrate the application to the cloud with **zero code changes** to the business logic. `gcsfuse` allows the legacy file-reading code to interact with Object Storage (GCS) as if it were a local POSIX filesystem. This reduced migration time and risk."

**Q: How did you handle the free tier limitations?**
A: "The `e2-micro` instance has limited RAM. I configured a **4GB Swap File** to handle the burst memory usage during Docker builds. I also implemented a `cleanup` stage in the Jenkins pipeline to prune unused Docker images, preventing disk saturation, which is critical for long-running CI/CD on constrained infrastructure."

**Q: Why separate Metrics and UI layers?**
A: "We refactored the app into `app.py` (UI) and `metrics.py` (Business Logic). This decoupling allows us to scale independently. If user load increases, we can run `metrics.py` as a serverless Cloud Function, keeping the Streamlit UI lightweight."
