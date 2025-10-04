"""
Graph traversal utilities with caching.

This module provides cached Neo4j queries for efficient prerequisite
and dependent lookups. Uses LRU cache to avoid repeated database queries.
"""

from functools import lru_cache
from typing import Set, List
import logging
from student.quiz_suggestion.engine.policies import GRAPH_CACHE_SIZE

logger = logging.getLogger(__name__)


@lru_cache(maxsize=GRAPH_CACHE_SIZE)
def get_prerequisites_cached(node_id: str) -> Set[str]:
    """
    Get immediate prerequisites for a node (cached).

    This queries Neo4j directly for the DEPENDS_ON relationships.
    Results are cached to avoid repeated queries.

    Args:
        node_id: The knowledge node ID

    Returns:
        Set of prerequisite node IDs
    """
    from knowledge.neo_models import Knowledge as NeoKnowledge

    try:
        # Find the knowledge node
        knowledge = NeoKnowledge.nodes.get(name=node_id)

        # Get all nodes it depends on
        prereqs = set()
        for prereq in knowledge.depends_on.all():
            prereq_id = getattr(prereq, "element_id", None) or prereq.name
            prereqs.add(str(prereq_id))

        return prereqs

    except NeoKnowledge.DoesNotExist:
        logger.warning(f"Knowledge node {node_id!r} not found")
        return set()
    except Exception as e:
        logger.error(f"Error getting prerequisites for {node_id!r}: {e}")
        return set()


@lru_cache(maxsize=GRAPH_CACHE_SIZE)
def get_dependents_cached(node_id: str) -> Set[str]:
    """
    Get immediate dependents for a node (cached).

    This finds all nodes that depend on the given node.

    Args:
        node_id: The knowledge node ID

    Returns:
        Set of dependent node IDs
    """
    from knowledge.neo_models import Knowledge as NeoKnowledge

    try:
        # Find the knowledge node
        knowledge = NeoKnowledge.nodes.get(name=node_id)

        # Get all nodes that depend on this one (reverse relationship)
        dependents = set()

        # Query all knowledge nodes and check if they depend on this one
        for other in NeoKnowledge.nodes.all():
            for prereq in other.depends_on.all():
                prereq_id = getattr(prereq, "element_id", None) or prereq.name
                if str(prereq_id) == node_id:
                    other_id = getattr(other, "element_id", None) or other.name
                    dependents.add(str(other_id))
                    break

        return dependents

    except NeoKnowledge.DoesNotExist:
        logger.warning(f"Knowledge node {node_id!r} not found")
        return set()
    except Exception as e:
        logger.error(f"Error getting dependents for {node_id!r}: {e}")
        return set()


@lru_cache(maxsize=GRAPH_CACHE_SIZE)
def get_quizzes_for_node_cached(node_id: str) -> List[str]:
    """
    Get all quiz IDs related to a knowledge node (cached).

    Args:
        node_id: The knowledge node ID

    Returns:
        List of quiz IDs
    """
    from knowledge.neo_models import Knowledge as NeoKnowledge

    try:
        # Find the knowledge node
        knowledge = NeoKnowledge.nodes.get(name=node_id)

        # Get all related quizzes
        quiz_ids = []
        for quiz in knowledge.related_quizzes.all():
            quiz_id = getattr(quiz, "element_id", str(quiz))
            quiz_ids.append(str(quiz_id))

        return quiz_ids

    except NeoKnowledge.DoesNotExist:
        logger.warning(f"Knowledge node {node_id!r} not found")
        return []
    except Exception as e:
        logger.error(f"Error getting quizzes for {node_id!r}: {e}")
        return []


def clear_graph_cache():
    """Clear all cached graph queries"""
    get_prerequisites_cached.cache_clear()
    get_dependents_cached.cache_clear()
    get_quizzes_for_node_cached.cache_clear()
    logger.info("Graph cache cleared")


def get_cache_info() -> dict:
    """
    Get cache statistics for all cached functions.

    Returns:
        Dictionary with cache info for each function
    """
    return {
        "prerequisites": get_prerequisites_cached.cache_info()._asdict(),
        "dependents": get_dependents_cached.cache_info()._asdict(),
        "quizzes": get_quizzes_for_node_cached.cache_info()._asdict(),
    }
