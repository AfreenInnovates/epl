"""Metric-learning networks: Siamese (contrastive) and triplet embeddings."""

from __future__ import annotations

import torch
from torch import nn


class EmbeddingNetwork(nn.Module):
    """Shared encoder used by both the Siamese and triplet models."""

    def __init__(self, input_dim: int = 41, embedding_dim: int = 8) -> None:
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class BetterEmbeddingNetwork(nn.Module):
    """Wider encoder whose output is L2-normalised, so cosine == dot product."""

    def __init__(self, input_dim: int = 41, embedding_dim: int = 16) -> None:
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return nn.functional.normalize(self.network(x), p=2, dim=1)


class SiameseNetwork(nn.Module):
    """Twin-tower wrapper that embeds a pair of players with shared weights."""

    def __init__(
        self,
        input_dim: int = 41,
        embedding_dim: int = 16,
        encoder: type[nn.Module] = BetterEmbeddingNetwork,
    ) -> None:
        super().__init__()

        self.embedding_network = encoder(input_dim, embedding_dim)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        return self.embedding_network(x1), self.embedding_network(x2)

    @torch.no_grad()
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.embedding_network(x)


class ContrastiveLoss(nn.Module):
    """Pulls similar pairs together and pushes dissimilar pairs past ``margin``."""

    def __init__(self, margin: float = 1.0) -> None:
        super().__init__()
        self.margin = margin

    def forward(self, z1: torch.Tensor, z2: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        distance = nn.functional.pairwise_distance(z1, z2)

        positive = target * distance.pow(2)
        negative = (1 - target) * torch.clamp(self.margin - distance, min=0).pow(2)

        return torch.mean(positive + negative)
