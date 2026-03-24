"""
Semantic similarity calculation using embeddings.
"""

import numpy as np
from typing import List, Dict
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger
from evaluation.config import EMBEDDING_MODEL


class SimilarityCalculator:
    """Calculate semantic similarity between texts using embeddings."""
    
    def __init__(self, api_key: str):
        """
        Initialize the similarity calculator.
        
        Args:
            api_key: API key for the embedding service
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model = EMBEDDING_MODEL
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding vector for a text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)
        
        # Reshape for sklearn
        embedding1 = embedding1.reshape(1, -1)
        embedding2 = embedding2.reshape(1, -1)
        
        similarity = cosine_similarity(embedding1, embedding2)[0][0]
        return float(similarity)
    
    def calculate_category_similarities(
        self, 
        generated_categories: Dict[str, str],
        reference_categories: Dict[str, str]
    ) -> Dict[str, float]:
        """
        Calculate similarity for each category separately.
        
        Args:
            generated_categories: Generated coaching text by category
            reference_categories: Reference coaching text by category
            
        Returns:
            Dictionary mapping category names to similarity scores
        """
        similarities = {}
        
        for category in generated_categories.keys():
            gen_text = generated_categories.get(category, "")
            ref_text = reference_categories.get(category, "")
            
            if gen_text and ref_text:
                similarities[category] = self.calculate_similarity(gen_text, ref_text)
            else:
                similarities[category] = 0.0
        
        return similarities
    
    def calculate_batch_similarity(
        self, 
        texts1: List[str], 
        texts2: List[str]
    ) -> List[float]:
        """
        Calculate similarities for multiple text pairs.
        
        Args:
            texts1: List of first texts
            texts2: List of second texts
            
        Returns:
            List of similarity scores
        """
        if len(texts1) != len(texts2):
            raise ValueError("Text lists must have the same length")
        
        return [
            self.calculate_similarity(t1, t2) 
            for t1, t2 in zip(texts1, texts2)
        ]
