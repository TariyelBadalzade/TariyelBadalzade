# Method, evidence, and limitations

## Model and training implementation

The published source uses a two-input-channel U-Net with four encoder/decoder levels, batch normalization, skip connections, and bottleneck dropout. Configuration selects base width 32 and dropout 0.3. The network returns logits; inference applies sigmoid and thresholds probabilities.

Training uses weighted focal loss plus Dice loss, AdamW, cosine learning-rate scheduling, early stopping, and mixed precision on CUDA. The dataset applies flips, rotations, Gaussian noise, and weighted sampling favoring flood-containing chips. Training-only mean/std normalization is embedded in saved checkpoints. Current configuration values describe the published code; they are not proof of the exact settings behind the historical results.

## Saved evaluation

`evaluation_results.json` is an unchanged copy of the original saved results: 66 chip-level records and aggregate scores. Chip names match the provided test manifest. Summing per-chip confusion counts yields:

| Count | Pixels |
| :--- | ---: |
| True positives | 1,606,208 |
| False positives | 460,866 |
| False negatives | 306,835 |
| True negatives | 13,835,117 |

Flood IoU = TP / (TP + FP + FN); F1 = 2TP / (2TP + FP + FN). Precision, recall, and accuracy use the same pooled counts. The published rounded aggregates match these counts. These are not averages of chip scores or mean IoU across classes. The evaluator excludes invalid labels and SAR pixels invalid in the first band.

The saved file does not record a checkpoint hash, evaluation timestamp, or threshold. No inference or training was rerun during portfolio preparation, and the reported results have no supplied baseline or uncertainty interval. Per-chip performance varies substantially; inspect the full results rather than relying only on aggregate accuracy.

## Routing limitations

Roads are retrieved from OSM and projected to UTM. Approximate width buffers are overlaid on predicted flood pixels. Flood exposure sets edge weights for Dijkstra/A*; nearby dry nodes may replace requested endpoints. A returned GeoJSON can contain flooded edges and a warning because flood penalties are finite.

Roads outside the raster footprint and SAR nodata regions can be classified as dry. OSM completeness, image age, georeferencing, and the lack of flood-depth or real-time road condition information further limit interpretation. Routing has no supplied ground-truth evaluation. The `road_types` list in the configuration is currently not passed through by `pipeline.py`; road extraction uses its built-in default list.

The existing map visualization applies a logarithmic conversion even though the expected SAR input is already dB. Its background contrast should be corrected before using it for qualitative comparisons; the portfolio chart is generated directly from numerical evaluation evidence instead.

## Qualitative figures

The portfolio now includes three unchanged PNG figures extracted from `Tariyel_Badalzade_Diploma_Work.docx`: a Spain routing example (`Spain_7370579_S1Hand`), a Spain flood/road overlay (`Spain_8565131_S1Hand`), and a Baku application (`Baku_April2026_S1_chip_006`). Their captions follow the chip IDs and visible annotations in the images. Dissertation prose and figure descriptions are not used to assert additional routing successes, baseline comparisons, or measured generalization.

These are historical visualization outputs, not fresh inference runs or paired ground-truth/prediction comparisons. The local `batch_show_results.py` uses direct percentile stretching of SAR channels and a road threshold of 0.30, whereas the published pipeline configuration uses 0.10. Exact configuration and checkpoint provenance for each figure are unavailable. The logarithmic-display issue noted above concerns the retained `visualize.py`, not proof that every historical multi-panel figure was generated with that path.

Blue masks may include permanent water. No independent labels or quantitative evaluation for the Baku, Valencia, or Dubai application images were supplied with the figures. The figures do not establish emergency route safety. Image sources and checksums are recorded in [image provenance](../images/README.md).

## Publication checks

All included Python files were parsed for syntax. Split counts, disjoint chip paths, evaluation chip membership, and aggregate confusion-count arithmetic were checked. Raw data and checkpoints are excluded. Dependency installation, training, inference, live OSM requests, and full routing execution remain unverified. The original local virtual environment could not start because it references a missing interpreter on another user path.
