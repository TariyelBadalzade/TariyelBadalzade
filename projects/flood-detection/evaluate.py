"""
Usage:
    python evaluate.py --config config.yaml
"""

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
import torch
from tqdm import tqdm
import yaml

from models.unet import UNet
from predict import load_model, preprocess_chip


# ── Metric computation ────────────────────────────────────────────────────────

def compute_metrics(pred_bin: np.ndarray, label: np.ndarray, valid: np.ndarray) -> dict:
    p = pred_bin[valid].astype(bool)
    t = (label[valid] == 1)

    tp = int((p  &  t).sum())
    fp = int((p  & ~t).sum())
    fn = int((~p &  t).sum())
    tn = int((~p & ~t).sum())

    iou       = tp / (tp + fp + fn + 1e-6)
    f1        = 2 * tp / (2 * tp + fp + fn + 1e-6)
    precision = tp / (tp + fp + 1e-6)
    recall    = tp / (tp + fn + 1e-6)
    accuracy  = (tp + tn) / (tp + tn + fp + fn + 1e-6)

    return {
        "iou":       round(iou,       4),
        "f1":        round(f1,        4),
        "precision": round(precision, 4),
        "recall":    round(recall,    4),
        "accuracy":  round(accuracy,  4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


# ── Main evaluation loop ──────────────────────────────────────────────────────

def evaluate(cfg: dict):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model, mean, std = load_model(cfg["checkpoint"], device)
    model.eval()

    threshold = cfg.get("seg_threshold", 0.5)

    with open(Path(cfg["split_dir"]) / "test.json") as f:
        test_info = json.load(f)

    chip_paths  = test_info["chips"]
    label_paths = test_info["labels"]

    all_metrics = []
    aggregate   = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}

    print(f"\nEvaluating {len(chip_paths)} test chips at threshold={threshold}...")
    print("-" * 70)

    for chip_path, label_path in tqdm(zip(chip_paths, label_paths), total=len(chip_paths)):
        tensor, _, valid_mask = preprocess_chip(chip_path, mean, std)
        tensor = tensor.to(device)

        with torch.no_grad():
            logits   = model(tensor)
            prob_map = torch.sigmoid(logits).squeeze().cpu().numpy()  # sigmoid here

        pred_bin = (prob_map >= threshold).astype(np.uint8)
        pred_bin[~valid_mask] = 0

        with rasterio.open(label_path) as src:
            label = src.read(1).astype(np.float32)
        label[label == 255] = -1
        valid = valid_mask & (label != -1)

        metrics = compute_metrics(pred_bin, label, valid)
        metrics["chip"] = Path(chip_path).name
        all_metrics.append(metrics)

        for key in ("tp", "fp", "fn", "tn"):
            aggregate[key] += metrics[key]

    # ── Aggregate metrics ─────────────────────────────────────────────────────
    tp, fp, fn, tn = aggregate["tp"], aggregate["fp"], aggregate["fn"], aggregate["tn"]

    agg_iou       = tp / (tp + fp + fn + 1e-6)
    agg_f1        = 2 * tp / (2 * tp + fp + fn + 1e-6)
    agg_precision = tp / (tp + fp + 1e-6)
    agg_recall    = tp / (tp + fn + 1e-6)
    agg_accuracy  = (tp + tn) / (tp + tn + fp + fn + 1e-6)

    mean_iou = float(np.mean([m["iou"] for m in all_metrics]))
    mean_f1  = float(np.mean([m["f1"]  for m in all_metrics]))

    print("\n" + "=" * 70)
    print("AGGREGATE TEST RESULTS")
    print("=" * 70)
    print(f"  IoU (flood):         {agg_iou:.4f}  (mean per-chip: {mean_iou:.4f})")
    print(f"  F1 Score:            {agg_f1:.4f}  (mean per-chip: {mean_f1:.4f})")
    print(f"  Precision:           {agg_precision:.4f}")
    print(f"  Recall:              {agg_recall:.4f}")
    print(f"  Pixel Accuracy:      {agg_accuracy:.4f}")
    print(f"  True Positives:      {tp:,}")
    print(f"  False Positives:     {fp:,}")
    print(f"  False Negatives:     {fn:,}")
    print(f"  True Negatives:      {tn:,}")
    print("=" * 70)

    print("\nPER-CHIP RESULTS:")
    print(f"{'Chip':<45} {'IoU':>6} {'F1':>6} {'Prec':>6} {'Rec':>6} {'Acc':>6}")
    print("-" * 75)
    for m in all_metrics:
        print(
            f"{m['chip']:<45} "
            f"{m['iou']:>6.4f} {m['f1']:>6.4f} "
            f"{m['precision']:>6.4f} {m['recall']:>6.4f} "
            f"{m['accuracy']:>6.4f}"
        )

    results = {
        "aggregate": {
            "iou":       round(agg_iou,       4),
            "f1":        round(agg_f1,        4),
            "precision": round(agg_precision, 4),
            "recall":    round(agg_recall,    4),
            "accuracy":  round(agg_accuracy,  4),
        },
        "per_chip": all_metrics,
    }

    out_path = Path(cfg.get("output_dir", "outputs")) / "evaluation_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to: {out_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    evaluate(cfg)
