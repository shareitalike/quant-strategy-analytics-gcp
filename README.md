# Quantitative Strategy Dashboard

A production-grade Python analytics platform for evaluating trading strategy performance. This application processes trade logs, calculates institutional-grade financial metrics (Sharpe, Sortino, Calmar), and provides interactive visualizations for deep performance analysis.

## 🏗️ Architecture

The application has been refactored from a monolithic script into a modern, modular micro-architecture designed for maintainability and cloud scalability.

### 1. `app.py` (Orchestration Layer)
- **Responsibility**: UI rendering (Streamlit), state management, and user interaction.
- **Function**: Acts as the controller, initializing the interface and delegating heavy lifting to specialized modules. It contains **no complex business logic**, ensuring the UI remains responsive and lightweight.

### 2. `metrics.py` (Logic Layer)
- **Responsibility**: Pure quantitative analysis.
- **Function**: Contains all financial formulas and simulation engines (Monte Carlo, Compounding).
- **Design Pattern**: Functional and stateless. This module is purely Python/Pandas/NumPy and has **zero dependencies on the UI**. It can be easily ported to run as a backend API (FastAPI/Flask) or a serverless Cloud Function.

### 3. `charts.py` (Visualization Layer)
- **Responsibility**: Data visualization.
- **Function**: Generates Plotly graph objects. Decoupling visualization allows for consistent styling and easy updates to chart aesthetics without risking breaks in calculation logic.

### 4. `io_layer.py` (Data Access Layer)
- **Responsibility**: Data ingestion and standardization.
- **Function**: Abstracts the file reading process. Currently configured for local Excel files, but designed to be swapped with a Cloud Storage (GCS/S3) connector with minimal code changes.

## 🚀 Cloud Readiness & Refactoring Rationale

This modularization was performed to transition the codebase from a "script" to a "platform".

- **Scalability**: By separating `metrics.py` (CPU bound) from `app.py` (IO/UI bound), future deployments can offload calculations to dedicated worker nodes if datasets grow to Big Data scale.
- **Testability**: The `metrics.py` module is now independently unit-testable. We can verify financial accuracy without spinning up a web server.
- **Cloud Native**: The `io_layer.py` abstraction allows us to inject cloud storage clients (e.g., Google Cloud Storage) without rewriting any analysis code. The stateless nature of the modules fits perfectly with containerized environments (Docker/Kubernetes).

## 🛠️ How to Run

1. **Install Dependencies**:
   ```bash
   pip install streamlit pandas plotly openpyxl xlsxwriter numpy
   ```

2. **Launch Application**:
   ```bash
   streamlit run app.py
   ```

3. **Usage**:
   - Select your data folder in the sidebar.
   - Adjust capital and risk settings.
   - Explore the tabs for Heatmaps, Drawdown analysis, and Monte Carlo simulations.
