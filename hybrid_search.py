"""
Recherche hybride: combine recherche sémantique + recherche par mots-clés
Pour améliorer la pertinence des résultats
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def hybrid_search(
    vector_store,
    query: str,
    top_k: int = 20,
    keyword_boost: float = 0.3
) -> List[Dict]:
    """
    Recherche hybride combinant:
    1. Recherche sémantique (embeddings)
    2. Recherche par mots-clés (texte)

    Args:
        vector_store: Instance VectorStore
        query: Question de l'utilisateur
        top_k: Nombre de résultats
        keyword_boost: Poids pour la recherche mots-clés (0-1)

    Returns:
        Liste de documents triés par score combiné
    """
    # S'assurer que top_k est un entier
    top_k = int(top_k) if top_k else 20

    # 1. Recherche sémantique (embeddings)
    logger.info("Recherche sémantique...")
    semantic_results = vector_store.similarity_search(query, top_k=int(top_k * 2))

    # 2. Extraire les mots-clés de la requête
    keywords = extract_keywords(query)
    logger.info(f"Mots-clés extraits: {keywords}")

    # 3. Scorer les résultats avec boost mots-clés
    scored_results = []
    for doc in semantic_results:
        semantic_score = doc.get('similarity', 0.5)
        keyword_score = calculate_keyword_score(doc['content'], keywords)

        # Score hybride
        combined_score = (
            (1 - keyword_boost) * semantic_score +
            keyword_boost * keyword_score
        )

        doc['hybrid_score'] = combined_score
        doc['keyword_score'] = keyword_score
        scored_results.append(doc)

    # 4. Trier par score hybride
    scored_results.sort(key=lambda x: x['hybrid_score'], reverse=True)

    # Logging pour debug
    logger.info(f"Top 3 résultats:")
    for i, doc in enumerate(scored_results[:3], 1):
        logger.info(f"  {i}. Score: {doc['hybrid_score']:.3f} (sem={doc.get('similarity', 0):.3f}, kw={doc['keyword_score']:.3f})")

    return scored_results[:top_k]


def extract_keywords(query: str) -> List[str]:
    """Extrait les mots-clés importants d'une requête"""
    # Mots vides français à ignorer
    stopwords = {
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'à', 'au', 'aux',
        'et', 'ou', 'mais', 'donc', 'car', 'ni', 'que', 'qui', 'quoi', 'dont',
        'ce', 'cet', 'cette', 'ces', 'mon', 'ton', 'son', 'ma', 'ta', 'sa',
        'mes', 'tes', 'ses', 'notre', 'votre', 'leur', 'nos', 'vos', 'leurs',
        'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles',
        'est', 'sont', 'suis', 'sommes', 'êtes', 'être', 'avoir', 'a', 'as',
        'qu', 'c', 'd', 'l', 's', 'n', 'm', 't', 'y',
        'que', 'quoi', 'quel', 'quelle', 'quels', 'quelles',
        'sur', 'sous', 'dans', 'par', 'pour', 'avec', 'sans'
    }

    # Tokenize et nettoie
    words = query.lower().replace('?', '').replace('!', '').split()
    keywords = [w.strip() for w in words if w.strip() and w.strip() not in stopwords and len(w) > 2]

    return keywords


def calculate_keyword_score(text: str, keywords: List[str]) -> float:
    """Calcule le score de présence des mots-clés dans le texte"""
    if not keywords:
        return 0.0

    text_lower = text.lower()

    # Compte les occurrences de chaque mot-clé
    total_matches = 0
    for keyword in keywords:
        # Compte exact + partial matches
        count = text_lower.count(keyword.lower())
        total_matches += count

    # Normalise par le nombre de mots-clés
    score = min(total_matches / len(keywords), 1.0)

    return score
