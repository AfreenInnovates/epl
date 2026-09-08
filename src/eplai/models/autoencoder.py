"""Autoencoder used to compress the per-90 feature space into a latent profile."""

from __future__ import annotations

import torch
from torch import nn


class PlayerAutoencoder(nn.Module):
    """Baseline autoencoder without regularisation."""

    def __init__(self, input_dim: int = 41, latent_dim: int = 8) -> None:
        super().__init__()

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, latent_dim),
        )

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, input_dim),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        latent = self.encoder(x)
        return self.decoder(latent), latent

    @torch.no_grad()
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)


class ImprovedPlayerAutoencoder(PlayerAutoencoder):
    """Autoencoder with dropout, which generalised better in notebook 03."""

    def __init__(self, input_dim: int = 41, latent_dim: int = 8, dropout: float = 0.15) -> None:
        super().__init__(input_dim, latent_dim)

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, latent_dim),
        )

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 16),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, input_dim),
        )
