# SubsiSense

### Real-Time Mine Subsidence Monitoring & Risk Detection

SubsiSense is a prototype **real-time mine monitoring and subsidence risk detection system** designed to identify abnormal changes in underground mine conditions using multi-sensor data.

The system combines **rule-based threshold detection, temporal trend analysis, and unsupervised anomaly detection** to produce a unified risk score and generate interpretable alerts for individual monitoring nodes.

> **Current status:** Prototype / Research Project
> The current implementation uses synthetic sensor data to validate the live detection pipeline. The thresholds and results are **not intended for real-world mine safety decisions**.

---

## Problem

Underground mine instability can develop gradually through changes in:

* Ground elevation / subsidence
* Structural tilt
* Crack growth
* Ground vibration
* Other environmental and geotechnical signals

Monitoring these signals independently can make it difficult to distinguish normal fluctuations from developing instability.

SubsiSense aims to combine multiple signals and multiple time scales into a single **real-time risk assessment pipeline**.

---

## System Overview

```text
                    Sensor Nodes
                         │
                         ▼
                ┌─────────────────┐
                │ Data Ingestion  │
                │  / Validation   │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Preprocessing   │
                │ & Cleaning      │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Feature         │
                │ Engineering     │
                └────────┬────────┘
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
        Threshold      Trend     Anomaly
        Detector      Detector   Detector
             │           │           │
             └───────────┼───────────┘
                         ▼
                ┌─────────────────┐
                │  Risk Fusion    │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Risk Assessment │
                │ NORMAL / WATCH  │
                │ WARNING / CRIT. │
                └────────┬────────┘
                         │
                         ▼
                    Alert System
```

The intended production architecture is:

```text
Sensors
   │
   ▼
Redis Stream
   │
   ▼
Ingestion Adapter
   │
   ▼
CleanSensorReading
   │
   ▼
Live Risk Detection Engine
   │
   ├── Threshold Detection
   ├── Trend Detection
   └── Anomaly Detection
          │
          ▼
      Risk Fusion
          │
          ▼
        Alerts
```

---

## Current Prototype

The current implementation is contained primarily in:

```text
notebooks/
└── live_engine/
    └── live_engine_prototype.ipynb
```

The notebook implements the complete detection pipeline using a synthetic 24-hour dataset.

### Dataset

The prototype contains data from **5 simulated sensor nodes**:

```text
NODE_01
NODE_02
NODE_03
NODE_04
NODE_05
```

Each node produces one reading per second for 24 hours.

That results in:

**432,000 sensor observations**

The sensor data includes:

| Sensor           | Description                              |
| ---------------- | ---------------------------------------- |
| `position_x`     | Node X-coordinate                        |
| `position_y`     | Node Y-coordinate                        |
| `position_z`     | Vertical position / subsidence indicator |
| `tilt_x`         | Tilt along X-axis                        |
| `tilt_y`         | Tilt along Y-axis                        |
| `vibration_rms`  | RMS vibration                            |
| `vibration_peak` | Peak vibration                           |
| `crack_width`    | Measured crack width                     |
| `scenario`       | Synthetic ground-condition scenario      |

The synthetic scenario contains deterioration around **NODE_04 and NODE_05**, while other nodes exhibit normal or milder deterioration.

---

# Detection Pipeline

## 1. Data Preprocessing

Before detection, incoming sensor data is:

* Sorted chronologically per node
* Deduplicated
* Converted to numeric types
* Interpolated where appropriate
* Checked for missing sensor values

This creates a consistent representation of sensor readings for downstream processing.

---

## 2. Multi-Timescale Feature Engineering

Instead of relying only on instantaneous sensor values, SubsiSense analyzes changes across multiple time scales.

### Second scale

Instantaneous rates are calculated for:

* Vertical movement
* X/Y tilt
* Crack growth

For example:

```text
position_z_rate =
    Δposition_z / Δtime
```

### Minute scale

Short-term changes are calculated over approximately one minute:

```text
position_z_change_1m
tilt_x_change_1m
tilt_y_change_1m
crack_width_change_1m
```

