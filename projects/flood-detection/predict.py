"""
Usage:
    python predict.py --input data/chip.tif --checkpoint models/checkpoints/best_model.pth --output outputs/mask.tif
"""

import argparse
from pathlib import Path

import numpy as np
import rasterio
import torch

from models.unet import UNet


def load_model(checkpoint_path: str, device: torch.device) -> tuple:
    ckpt    = torch.load(checkpoint_path, map_location=device)
    mean    = np.array(ckpt["mean"], dtype=np.float32)
    std     = np.array(ckpt["std"],  dtype=np.float32)
    base_ch = ckpt.get("base_ch", 32)
    in_ch   = ckpt.get("in_channels", 2)
    model   = UNet(in_channels=in_ch, base_ch=base_ch).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model, mean, std


def preprocess_chip(tif_path: str, mean: np.ndarray, std: np.ndarray) -> tuple:

    with rasterio.open(tif_path) as src:
        img     = src.read().astype(np.float32)   # (2, H, W) already dB
        profile = src.profile.copy()

    # Valid = finite pixels (negative values are valid SAR dB returns)
    valid_mask = np.isfinite(img[0])

    # Replace NaN with 0 before normalisation
    img = np.where(np.isfinite(img), img, 0.0)

    # Normalise directly (no log conversion)
    img_norm = (img - mean[:, None, None]) / (std[:, None, None] + 1e-8)
    img_norm[:, ~valid_mask] = 0.0

    tensor = torch.from_numpy(img_norm).unsqueeze(0)   # (1, 2, H, W)
    return tensor, profile, valid_mask


def predict_flood_mask(
    tif_path: str,
    checkpoint_path: str,
    output_path: str,
    threshold: float = 0.5,
    device_str: str = "auto",
) -> np.ndarray:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu") \
             if device_str == "auto" else torch.device(device_str)

    model, mean, std = load_model(checkpoint_path, device)
    tensor, profile, valid_mask = preprocess_chip(tif_path, mean, std)
    tensor = tensor.to(device)

    with torch.no_grad():
        prob_map = torch.sigmoid(model(tensor)).squeeze().cpu().numpy()

    flood_mask = (prob_map >= threshold).astype(np.uint8)
    flood_mask[~valid_mask] = 0

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    profile.update(count=1, dtype="uint8", nodata=255)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(flood_mask, 1)

    print(f"Flood mask saved to: {output_path}")
    if valid_mask.any():
        print(f"Flood coverage: {flood_mask[valid_mask].mean() * 100:.1f}% of valid pixels")
    return flood_mask


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",      required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output",     required=True)
    parser.add_argument("--threshold",  type=float, default=0.5)
    parser.add_argument("--device",     default="auto")
    args = parser.parse_args()
    predict_flood_mask(
        tif_path=args.input, checkpoint_path=args.checkpoint,
        output_path=args.output, threshold=args.threshold, device_str=args.device,
    )
