# Data and split manifests

Source: [Sen1Floods11](https://github.com/cloudtostreet/Sen1Floods11). Follow the upstream download instructions and terms; imagery and labels are not bundled here.

The loader expects two-channel Sentinel-1 SAR GeoTIFFs in **VV, VH** order, already in **dB**, and spatially aligned single-band labels: 0 = non-flood, 1 = flood, -1 or 255 = invalid. Use NaN for missing SAR values as expected by the existing finite-value checks; finite nodata sentinels need preprocessing. Normalization statistics are computed on training chips and saved with the model checkpoint. Do not apply another logarithmic transform to dB input.

Preserve the relative file paths in the manifests:

```text
data/sen1floods11/S1Hand/<chip>_S1Hand.tif
data/sen1floods11/LabelHand/<chip>_LabelHand.tif
data/splits/train.json
data/splits/val.json
data/splits/test.json
```

Check the exact label paths in each JSON manifest when arranging your download. Commands resolve these paths from the project directory. Paths were converted from Windows backslashes to forward slashes without changing split membership.

| Split | Chips | Location prefixes |
| :--- | ---: | :--- |
| Training | 373 | Bolivia, Ghana, India, Mekong, Nigeria, Pakistan, Paraguay, Somalia, USA |
| Validation | 6 | Spain |
| Test | 66 | Spain, Sri-Lanka |

No identical chip path appears in multiple splits. Validation and test share the Spain prefix; geographic overlap between different chips was not assessed. These manifests document the existing experiment, not a claim of a fully independent event-level benchmark. A stricter future experiment should separate events across all splits and regenerate training statistics.

Raw imagery, labels, cached sampling fractions, and normalization caches are excluded from Git. No download or preprocessing script is included; users must obtain and arrange compatible data before training.
