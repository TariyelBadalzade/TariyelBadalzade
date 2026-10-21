# Proposed project plan

The flood project now has [published source and saved evaluation evidence](projects/flood-detection/). The analytics and forecasting projects below remain proposals.

## 1. Operational performance analysis

**Suggested repository:** `operations-analytics-sql`

**Question:** Which customers, products, or operational processes explain changes in revenue and service performance?

**Data:** A documented public transaction dataset. If using generated data, label it synthetic and explain its assumptions. Do not upload internal AZENROB data without permission.

**Build:** Define the data model; check missing values, duplicate records, and joins; write SQL using CTEs and window functions; analyze trends and customer segments; produce a Power BI report with screenshots or a PDF for readers without Power BI.

**Show:** SQL files, a metric dictionary, revenue and customer trend plots, a dashboard preview, and three findings supported by numbers. Distinguish observed associations from causal explanations.

**Quality checks:** Reconcile aggregate totals, verify join cardinality, document date filters, and state how refunds and missing values affect the metrics.

## 2. Energy demand forecasting

**Suggested repository:** `energy-demand-forecasting`

**Question:** How accurately can next-day energy demand be predicted from information available at forecast time?

**Data:** A public hourly electricity demand dataset with documented source, timezone, units, and reuse terms.

**Build:** Explore daily and weekly seasonality; handle missing timestamps; use chronological training, validation, and final test periods; compare a seasonal naive forecast against a simple statistical or regression model, then a tree-based model if useful.

**Show:** Forecast and actual plots, MAE and RMSE for every model, errors by hour or day, and a discussion of operational usefulness.

**Quality checks:** Use rolling validation inside the development period. Create lags without future information. Do not use observed future weather as though it were available in production. Keep the final test period untouched during model selection.

## 3. Flood segmentation from satellite imagery — source and saved results published

**Current location:** [projects/flood-detection](projects/flood-detection/). The following describes further improvements.

**Question:** Can a segmentation model identify flooded areas in satellite images from unseen locations or events?

**Data:** Public satellite imagery with suitable flood annotations and documented reuse terms. Verify sensor type, band definitions, masks, and label quality before choosing the model.

**Build:** Document preprocessing and alignment; separate locations or events across splits; compare a suitable simple baseline with a segmentation model; evaluate on held-out scenes.

**Show:** Input images, ground-truth masks, predictions, IoU and Dice scores, and examples where the model fails.

**Quality checks:** Prevent neighboring or overlapping tiles from leaking across splits. Explain clouds, permanent water, class imbalance, and the limits of transferring between events. Inspect metrics per event or scene as well as overall.

**Optional extension:** Explore route planning as a separately evaluated prototype. Predicted flood masks alone cannot establish that a route is safe.

## Recommended order

Start by reproducing the published flood experiment in a clean environment and improving its evaluation and visual examples. Then develop the proposed SQL analytics and forecasting projects.

Before adding another project, improve the existing ones: clearer documentation, a useful visual, reproducibility, and a fair evaluation usually provide more value than another unfinished notebook.
