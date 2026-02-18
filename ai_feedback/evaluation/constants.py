"""
Constants for the evaluation pipeline.
"""

# Similarity scoring
SIMILARITY_THRESHOLD = 0.75  # Minimum similarity score to pass (0.0 to 1.0)

# Embedding model
EMBEDDING_MODEL = "models/gemini-embedding-001"  # Only available embedding model

# Langfuse experiment configuration
LANGFUSE_EXPERIMENT_PREFIX = "eval"

# Similarity score interpretation
SIMILARITY_EXCELLENT = 0.90  # 0.90-1.00: Excellent - Nearly identical meaning
SIMILARITY_GOOD = 0.75       # 0.75-0.89: Good - Similar meaning with minor variations
SIMILARITY_FAIR = 0.60       # 0.60-0.74: Fair - Related but noticeable differences
# 0.00-0.59: Poor - Significantly different meaning