Rolling vibration statistics are also calculated:

```text
vibration_mean_1m
vibration_std_1m
```

### Hour scale

Longer-term behavior is captured using approximately one-hour changes:

```text
position_z_change_1h
tilt_x_change_1h
tilt_y_change_1h
crack_width_change_1h
```

along with:

```text
vibration_mean_1h
vibration_std_1h
```

This allows the system to distinguish between short-lived fluctuations and persistent deterioration.

---

# Detection Methods

## 3. Threshold Detection

The threshold detector compares sensor-derived features against predefined severity levels:

```text
NORMAL
   ↓
WATCH
   ↓
WARNING
   ↓
CRITICAL
```

Example monitored features include:

* Vertical subsidence
* Tilt
* Crack growth
* Vibration

The prototype uses demonstration thresholds.

**These thresholds are not engineering-certified safety limits and must be replaced with validated mine-specific limits before any real deployment.**

---

## 4. Trend Detection

The trend detector looks for rapid or persistent changes rather than simply checking whether a value is large.

Examples include:

```text
Rapid tilt increase
Strong 1-hour tilt increase
Significant crack growth
```

This helps detect developing instability even when an absolute sensor value has not yet crossed a predefined safety threshold.

---

## 5. Isolation Forest Anomaly Detection

SubsiSense also uses an **Isolation Forest** for unsupervised anomaly detection.

The model is trained primarily on the synthetic normal period and learns the typical behavior of the monitoring system.

Features include:

```text
tilt_x_rate_sec
tilt_y_rate_sec
crack_width_rate_sec

tilt_x_change_1m
tilt_y_change_1m
crack_growth_1m

vibration_mean_1m
vibration_std_1m

position_z_change_1h
tilt_x_change_1h
tilt_y_change_1h
crack_growth_1h

vibration_mean_1h
vibration_std_1h
```

The resulting anomaly score is normalized to:

```text
0 → Normal
1 → Highly anomalous
```

An anomaly score above the prototype threshold can contribute to the final risk assessment.

---

# Risk Fusion

Instead of relying on a single detector, SubsiSense combines the outputs of all three detection mechanisms.

The current prototype uses:

```text
Risk Score =
    0.50 × Threshold Score
  + 0.25 × Trend Score
  + 0.25 × Anomaly Score
```

The resulting score is converted to a 0–100 scale.

### Risk levels

|   Score | Severity |
| ------: | -------- |
|  `< 50` | NORMAL   |
| `50–74` | WATCH    |
| `75–89` | WARNING  |
|  `≥ 90` | CRITICAL |

Each assessment also retains human-readable reasons from the individual detectors.

For example:

```text
WARNING risk at NODE_04

Reasons:
- position_z_change_1h exceeded warning threshold
- rapid tilt increase
- Isolation Forest anomaly
```

This makes the system more interpretable than using a black-box anomaly score alone.

---

# Prototype Results

The end-to-end prototype processes the synthetic dataset and generates:

* **432,000 raw sensor observations**
* **5 monitoring nodes**
* **24 hours of simulated readings**
* Multi-timescale engineered features
* Threshold-based detections
* Trend detections
* Isolation Forest anomaly scores
* Combined risk assessments
* Automated alerts

For notebook demonstration, the live engine evaluates every 10th reading to reduce execution time.

This produces:

```text
Risk assessments: 43,200
Alerts generated: 11,141
```

These numbers are **prototype outputs rather than measures of real-world detection performance**. In particular, the alert rate should not be interpreted as a validated false-positive or detection rate.

---

# Repository Structure

The current prototype:

```text
SubsiSense/
│
├── data/
│   └── Simulator_Gen_Synthetic/
│       └── mine_sensor_5nodes_with_z_subsidence.csv
│
├── notebooks/
│   └── live_engine/
│       └── live_engine_prototype.ipynb
│
├── README.md
└── .gitignore
```

The intended architecture for the next stage is:

