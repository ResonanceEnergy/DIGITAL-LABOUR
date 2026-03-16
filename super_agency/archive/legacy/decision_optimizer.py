#!/usr/bin/env python3
"""
Advanced Decision Optimization Module
Provides machine learning tools to support and optimize executive decisions.
"""

import json
import logging
import random
from typing import List, Dict, Any, Optional

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

logger = logging.getLogger(__name__)


class DecisionOptimizer:
    """Wraps ML models to score and recommend actions"""

    def __init__(self):
        """Initialize."""
        # placeholder models - in real system these would be trained on historic data
        self.models: Dict[str, Any] = {
            'budget': make_pipeline(StandardScaler(), LogisticRegression()),
            'strategy': make_pipeline(StandardScaler(), RandomForestClassifier()),
        }
        self.trained = False

    def train(self, dataset: List[Dict[str, Any]], label_key: str) -> None:
        """Train optimizer on provided dataset"""
        if not dataset:
            logger.warning("No data provided for training")
            return

        # extract features and labels
        X = []
        y = []
        for row in dataset:
            features = [v for k, v in row.items() if k != label_key]
            X.append(features)
            y.append(row[label_key])

        model = self.models.get(label_key)
        if model is not None:
            try:
                model.fit(X, y)
                self.trained = True
                logger.info(f"DecisionOptimizer trained for {label_key}")
            except Exception as e:
                logger.error(f"Error training DecisionOptimizer: {e}")
        else:
            logger.warning(f"No model configured for label {label_key}")

    def score(self, input_features: Dict[str, Any], label_key: str) -> float:
        """Return a score/probability for the given input"""
        if not self.trained or label_key not in self.models:
            # fallback to random estimate
            return random.random()

        model = self.models[label_key]
        features = [v for k, v in input_features.items()]
        try:
            prob = model.predict_proba([features])[0][1]
            return float(prob)
        except Exception as e:
            logger.error(f"Error scoring decision: {e}")
            return random.random()

    def recommend(self, candidates: List[Dict[str, Any]], label_key: str, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Filter candidate actions by score threshold"""
        recommendations = []
        for candidate in candidates:
            score = self.score(candidate, label_key)
            if score >= threshold:
                candidate['score'] = score
                recommendations.append(candidate)
        # sort by descending score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations
