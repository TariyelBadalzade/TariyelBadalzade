import json
from pathlib import Path
from typing import List, Tuple

import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler


LABEL_FLOOD   = 1
LABEL_NOFLOOD = 0
LABEL_INVALID = -1


class Sen1Floods11Dataset(Dataset):

    def __init__(
        self,
        chip_paths: List[str],
        label_paths: List[str],
        mean: np.ndarray,
        std: np.ndarray,
        augment: bool = False,
        flood_fractions: List[float] = None,
    ):
        assert len(chip_paths) == len(label_paths)
        self.chips   = chip_paths
        self.labels  = label_paths
        self.mean    = mean.astype(np.float32)   # shape (2,), dB scale
        self.std     = std.astype(np.float32)    # shape (2,), dB scale
        self.augment = augment

        if flood_fractions is not None:
            self._flood_fractions = flood_fractions
        else:
            self._flood_fractions = self._compute_flood_fractions()

    def __len__(self) -> int:
        return len(self.chips)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        with rasterio.open(self.chips[idx]) as src:
            img = src.read().astype(np.float32)   # (2, H, W) already in dB

        lbl = self._read_label(self.labels[idx])

        # Valid SAR pixels = finite values (NaN = nodata)
        valid_sar = np.isfinite(img[0])   # VV band drives validity

        # Replace NaN with 0 so normalisation doesn't propagate NaN
        img = np.where(np.isfinite(img), img, 0.0)

        # Normalise directly — data is already in dB
        img_norm = (img - self.mean[:, None, None]) / (self.std[:, None, None] + 1e-8)

        # Zero out nodata pixels
        img_norm[:, ~valid_sar] = 0.0

        # Combine SAR validity with label validity
        label_valid = (lbl != LABEL_INVALID)
        valid = (valid_sar & label_valid).astype(np.float32)
        lbl   = np.clip(lbl, 0.0, 1.0)

        if self.augment:
            img_norm, lbl, valid = self._augment(img_norm, lbl, valid)

        return (
            torch.from_numpy(img_norm.copy()),
            torch.from_numpy(lbl.copy()).unsqueeze(0),
            torch.from_numpy(valid.copy()).unsqueeze(0),
        )

    def get_weighted_sampler(self) -> WeightedRandomSampler:
        weights = [max(f, 0.05) for f in self._flood_fractions]
        return WeightedRandomSampler(weights=weights, num_samples=len(weights), replacement=True)

    @staticmethod
    def _read_label(path: str) -> np.ndarray:
        with rasterio.open(path) as src:
            lbl = src.read(1)
        lbl = lbl.astype(np.float32)
        lbl[lbl == 255] = LABEL_INVALID
        return lbl

    def _compute_flood_fractions(self) -> List[float]:
        fractions = []
        for lp in self.labels:
            lbl   = self._read_label(lp)
            valid = lbl != LABEL_INVALID
            frac  = float((lbl[valid] == LABEL_FLOOD).mean()) if valid.any() else 0.0
            fractions.append(frac)
        return fractions

    @staticmethod
    def _augment(img, lbl, valid):
        if np.random.rand() < 0.5:
            img, lbl, valid = img[:, :, ::-1], lbl[:, ::-1], valid[:, ::-1]
        if np.random.rand() < 0.5:
            img, lbl, valid = img[:, ::-1, :], lbl[::-1, :], valid[::-1, :]
        k = np.random.randint(0, 4)
        if k > 0:
            img   = np.rot90(img,   k, axes=(1, 2)).copy()
            lbl   = np.rot90(lbl,   k, axes=(0, 1)).copy()
            valid = np.rot90(valid, k, axes=(0, 1)).copy()
        img = img + np.random.normal(0.0, 0.05, img.shape).astype(np.float32)
        return img, lbl, valid


# ── Normalisation statistics ─────────────────────────────────────────────────

def compute_normalisation_stats(
    chip_paths: List[str],
    label_paths: List[str],
) -> Tuple[np.ndarray, np.ndarray]:

    sums    = np.zeros(2, dtype=np.float64)
    sq_sums = np.zeros(2, dtype=np.float64)
    counts  = np.zeros(2, dtype=np.int64)

    print(f"  Computing stats over {len(chip_paths)} chips (already in dB)...")
    for path in chip_paths:
        with rasterio.open(path) as src:
            img = src.read().astype(np.float64)   # (2, H, W)
        for c in range(min(2, img.shape[0])):
            v = img[c][np.isfinite(img[c])]        # finite only — negatives ARE valid
            if len(v) == 0:
                continue
            sums[c]    += v.sum()
            sq_sums[c] += (v ** 2).sum()
            counts[c]  += len(v)

    mean = np.where(counts > 0, sums / counts, 0.0)
    std  = np.where(counts > 0,
                    np.sqrt(np.maximum(sq_sums / np.maximum(counts, 1) - mean ** 2, 1e-8)),
                    1.0)

    print(f"  VV: mean={mean[0]:.2f} dB  std={std[0]:.2f}")
    print(f"  VH: mean={mean[1]:.2f} dB  std={std[1]:.2f}")

    return mean.astype(np.float32), std.astype(np.float32)


# ── DataLoader factory ────────────────────────────────────────────────────────

def build_dataloaders(
    split_dir: str,
    data_dir: str,
    mean: np.ndarray,
    std: np.ndarray,
    batch_size: int = 4,
    num_workers: int = 0,
    train_subset: int = None,
):
    loaders         = {}
    cache_path      = Path(split_dir) / "flood_fractions_cache.json"
    fractions_cache = {}
    if cache_path.exists():
        with open(cache_path) as f:
            fractions_cache = json.load(f)
    cache_updated = False

    for split in ("train", "val", "test"):
        split_file = Path(split_dir) / f"{split}.json"
        with open(split_file) as f:
            info = json.load(f)

        chips   = info["chips"]
        labels  = info["labels"]
        augment = (split == "train")

        if split == "train" and train_subset is not None:
            import random
            combined = list(zip(chips, labels))
            random.shuffle(combined)
            chips, labels = zip(*combined[:train_subset])
            chips, labels = list(chips), list(labels)
            print(f"  Using {len(chips)} training chips (subset)")

        missing_chips  = [c for c in chips if c not in fractions_cache]
        missing_labels = [labels[list(chips).index(c)] for c in missing_chips]

        if missing_chips:
            print(f"  [{split}] Computing flood fractions for {len(missing_chips)} chips...")
            tmp = Sen1Floods11Dataset(
                chip_paths=missing_chips, label_paths=missing_labels,
                mean=mean, std=std, augment=False,
            )
            for chip, frac in zip(missing_chips, tmp._flood_fractions):
                fractions_cache[chip] = frac
            cache_updated = True

        fractions = [fractions_cache.get(c, 0.05) for c in chips]

        dataset = Sen1Floods11Dataset(
            chip_paths=list(chips), label_paths=list(labels),
            mean=mean, std=std, augment=augment, flood_fractions=fractions,
        )

        if split == "train":
            sampler = dataset.get_weighted_sampler()
            loader  = DataLoader(dataset, batch_size=batch_size, sampler=sampler,
                                 num_workers=num_workers, pin_memory=True,
                                 persistent_workers=False, drop_last=True)
        else:
            loader = DataLoader(dataset, batch_size=batch_size, shuffle=False,
                                num_workers=num_workers, pin_memory=True,
                                persistent_workers=False)
        loaders[split] = loader

    if cache_updated:
        with open(cache_path, "w") as f:
            json.dump(fractions_cache, f)

    return loaders["train"], loaders["val"], loaders["test"]
