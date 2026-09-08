"""Retrain all three embedding models and regenerate ``artifacts/``.

Reproduces the artifacts shipped with the project. Needs the raw dataset, so
run ``scripts/download_data.py`` first.

    python scripts/train_embeddings.py --epochs 100
"""

from __future__ import annotations

import argparse
import sys

import joblib
import numpy as np

import _bootstrap  # noqa: F401

from eplai.config import ARTIFACT_DIR
from eplai.data import (
    build_feature_matrix,
    build_model_frame,
    drop_correlated_features,
    load_raw,
    write_player_knowledge,
)
from eplai.models.training import (
    TrainingConfig,
    encode_all,
    get_device,
    set_seed,
    train_autoencoder,
    train_siamese,
    train_triplet,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.20)
    args = parser.parse_args()

    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    set_seed(args.seed)
    device = get_device()
    print(f"Device: {device}")

    # ------------------------------------------------------------------
    # data
    # ------------------------------------------------------------------

    df_model = build_model_frame(load_raw())
    print(f"Players in modelling population: {len(df_model)}")

    X = build_feature_matrix(df_model)
    X_reduced, dropped = drop_correlated_features(X, threshold=0.90)
    print(f"Dropped {len(dropped)} correlated features, {X_reduced.shape[1]} remain")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_reduced)

    positions = df_model["Position"]

    train_idx, _ = train_test_split(
        np.arange(len(X_scaled)),
        test_size=args.test_size,
        random_state=args.seed,
        stratify=positions,
    )

    X_train = X_scaled[train_idx]
    y_train = positions.iloc[train_idx].to_numpy()

    config = TrainingConfig(epochs=args.epochs)

    # ------------------------------------------------------------------
    # training
    # ------------------------------------------------------------------

    print("\nTraining autoencoder ...")
    autoencoder = train_autoencoder(X_train, config, device)

    print("\nTraining triplet model ...")
    triplet = train_triplet(X_train, y_train, config, device)

    print("\nTraining Siamese model ...")
    siamese = train_siamese(X_train, y_train, config, device)

    # ------------------------------------------------------------------
    # embeddings for the full population
    # ------------------------------------------------------------------

    standard_embeddings = X_scaled
    autoencoder_embeddings = encode_all(autoencoder.encoder, X_scaled, device)
    triplet_embeddings = encode_all(triplet, X_scaled, device)
    siamese_embeddings = encode_all(siamese.embedding_network, X_scaled, device)

    print(
        "\nEmbedding shapes -- "
        f"standard {standard_embeddings.shape}, "
        f"autoencoder {autoencoder_embeddings.shape}, "
        f"siamese {siamese_embeddings.shape}, "
        f"triplet {triplet_embeddings.shape}"
    )

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    import torch

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    torch.save(autoencoder.state_dict(), ARTIFACT_DIR / "autoencoder_model.pt")
    torch.save(triplet.state_dict(), ARTIFACT_DIR / "triplet_model.pt")
    torch.save(siamese.state_dict(), ARTIFACT_DIR / "siamese_model.pt")

    joblib.dump(scaler, ARTIFACT_DIR / "feature_scaler.joblib")
    joblib.dump(dropped, ARTIFACT_DIR / "dropped_features.joblib")
    joblib.dump(X_reduced.columns.tolist(), ARTIFACT_DIR / "model_features.joblib")

    np.save(ARTIFACT_DIR / "standard_embeddings.npy", standard_embeddings)
    np.save(ARTIFACT_DIR / "autoencoder_embeddings.npy", autoencoder_embeddings)
    np.save(ARTIFACT_DIR / "siamese_embeddings.npy", siamese_embeddings)
    np.save(ARTIFACT_DIR / "triplet_embeddings.npy", triplet_embeddings)

    df_model[["Player Name", "Club", "Position"]].to_csv(
        ARTIFACT_DIR / "player_metadata.csv", index=False
    )

    write_player_knowledge(df_model)

    print(f"\nArtifacts written to {ARTIFACT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
