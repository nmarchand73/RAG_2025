"""
Cross-Encoder Re-ranking pour améliorer la pertinence des résultats.
Utilise un modèle qui comprend mieux le français.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Re-ranking will be disabled.")
    logger.warning("Install with: pip install sentence-transformers")


class ReRanker:
    """Re-classe les documents récupérés avec un cross-encoder."""

    def __init__(self, model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"):
        """
        Initialise le re-ranker.

        Args:
            model_name: Modèle cross-encoder de HuggingFace

        Modèles recommandés pour le français:
        - "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1" (multilingue, bon équilibre)
        - "cross-encoder/ms-marco-MiniLM-L-6-v2" (rapide, multilingue)
        - "antoinelouis/crossencoder-camembert-base-mmarcoFR" (spécifique français)
        """
        if not RERANKER_AVAILABLE:
            self.model = None
            logger.error("ReRanker disabled - sentence-transformers not installed")
            return

        try:
            logger.info(f"Chargement du modèle cross-encoder: {model_name}")
            self.model = CrossEncoder(model_name)
            logger.info("✅ Cross-encoder chargé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du cross-encoder: {e}")
            self.model = None

    def rerank(self, query: str, documents: List[Dict], top_k: int = 20) -> List[Dict]:
        """
        Re-classe les documents avec le cross-encoder.

        Args:
            query: Question de l'utilisateur
            documents: Documents récupérés
            top_k: Nombre de résultats à retourner

        Returns:
            Documents re-classés avec 'rerank_score' ajouté
        """
        if not self.model or not documents:
            logger.warning("Re-ranking skipped (model not available or no documents)")
            return documents[:top_k]

        try:
            # Préparer les paires query-document
            pairs = [[query, doc['content'][:512]] for doc in documents]  # Limite à 512 chars pour la vitesse

            # Obtenir les scores du cross-encoder
            logger.info(f"Re-ranking {len(documents)} documents...")
            scores = self.model.predict(pairs)

            # Ajouter les scores aux documents
            for doc, score in zip(documents, scores):
                doc['rerank_score'] = float(score)

            # Trier par score de re-ranking
            documents.sort(key=lambda x: x['rerank_score'], reverse=True)

            # Log des meilleurs résultats
            logger.info("🎯 Top 3 après re-ranking:")
            for i, doc in enumerate(documents[:3], 1):
                file_name = doc.get('metadata', {}).get('file_name', 'Unknown')
                score = doc['rerank_score']
                preview = doc['content'][:80].replace('\n', ' ')
                logger.info(f"  {i}. Score: {score:.3f} | {file_name} | {preview}...")

            return documents[:top_k]

        except Exception as e:
            logger.error(f"Erreur lors du re-ranking: {e}")
            return documents[:top_k]  # Fallback: retourner les documents originaux
