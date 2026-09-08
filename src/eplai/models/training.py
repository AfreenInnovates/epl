"""Dataset builders and training loops for the three embedding models.

This is the code path that regenerates everything in ``artifacts/``. It mirrors
notebook 03; the notebook stays the place to explore, this stays the place to
reproduce.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from .autoencoder import ImprovedPlayerAutoencoder
from .metric import BetterEmbeddingNetwork, EmbeddingNetwork, SiameseNetwork


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


# ----------------------------------------------------------------------
# datasets
# ----------------------------------------------------------------------


class TripletDataset(Dataset):
    """Samples (anchor, positive, negative) triplets by position label."""

    def __init__(self, X: np.ndarray, y: np.ndarray, triplets_per_epoch: int = 5000) -> None:
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = np.asarray(y)
        self.triplets_per_epoch = triplets_per_epoch

        self.class_indices = {
            label: np.where(self.y == label)[0] for label in np.unique(self.y)
        }
        self.labels = list(self.class_indices.keys())

    def __len__(self) -> int:
        return self.triplets_per_epoch

    def __getitem__(self, idx: int):
        label = random.choice(self.labels)

        anchor, positive = np.random.choice(
            self.class_indices[label], size=2, replace=False
        )

        negative_label = random.choice([x for x in self.labels if x != label])
        negative = random.choice(self.class_indices[negative_label])

        return self.X[anchor], self.X[positive], self.X[negative]


class HardPairDataset(Dataset):
    """Fixed list of mined (i, j, label) pairs."""

    def __init__(self, X: np.ndarray, pairs: list[tuple[int, int, float]]) -> None:
        self.X = torch.tensor(X, dtype=torch.float32)
        self.pairs = pairs

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int):
        i, j, label = self.pairs[idx]
        return self.X[i], self.X[j], torch.tensor(label, dtype=torch.float32)


def mine_hard_pairs(
    X: np.ndarray,
    y: np.ndarray,
    seed: int = 42,
) -> list[tuple[int, int, float]]:
    """Mine same-position pairs that are hard rather than obvious.

    Positives are drawn from the closest quarter of same-position players and
    negatives from the furthest quarter, so the model has to learn playing
    style rather than simply separating goalkeepers from forwards.
    """
    from sklearn.metrics import pairwise_distances

    distances = pairwise_distances(X)
    rng = np.random.default_rng(seed)

    pairs: list[tuple[int, int, float]] = []

    for i in range(len(X)):
        same_position = np.where(y == y[i])[0]
        same_position = same_position[same_position != i]

        if same_position.size == 0:
            continue

        sorted_same = same_position[np.argsort(distances[i, same_position])]
        quarter = max(1, len(sorted_same) // 4)

        pairs.append((i, int(rng.choice(sorted_same[:quarter])), 1.0))
        pairs.append((i, int(rng.choice(sorted_same[-quarter:])), 0.0))

    return pairs


# ----------------------------------------------------------------------
# training loops
# ----------------------------------------------------------------------


@dataclass
class TrainingConfig:
    epochs: int = 100
    batch_size: int = 64
    autoencoder_lr: float = 1e-3
    triplet_lr: float = 1e-3
    siamese_lr: float = 5e-4
    latent_dim: int = 8
    triplet_dim: int = 8
    siamese_dim: int = 16
    log_every: int = 10


def train_autoencoder(
    X_train: np.ndarray,
    config: TrainingConfig,
    device: torch.device,
) -> ImprovedPlayerAutoencoder:
    model = ImprovedPlayerAutoencoder(
        input_dim=X_train.shape[1], latent_dim=config.latent_dim
    ).to(device)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.autoencoder_lr)

    tensor = torch.tensor(X_train, dtype=torch.float32).to(device)
    loader = DataLoader(tensor, batch_size=config.batch_size, shuffle=True)

    for epoch in range(config.epochs):
        model.train()
        epoch_loss = 0.0

        for batch in loader:
            optimizer.zero_grad()

            reconstruction, _ = model(batch)
            loss = criterion(reconstruction, batch)

            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

        if (epoch + 1) % config.log_every == 0:
            print(f"  autoencoder epoch {epoch + 1:3d} | loss {epoch_loss / len(loader):.4f}")

    return model


def train_triplet(
    X_train: np.ndarray,
    y_train: np.ndarray,
    config: TrainingConfig,
    device: torch.device,
) -> EmbeddingNetwork:
    dataset = TripletDataset(X_train, y_train)
    loader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True)

    model = EmbeddingNetwork(
        input_dim=X_train.shape[1], embedding_dim=config.triplet_dim
    ).to(device)

    criterion = nn.TripletMarginLoss(margin=1.0, p=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.triplet_lr, weight_decay=1e-5)

    for epoch in range(config.epochs):
        model.train()
        epoch_loss = 0.0

        for anchor, positive, negative in loader:
            anchor, positive, negative = (
                anchor.to(device),
                positive.to(device),
                negative.to(device),
            )

            optimizer.zero_grad()

            loss = criterion(model(anchor), model(positive), model(negative))

            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

        if (epoch + 1) % config.log_every == 0:
            print(f"  triplet epoch {epoch + 1:3d} | loss {epoch_loss / len(loader):.4f}")

    return model


def train_siamese(
    X_train: np.ndarray,
    y_train: np.ndarray,
    config: TrainingConfig,
    device: torch.device,
) -> SiameseNetwork:
    pairs = mine_hard_pairs(X_train, y_train)
    print(f"  mined {len(pairs)} hard pairs")

    loader = DataLoader(
        HardPairDataset(X_train, pairs), batch_size=config.batch_size, shuffle=True
    )

    model = SiameseNetwork(
        input_dim=X_train.shape[1],
        embedding_dim=config.siamese_dim,
        encoder=BetterEmbeddingNetwork,
    ).to(device)

    criterion = nn.CosineEmbeddingLoss(margin=0.2)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.siamese_lr, weight_decay=1e-4)

    for epoch in range(config.epochs):
        model.train()
        epoch_loss = 0.0

        for x1, x2, target in loader:
            x1, x2 = x1.to(device), x2.to(device)

            # CosineEmbeddingLoss expects targets in {-1, 1}.
            target = target.to(device) * 2 - 1

            optimizer.zero_grad()

            z1, z2 = model(x1, x2)
            loss = criterion(z1, z2, target)

            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

        if (epoch + 1) % config.log_every == 0:
            print(f"  siamese epoch {epoch + 1:3d} | loss {epoch_loss / len(loader):.4f}")

    return model


# ----------------------------------------------------------------------
# inference
# ----------------------------------------------------------------------


@torch.no_grad()
def encode_all(module: nn.Module, X: np.ndarray, device: torch.device) -> np.ndarray:
    """Embed the full player population with a trained encoder."""
    module.eval()
    tensor = torch.tensor(X, dtype=torch.float32).to(device)
    return module(tensor).cpu().numpy()
