# Autonomous Anomaly Detection & Response Agent

An automated system that detects anomalies in data streams and triggers reasoning agents for response.

## 🛠️ Tech Stack
* **Python 3.14**
* **Machine Learning:** Isolation Forest (`models/iso_forest.joblib`)
* **Ingestion:** Kafka (`kafka_ingestion.py`)
* **Visualization:** Dashboard (`dashboard.py`)

## 🚀 How It Works
1.  **Ingestion:** Data is ingested via Kafka.
2.  **Detection:** The ML model scans for anomalies.
3.  **Response:** The Reasoning Agent determines the best action.
