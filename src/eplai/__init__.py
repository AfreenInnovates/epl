"""Premier League player-intelligence toolkit.

The package is split into four layers:

``eplai.data``        loading and feature engineering for the raw season data
``eplai.models``      the PyTorch architectures used to learn player embeddings
``eplai.similarity``  embedding storage and consensus similarity search
``eplai.rag``         web retrieval, chunking and the vector index
``eplai.agent``       the tool-calling agent that answers user questions
"""

__version__ = "0.1.0"
