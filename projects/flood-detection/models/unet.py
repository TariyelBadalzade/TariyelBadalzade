"""
models/unet.py
U-Net architecture for binary flood segmentation from 2-channel Sentinel-1 SAR input.

NOTE: forward() returns RAW LOGITS (no sigmoid).
      Apply sigmoid externally at inference time.
      This is required for BCEWithLogitsLoss + autocast (mixed precision) compatibility.
"""

import torch
import torch.nn as nn


class DoubleConv(nn.Module):
    """Two consecutive Conv2d → BatchNorm → ReLU blocks."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class EncoderBlock(nn.Module):
    """DoubleConv followed by MaxPool2d. Returns (pooled, skip)."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.conv = DoubleConv(in_ch, out_ch)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

    def forward(self, x: torch.Tensor):
        skip = self.conv(x)
        return self.pool(skip), skip


class DecoderBlock(nn.Module):
    """TransposedConv upsampling, skip-connection concat, then DoubleConv."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.up   = nn.ConvTranspose2d(in_ch, out_ch, kernel_size=2, stride=2)
        self.conv = DoubleConv(out_ch * 2, out_ch)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        if x.shape != skip.shape:
            x = nn.functional.interpolate(x, size=skip.shape[2:], mode="bilinear", align_corners=False)
        return self.conv(torch.cat([x, skip], dim=1))


class UNet(nn.Module):
    """
    U-Net for binary flood segmentation.

    Args:
        in_channels: Number of input channels (2 for VV + VH SAR).
        base_ch:     Number of feature channels in the first encoder block.
        dropout:     Dropout probability applied at the bottleneck.

    Returns raw logits — apply torch.sigmoid() externally at inference.
    """

    def __init__(self, in_channels: int = 2, base_ch: int = 64, dropout: float = 0.3):
        super().__init__()
        b = base_ch

        # Encoder
        self.enc1 = EncoderBlock(in_channels, b)
        self.enc2 = EncoderBlock(b,     b * 2)
        self.enc3 = EncoderBlock(b * 2, b * 4)
        self.enc4 = EncoderBlock(b * 4, b * 8)

        # Bottleneck
        self.bottleneck = nn.Sequential(
            DoubleConv(b * 8, b * 16),
            nn.Dropout2d(p=dropout),
        )

        # Decoder
        self.dec4 = DecoderBlock(b * 16, b * 8)
        self.dec3 = DecoderBlock(b * 8,  b * 4)
        self.dec2 = DecoderBlock(b * 4,  b * 2)
        self.dec1 = DecoderBlock(b * 2,  b)

        # Output: 1×1 conv — NO sigmoid here (applied externally)
        self.out_conv = nn.Conv2d(b, 1, kernel_size=1)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d)):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x, s1 = self.enc1(x)
        x, s2 = self.enc2(x)
        x, s3 = self.enc3(x)
        x, s4 = self.enc4(x)
        x = self.bottleneck(x)
        x = self.dec4(x, s4)
        x = self.dec3(x, s3)
        x = self.dec2(x, s2)
        x = self.dec1(x, s1)
        return self.out_conv(x)   # raw logits — NO sigmoid


if __name__ == "__main__":
    model = UNet(in_channels=2, base_ch=64)
    dummy = torch.randn(2, 2, 512, 512)
    out   = model(dummy)
    print(f"Input:  {dummy.shape}")
    print(f"Output: {out.shape}")
    print(f"Trainable parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")
