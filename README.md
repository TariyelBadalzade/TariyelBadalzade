<!-- Modern GitHub profile README -->

<h1 align="center">Hi, I'm Tariyel Badalzade 👋</h1>

<p align="center">
  <strong>Machine Learning · Data Science · Computer Vision</strong><br>
  Building practical AI and data solutions at the intersection of software and engineering.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Focus-Machine%20Learning-2563eb?style=flat" alt="Focus: Machine Learning">
  <img src="https://img.shields.io/badge/Location-Azerbaijan-64748b?style=flat" alt="Location: Azerbaijan">
</p>

---

## About me

I'm an AI Engineer at **AZENROB** and an MSc student in **Machine Learning at Baku Engineering University**. With a BSc background in Process Automation Engineering from Baku Higher Oil School, I enjoy applying machine learning and analytics to real-world engineering problems.

- 🛰️ Interested in geospatial AI, satellite imagery, and computer vision
- 📊 Working with data analysis, SQL, and dashboards
- ⚙️ Interested in industrial systems, automation, and energy analytics
- 🌱 Focused on building reliable, well-documented, reproducible projects

## Tech stack

<p>
  <strong>Languages & data</strong><br>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/SQL-4479A1?style=flat&logo=mysql&logoColor=white" alt="SQL">
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/C%2B%2B-00599C?style=flat&logo=cplusplus&logoColor=white" alt="C++">
</p>
<p>
  <strong>Machine learning & vision</strong><br>
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=flat&logo=pytorch&logoColor=white" alt="PyTorch">
  <img src="https://img.shields.io/badge/TensorFlow-FF6F00?style=flat&logo=tensorflow&logoColor=white" alt="TensorFlow">
  <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=flat&logo=opencv&logoColor=white" alt="OpenCV">
  <img src="https://img.shields.io/badge/YOLO-111F68?style=flat" alt="YOLO">
  <img src="https://img.shields.io/badge/SAM-Segment%20Anything-64748b?style=flat" alt="Segment Anything Model">
</p>
<p>
  <strong>Analytics & tools</strong><br>
  <img src="https://img.shields.io/badge/Power%20BI-F2C811?style=flat&logo=powerbi&logoColor=111111" alt="Power BI">
  <img src="https://img.shields.io/badge/Git-F05032?style=flat&logo=git&logoColor=white" alt="Git">
  <img src="https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=111111" alt="Linux">
  <img src="https://img.shields.io/badge/QGIS-589632?style=flat&logo=qgis&logoColor=white" alt="QGIS">
</p>

## Featured work

### 🛰️ [Flood detection and route planning](projects/flood-detection/)

My bachelor's dissertation connects **flood detection from satellite imagery** with **road-network route planning**. I built a Python pipeline that takes two-band **Sentinel-1 SAR** imagery, predicts a pixel-level water/flood mask with a **PyTorch U-Net**, and overlays the result on **OpenStreetMap** roads to explore routes with **Dijkstra / A\***.

![Spain example showing VV and VH satellite imagery, predicted flooding, road classifications, and a generated route](projects/flood-detection/images/spain-routing-overview.png)

*From image to map: VV/VH radar inputs → predicted mask in blue → road exposure in green/red → a generated route in yellow. Historical project output; the route is illustrative.*

**What I worked on**

- **Flood segmentation:** two-channel U-Net, training-only normalization, augmentation, flood-weighted sampling, and focal + Dice loss.
- **Geospatial integration:** georeferenced raster predictions, road buffering in metres, and flood-overlap estimates for each road edge.
- **Route exploration:** origin/destination matching, flood-aware edge costs, Dijkstra/A* search, and GeoTIFF / GeoJSON exports.
- **Evaluation and visual analysis:** saved test results from Spain and Sri Lanka, plus qualitative application examples from the dissertation, including Baku.

| Flood IoU | F1 / Dice | Precision | Recall | Test chips |
| ---: | ---: | ---: | ---: | ---: |
| **0.6766** | **0.8071** | 0.7770 | 0.8396 | 66 |

Scores pool valid pixels from the saved test evaluation. Validation and test both include Spain; the project documents this evaluation limitation. Additional application images are qualitative examples and do not add to these test scores.

[Read the full case study and image walkthrough](projects/flood-detection/) · [Explore the code and setup](projects/flood-detection/#included-files) · [Inspect the evaluation](projects/flood-detection/reports/evaluation_results.json) · [Read the method and limitations](projects/flood-detection/reports/METHODS.md)

Research prototype; generated routes have not been validated for emergency navigation.

### 📊 [Azerbaijan ISP Analytics Dashboard](projects/azerbaijan-isp-analytics/)

A four-page **Power BI** dashboard for subscriber trends, tariff adoption, static-IP billing, and geographic analysis. Built with **DAX**, **Power Query**, a calendar model, and interactive bookmark navigation.

**10,000 synthetic subscribers · 10,000 billing records · 75 administrative units · 12 Baku districts**

![Azerbaijan ISP analytics — synthetic subscriber overview](projects/azerbaijan-isp-analytics/images/overview.png)

**Page 2 — Tariffs**

![Tariff analysis with synthetic data](projects/azerbaijan-isp-analytics/images/tariffs.png)

**Page 3 — Static-IP billing**

![Static-IP subscribers and billing with synthetic data](projects/azerbaijan-isp-analytics/images/static-ip.png)

**Page 4 — Regions**

![Regional analysis and synthetic subscriber details](projects/azerbaijan-isp-analytics/images/regions.png)

[Explore the case study](projects/azerbaijan-isp-analytics/) · [Read the data assumptions](projects/azerbaijan-isp-analytics/docs/DATA_METHODOLOGY.md)

**Synthetic data — portfolio demonstration.** Geographic weights use public Azerbaijan statistics; customer-level data and business results are fictional.

### ⚡ [Grid Energy — IoT and ML for Energy Management](projects/grid-energy/)

A **Baku Higher Oil School team project** exploring energy-demand forecasting and IoT monitoring for urban and industrial buildings. **My contribution: machine learning and modeling** for the energy-forecasting component.

The team report describes **ARIMA/SARIMA, LSTM, and Random Forest** approaches alongside an **ESP32 / MQTT** monitoring architecture.

<p align="center">
  <img src="projects/grid-energy/images/team-demonstration.jpg" alt="Grid Energy team presenting the energy-management demonstration" width="480">
</p>

[Read the project case study](projects/grid-energy/)

Team demonstration and documented approach; measured forecasting results are not included.

*The flood project includes source and saved evaluation evidence. The Power BI project includes a working report, synthetic datasets, dashboard previews, and documented assumptions. Grid Energy includes a team demonstration and a documented forecasting approach.*

### ♻️ [Water Trash Classification](projects/water-trash-classification/)

A team course project combining **TensorFlow/Keras**, **OpenCV**, and webcam classification with **voice alerts** for a proposed water-cleanup application. Includes a separate CNN experiment and saved validation evidence.

![Webcam waste-classification demonstration](projects/water-trash-classification/images/webcam-demo.jpg)

**Historical validation accuracy: 78.81% across 1,180 images**, calculated from the saved CNN confusion matrix. The webcam screenshot is a separate demonstration; its confidence score is not an accuracy result.

[Explore the project and code](projects/water-trash-classification/) · [Inspect the saved evaluation](projects/water-trash-classification/reports/evaluation.json)

## Experience

- **AZENROB** — AI engineering and operational data analytics
- **Azercosmos** — AI engineering internship focused on satellite imagery and geospatial data

## Education & certification

- **MSc, Machine Learning** — Baku Engineering University
- **BSc, Process Automation Engineering** — Baku Higher Oil School
- **Supervised Machine Learning — Course Completion** — Stanford University & DeepLearning.AI
- **HCIA — Artificial Intelligence V3.0 — Course Completion** — Huawei

---

<p align="center">
  <em>Learning continuously. Building thoughtfully. Measuring what matters.</em>
</p>

## Connect

[LinkedIn](https://www.linkedin.com/in/tariyelbadalzade/)