```text
SubsiSense/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── ingestion/
│   ├── redis_stream.py
│   └── simulator.py
│
├── engines/
│   └── live/
│       ├── pipeline.py
│       ├── preprocessing.py
│       ├── features.py
│       │
│       ├── detectors/
│       │   ├── threshold.py
│       │   ├── trend.py
│       │   └── anomaly.py
│       │
│       ├── fusion/
│       │   └── risk_score.py
│       │
│       └── alerts/
│           └── alert_manager.py
│
├── notebooks/
│   └── live_engine/
│       └── live_engine_prototype.ipynb
│
├── tests/
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Technology Stack

### Programming

* Python
* Pandas
* NumPy

### Machine Learning

* Scikit-learn
* Isolation Forest
* StandardScaler

### Data Visualization

* Matplotlib

### Planned Infrastructure

* Redis Streams
* Real-time sensor ingestion
* Persistent time-series storage
* Real-time alerting

---

# Roadmap

## Phase 1 — Prototype

* [x] Synthetic multi-node sensor dataset
* [x] Data preprocessing
* [x] Multi-timescale feature engineering
* [x] Threshold detector
* [x] Trend detector
* [x] Isolation Forest anomaly detector
* [x] Risk fusion
* [x] Alert generation
* [x] Visualization

## Phase 2 — Engineering

* [ ] Move notebook logic into modular Python packages
* [ ] Implement Redis-based streaming ingestion
* [ ] Process individual sensor readings in real time
* [ ] Add unit and integration tests
* [ ] Add structured logging
* [ ] Add configuration files for detector thresholds
* [ ] Separate model training from inference

## Phase 3 — Monitoring Interface

* [ ] Real-time dashboard
* [ ] Node-wise risk visualization
* [ ] Historical sensor trends
* [ ] Alert history
* [ ] Mine layout visualization
* [ ] Sensor health monitoring

## Phase 4 — Advanced Risk Prediction

* [ ] Train models on real historical mine data
* [ ] Improve anomaly detection
* [ ] Add supervised failure prediction where labeled data exists
* [ ] Model spatial relationships between sensor nodes
* [ ] Add long-term subsidence forecasting
* [ ] Integrate geotechnical / physics-based simulation
* [ ] Evaluate against expert-defined safety criteria

---

# Limitations

This project is currently a research prototype.

The main limitations are:

1. **Synthetic data**

   The current dataset does not represent the complexity of real underground mine sensor data.

2. **Demonstration thresholds**

   Threshold values are manually selected for experimentation and are not validated engineering limits.

3. **Limited spatial modeling**

   Sensor nodes are currently treated mostly as independent monitoring points.

4. **No real-time infrastructure yet**

   The notebook simulates the live pipeline using CSV data. Redis-based ingestion is part of the planned architecture.

5. **Limited validation**

   The system has not yet been evaluated against real mine incidents or expert-labeled datasets.

Therefore, the current system should **not be used for operational mine safety decisions**.

---

# Future Direction

The long-term goal is to evolve SubsiSense from a prototype anomaly detector into a complete **real-time mine structural risk monitoring platform**.

The envisioned system combines:

```text
Real-time Sensors
       │
       ▼
Streaming Infrastructure
       │
       ▼
Real-time Risk Engine
       │
       ├── Threshold Analysis
       ├── Trend Analysis
       ├── Anomaly Detection
       └── Spatial Correlation
       │
       ▼
Risk Assessment
       │
       ├── Real-time Alerts
       └── Monitoring Dashboard
       │
       ▼
Historical Data
       │
       ▼
Long-term Prediction
       │
       └── Geotechnical / Physics-based Modeling
```

The goal is not simply to detect that **something changed**, but to determine:

> **What changed, how rapidly it is changing, where it is happening, how unusual it is, and whether multiple sensors indicate a developing instability.**

---

# Disclaimer

SubsiSense is an academic/research prototype.

It is **not a certified mine safety system** and must not be used to make operational safety decisions.

All sensor data and thresholds currently included in the repository are synthetic or experimental.

---


## License

This project is currently intended for academic and research purposes.
