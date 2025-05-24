import re
from collections import Counter, defaultdict
from typing import Dict, List, Set

import structlog
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

from src.models.scoring import ScoringResult
from src.models.report import TopicCluster

logger = structlog.get_logger()


class TopicClusterer:
    """Cluster documents by topic using text analysis."""

    def __init__(self, max_clusters: int = 10, min_cluster_size: int = 2):
        self.max_clusters = max_clusters
        self.min_cluster_size = min_cluster_size

    async def cluster_by_topic(self, scoring_results: List[ScoringResult]) -> List[TopicCluster]:
        """Cluster documents by identified topics."""
        try:
            logger.info("Starting topic clustering", document_count=len(scoring_results))

            if len(scoring_results) < 2:
                logger.info("Not enough documents for clustering")
                return self._create_single_cluster(scoring_results)

            # Extract text for clustering
            documents_text = []
            for result in scoring_results:
                # Combine evidence snippets and justifications
                text_parts = []

                # Add evidence from all dimensions
                for dim_score in result.dimension_scores.values():
                    text_parts.extend(dim_score.evidence_snippets)

                # Add overall justification
                text_parts.append(result.overall_justification)

                # Combine all text
                combined_text = " ".join(text_parts)
                documents_text.append(combined_text)

            # Perform clustering
            clusters = self._perform_text_clustering(documents_text, scoring_results)

            # Convert to TopicCluster objects
            topic_clusters = []
            for cluster_id, cluster_docs in clusters.items():
                if len(cluster_docs) >= self.min_cluster_size:
                    topic_cluster = await self._create_topic_cluster(cluster_id, cluster_docs)
                    topic_clusters.append(topic_cluster)

            # Sort clusters by average score (highest first)
            topic_clusters.sort(key=lambda x: x.average_score, reverse=True)

            logger.info(f"Created {len(topic_clusters)} topic clusters")
            return topic_clusters

        except Exception as e:
            logger.error("Topic clustering failed", error=str(e))
            # Fallback to single cluster
            return self._create_single_cluster(scoring_results)

    def _perform_text_clustering(
        self, documents_text: List[str], scoring_results: List[ScoringResult]
    ) -> Dict[int, List[ScoringResult]]:
        """Perform text-based clustering using TF-IDF and K-means."""
        try:
            # Determine optimal number of clusters
            n_clusters = min(self.max_clusters, max(2, len(documents_text) // 3))

            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(
                max_features=1000, stop_words="english", ngram_range=(1, 2), min_df=1, max_df=0.8
            )

            tfidf_matrix = vectorizer.fit_transform(documents_text)

            # Perform K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)

            # Group documents by cluster
            clusters = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                clusters[label].append(scoring_results[i])

            return dict(clusters)

        except Exception as e:
            logger.warning("TF-IDF clustering failed, using fallback", error=str(e))
            return self._fallback_clustering(scoring_results)

    def _fallback_clustering(
        self, scoring_results: List[ScoringResult]
    ) -> Dict[int, List[ScoringResult]]:
        """Fallback clustering based on scoring dimensions."""
        clusters = defaultdict(list)

        for result in scoring_results:
            # Find the highest scoring dimension
            highest_dim = max(result.dimension_scores.items(), key=lambda x: x[1].score)

            # Use dimension name as cluster key
            dim_name = highest_dim[0]
            cluster_key = hash(dim_name) % self.max_clusters
            clusters[cluster_key].append(result)

        return dict(clusters)

    async def _create_topic_cluster(
        self, cluster_id: int, cluster_docs: List[ScoringResult]
    ) -> TopicCluster:
        """Create a TopicCluster from grouped documents."""

        # Calculate average score
        average_score = sum(doc.master_score for doc in cluster_docs) / len(cluster_docs)

        # Identify topic name and description
        topic_name, topic_description = self._identify_topic(cluster_docs)

        # Extract key themes
        key_themes = self._extract_key_themes(cluster_docs)

        return TopicCluster(
            topic_name=topic_name,
            topic_description=topic_description,
            document_count=len(cluster_docs),
            average_score=round(average_score, 1),
            documents=cluster_docs,
            key_themes=key_themes,
        )

    def _identify_topic(self, cluster_docs: List[ScoringResult]) -> tuple[str, str]:
        """Identify topic name and description from cluster documents."""

        # Collect all evidence and justifications
        all_text = []
        dimension_strengths = Counter()

        for doc in cluster_docs:
            for dim_name, dim_score in doc.dimension_scores.items():
                if dim_score.score >= 50:  # Only consider significant dimensions
                    all_text.extend(dim_score.evidence_snippets)
                    dimension_strengths[dim_name] += dim_score.score

            all_text.append(doc.overall_justification)

        # Find the most prominent dimension
        if dimension_strengths:
            primary_dimension = dimension_strengths.most_common(1)[0][0]
            topic_name = primary_dimension.replace("_", " ").title()
        else:
            topic_name = f"Cluster {hash(str(cluster_docs)) % 1000}"

        # Extract key phrases for description
        combined_text = " ".join(all_text).lower()
        key_phrases = self._extract_key_phrases(combined_text)

        if key_phrases:
            topic_description = f"Documents focusing on {', '.join(key_phrases[:3])}"
        else:
            topic_description = f"Documents with similar {topic_name.lower()} patterns"

        return topic_name, topic_description

    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text."""
        # Simple phrase extraction based on common patterns
        phrases = []

        # Look for quoted phrases
        quoted = re.findall(r'"([^"]+)"', text)
        phrases.extend(quoted)

        # Look for regulatory terms
        regulatory_patterns = [
            r"\b(compliance|regulation|requirement|mandate|policy)\b",
            r"\b(gdpr|data protection|privacy)\b",
            r"\b(digital|technology|innovation)\b",
            r"\b(market|industry|business)\b",
        ]

        for pattern in regulatory_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            phrases.extend(matches)

        # Count frequency and return most common
        phrase_counts = Counter(phrases)
        return [phrase for phrase, _ in phrase_counts.most_common(10)]

    def _extract_key_themes(self, cluster_docs: List[ScoringResult]) -> List[str]:
        """Extract key themes from cluster documents."""
        themes = []

        # Collect dimension justifications
        for doc in cluster_docs:
            for dim_score in doc.dimension_scores.values():
                if dim_score.score >= 60:  # High relevance threshold
                    # Extract key terms from justification
                    justification = dim_score.justification.lower()

                    # Look for specific patterns
                    if "company mention" in justification:
                        themes.append("Direct company impact")
                    elif "regulatory" in justification:
                        themes.append("Regulatory compliance")
                    elif "industry" in justification:
                        themes.append("Industry relevance")
                    elif "market" in justification or "geographic" in justification:
                        themes.append("Geographic scope")
                    elif "urgent" in justification or "immediate" in justification:
                        themes.append("Time-sensitive")
                    elif "strategic" in justification:
                        themes.append("Strategic alignment")

        # Count and return most common themes
        theme_counts = Counter(themes)
        return [theme for theme, _ in theme_counts.most_common(5)]

    def _create_single_cluster(self, scoring_results: List[ScoringResult]) -> List[TopicCluster]:
        """Create a single cluster when clustering is not possible."""
        if not scoring_results:
            return []

        average_score = sum(doc.master_score for doc in scoring_results) / len(scoring_results)

        return [
            TopicCluster(
                topic_name="General Documents",
                topic_description="All analyzed documents grouped together",
                document_count=len(scoring_results),
                average_score=round(average_score, 1),
                documents=scoring_results,
                key_themes=["Mixed content"],
            )
        ]
