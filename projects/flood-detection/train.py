"""
Usage:
    python train.py --config config.yaml
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.cuda.amp import GradScaler, autocast
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm
import yaml

from models.unet import UNet
from dataset import Sen1Floods11Dataset, compute_normalisation_stats, build_dataloaders


# ── Reproducibility ───────────────────────────────────────────────────────────

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = False
    torch.backends.cudnn.benchmark     = True


# ── Loss ─────────────────────────────────────────────────────────────────────

def focal_dice_loss(
    logits: torch.Tensor,
    target: torch.Tensor,
    valid: torch.Tensor,
    flood_weight: float = 3.0,
    gamma: float = 2.0,
    eps: float = 1e-6,
) -> torch.Tensor:

    logits = logits.float()
    target = target.float()
    valid  = valid.float()

    prob = torch.sigmoid(logits)

    # ── Focal loss ────────────────────────────────────────────────────────────
    bce  = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    p_t  = prob * target + (1 - prob) * (1 - target)      # prob of correct class
    focal_weight = (1 - p_t) ** gamma                      # down-weight easy examples

    # Class weight for flood pixels
    alpha = torch.where(target == 1,
                        torch.full_like(target, flood_weight),
                        torch.ones_like(target))

    focal = (alpha * focal_weight * bce * valid).sum() / (valid.sum() + eps)

    # ── Dice loss ─────────────────────────────────────────────────────────────
    p = prob * valid
    t = target * valid
    intersection = (p * t).sum()
    dice = 1.0 - (2.0 * intersection + eps) / (p.sum() + t.sum() + eps)

    return focal + dice


# ── Metrics ───────────────────────────────────────────────────────────────────

@torch.no_grad()
def compute_iou(logits, target, valid, threshold=0.5):
    prob     = torch.sigmoid(logits.float())
    pred_bin = (prob > threshold).float() * valid
    target_v = target * valid
    tp = (pred_bin * target_v).sum().item()
    fp = (pred_bin * (1 - target_v)).sum().item()
    fn = ((1 - pred_bin) * target_v).sum().item()
    return tp / (tp + fp + fn + 1e-6)


# ── Validation ────────────────────────────────────────────────────────────────

@torch.no_grad()
def validate(model, loader, device, flood_weight):
    if len(loader) == 0:
        return None, None
    model.eval()
    total_loss, total_iou, n = 0.0, 0.0, 0
    for imgs, lbls, valid in loader:
        imgs  = imgs.to(device)
        lbls  = lbls.to(device)
        valid = valid.to(device)
        with autocast():
            logits = model(imgs)
        loss = focal_dice_loss(logits, lbls, valid, flood_weight)
        total_loss += loss.item()
        total_iou  += compute_iou(logits, lbls, valid)
        n += 1
    return total_loss / n, total_iou / n


# ── Training ──────────────────────────────────────────────────────────────────

def train(cfg: dict):
    set_seed(cfg.get("seed", 42))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # ── Normalisation statistics ──────────────────────────────────────────────
    stats_path = Path(cfg["split_dir"]) / "norm_stats.json"
    if stats_path.exists():
        with open(stats_path) as f:
            stats = json.load(f)
        mean = np.array(stats["mean"], dtype=np.float32)
        std  = np.array(stats["std"],  dtype=np.float32)
        print(f"Loaded normalisation stats: VV mean={mean[0]:.2f} VH mean={mean[1]:.2f}")
    else:
        print("Computing normalisation statistics...")
        with open(Path(cfg["split_dir"]) / "train.json") as f:
            train_info = json.load(f)
        mean, std = compute_normalisation_stats(train_info["chips"], train_info["labels"])
        with open(stats_path, "w") as f:
            json.dump({"mean": mean.tolist(), "std": std.tolist()}, f)

    # ── DataLoaders ───────────────────────────────────────────────────────────
    train_loader, val_loader, _ = build_dataloaders(
        split_dir=cfg["split_dir"],
        data_dir=cfg["data_dir"],
        mean=mean, std=std,
        batch_size=cfg.get("batch_size", 4),
        num_workers=cfg.get("num_workers", 0),
        train_subset=cfg.get("train_subset", None),
    )

    has_val = len(val_loader) > 0
    print(f"Train batches: {len(train_loader)} | Val batches: {len(val_loader)}")

    # ── Model ─────────────────────────────────────────────────────────────────
    model = UNet(
        in_channels=cfg.get("in_channels", 2),
        base_ch=cfg.get("base_ch", 32),
        dropout=cfg.get("dropout", 0.5),
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model parameters: {total_params:,}")

    optimizer = AdamW(
        model.parameters(),
        lr=cfg.get("lr", 5e-5),
        weight_decay=cfg.get("weight_decay", 1e-3),
    )

    n_epochs  = cfg.get("epochs", 100)
    scheduler = CosineAnnealingLR(optimizer, T_max=n_epochs, eta_min=1e-6)
    scaler    = GradScaler()

    flood_weight   = cfg.get("flood_weight", 3.0)
    patience_max   = cfg.get("early_stopping_patience", 20)
    checkpoint_dir = Path(cfg.get("checkpoint_dir", "models/checkpoints"))
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    best_val_iou     = 0.0
    best_train_loss  = float("inf")
    patience_counter = 0
    history          = {"train_loss": [], "val_loss": [], "val_iou": []}

    # ── Epoch loop ────────────────────────────────────────────────────────────
    for epoch in range(1, n_epochs + 1):
        model.train()
        train_loss = 0.0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{n_epochs}", leave=False)
        for batch_idx, (imgs, lbls, valid) in enumerate(pbar):
            imgs  = imgs.to(device, non_blocking=True)
            lbls  = lbls.to(device, non_blocking=True)
            valid = valid.to(device, non_blocking=True)

            optimizer.zero_grad()

            with autocast():
                logits = model(imgs)
                loss   = focal_dice_loss(logits, lbls, valid, flood_weight)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item()
            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

            if batch_idx % 20 == 0:
                torch.cuda.empty_cache()

        train_loss /= len(train_loader)
        torch.cuda.empty_cache()

        val_loss, val_iou = validate(model, val_loader, device, flood_weight)
        scheduler.step()
        torch.cuda.empty_cache()

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss or 0.0)
        history["val_iou"].append(val_iou or 0.0)

        if val_loss is not None:
            print(f"Epoch {epoch:3d} | train={train_loss:.4f} | val={val_loss:.4f} | iou={val_iou:.4f} | lr={optimizer.param_groups[0]['lr']:.2e}")
        else:
            print(f"Epoch {epoch:3d} | train={train_loss:.4f} | val=N/A | lr={optimizer.param_groups[0]['lr']:.2e}")

        # ── Checkpoint (by val_iou if available, else train_loss) ─────────────
        improved = (val_iou is not None and val_iou > best_val_iou) if has_val \
                   else (train_loss < best_train_loss)

        if improved:
            best_val_iou    = val_iou or 0.0
            best_train_loss = train_loss
            patience_counter = 0
            ckpt_path = checkpoint_dir / "best_model.pth"
            torch.save({
                "epoch":                epoch,
                "model_state_dict":     model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss":             val_loss or 0.0,
                "val_iou":              val_iou or 0.0,
                "train_loss":           train_loss,
                "mean":                 mean.tolist(),
                "std":                  std.tolist(),
                "base_ch":              cfg.get("base_ch", 32),
                "in_channels":          cfg.get("in_channels", 2),
            }, ckpt_path)
            score = f"iou={val_iou:.4f}" if has_val else f"loss={train_loss:.4f}"
            print(f"  Saved best model ({score})")
        else:
            patience_counter += 1
            if patience_counter >= patience_max:
                print(f"Early stopping at epoch {epoch}.")
                break

    with open(checkpoint_dir / "history.json", "w") as f:
        json.dump(history, f, indent=2)

    print(f"\nTraining complete. Best val_iou={best_val_iou:.4f}")
    print(f"Checkpoint: {checkpoint_dir / 'best_model.pth'}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    train(cfg)
