import logging
from typing import Any, Dict, List, Set

from neomodel import db

from core.api import APIError
from core.services import BaseService
from student.neo_models import Student as NeoStudent
from knowledge.neo_models import Knowledge as NeoKnowledge, TopicKnowledge

logger = logging.getLogger(__name__)


class GetStudentGraphService(BaseService[Dict[str, Any], Dict[str, Any]]):
    """
    Class-based service for retrieving a student's knowledge graph with scores from Neo4j.

    This service:
    - Finds the student by db_id
    - Gets student's knowledge scores from Neo4j Student-Knowledge relationships
    - Builds a hierarchical tree structure (Topic -> Knowledge) with scores
    - Returns student info and knowledge graph with scores
    """

    def run(self) -> Dict[str, Any]:
        data = self.inp or {}
        student_id = data.get("student_id", "")

        if not student_id:
            raise APIError(
                "student_gid is required", code="invalid_input", status_code=400
            )

        logger.info(f"Fetching knowledge graph for student {student_id}")

        # Find student by db_id
        student_node = self._get_student_by_db_id(student_id)
        if not student_node:
            raise APIError(
                f"Student with graph_id {student_id} not found",
                code="student_not_found",
                status_code=404,
            )

        student_username = getattr(student_node, "username", "unknown")

        # Get ram_id from context
        ram_id = self.ctx.ram_id if self.ctx else None
        if not ram_id:
            raise APIError("ram_id is required", code="invalid_input", status_code=400)

        # Load student's knowledge scores from Neo4j relationships
        student_scores = self._get_student_knowledge_scores(student_node)

        # Build hierarchical knowledge graph with scores (Topic -> Knowledge tree)
        knowledge_tree = self._build_topic_knowledge_tree(ram_id, student_scores)

        # Build response
        resp_student = {
            "name": student_username,
            "db_id": str(getattr(student_node, "db_id", student_id)),
        }

        logger.info(
            f"Retrieved knowledge graph for {student_username} with {len(knowledge_tree)} topics"
        )

        return {
            "student": resp_student,
            "student_knowledge_graph": knowledge_tree,
        }

    def _get_student_by_db_id(self, db_id: str) -> NeoStudent | None:
        """Find student node by db ID (db_id)."""
        try:
            qs = NeoStudent.nodes.filter(db_id=db_id)
            student_node = qs.first()
            return student_node
        except Exception as e:
            logger.error(f"Failed to fetch student by db_id {db_id}: {e}")
            return None

    def _get_student_knowledge_scores(
        self, student_node: NeoStudent
    ) -> Dict[str, float]:
        """
        Get student's knowledge scores from Neo4j Student-Knowledge relationships.

        Args:
            student_node: Student node from Neo4j

        Returns:
            Dictionary mapping knowledge element_id to last_score
        """
        try:
            # Query all Student-[RELATED_TO]->Knowledge relationships with scores
            query = """
            MATCH (s:Student)-[r:RELATED_TO]->(k:Knowledge)
            WHERE elementId(s) = $student_id
            RETURN elementId(k) as knowledge_id, r.last_score as score
            """
            params = {"student_id": student_node.element_id}

            results, _ = db.cypher_query(query, params)

            scores = {}
            for row in results:
                knowledge_id = row[0]
                score = row[1] if row[1] is not None else 0.0
                scores[knowledge_id] = float(score)

            logger.info(
                f"Loaded {len(scores)} knowledge scores for student {student_node.username}"
            )
            return scores
        except Exception as e:
            logger.error(f"Failed to get student knowledge scores: {e}", exc_info=True)
            return {}

    def _build_topic_knowledge_tree(
        self, ram_id: str, student_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Build a hierarchical tree starting from Subject (ram_id) -> Topics -> Knowledge nodes.

        The tree structure:
        - Find the root TopicKnowledge node by ram_id (name)
        - Get all child Topics (via has_subtopic)
        - For each Topic, get Knowledge nodes (via has_knowledge)
        - Build nested Knowledge tree using depends_on relationships
        - Calculate average score for each Topic from all descendant Knowledge scores

        Args:
            ram_id: The root TopicKnowledge node name (e.g., "RAM1111")
            student_scores: Dictionary mapping knowledge element_id to last_score

        Returns:
            List of Topic nodes with nested Knowledge children
        """
        # Find the root TopicKnowledge node by name
        try:
            root_topic = TopicKnowledge.nodes.filter(name=ram_id).first()
            if not root_topic:
                logger.warning(f"Root TopicKnowledge node '{ram_id}' not found")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch root TopicKnowledge '{ram_id}': {e}")
            return []

        # Get all child Topics (via has_subtopic)
        try:
            child_topics = root_topic.has_subtopic.all()
            logger.info(f"Found {len(child_topics)} child topics for {ram_id}")
        except Exception as e:
            logger.error(f"Failed to fetch child topics for {ram_id}: {e}")
            return []

        # Build tree for each Topic
        topic_tree = []
        for topic in child_topics:
            topic_data = self._build_topic_node(topic, student_scores)
            if topic_data:
                topic_tree.append(topic_data)

        return topic_tree

    def _build_topic_node(
        self,
        topic: TopicKnowledge,
        student_scores: Dict[str, float],
        visited_topics: Set[str] = None,
    ) -> Dict[str, Any] | None:
        """
        Build a single Topic node with its nested Topic and Knowledge children.

        Args:
            topic: TopicKnowledge node
            student_scores: Dictionary mapping knowledge element_id to last_score
            visited_topics: Set of visited topic IDs to prevent cycles

        Returns:
            Topic node data with nested Topic/Knowledge children and average score
        """
        try:
            if visited_topics is None:
                visited_topics = set()

            topic_id = getattr(topic, "element_id", None) or topic.name
            topic_id_str = str(topic_id)
            topic_name = topic.name

            # Prevent infinite loops for Topics
            if topic_id_str in visited_topics:
                logger.warning(
                    f"Topic '{topic_name}' already visited, skipping to prevent cycle"
                )
                return None

            visited_topics.add(topic_id_str)

            # Collect all scores from descendants for average calculation
            all_scores = []
            children = []

            # 1. Get nested TopicKnowledge nodes (via has_subtopic)
            try:
                subtopics = topic.has_subtopic.all()
                logger.info(f"Topic '{topic_name}' has {len(subtopics)} subtopics")

                for subtopic in subtopics:
                    subtopic_data = self._build_topic_node(
                        subtopic, student_scores, visited_topics
                    )
                    if subtopic_data:
                        children.append(subtopic_data)
                        # Collect scores from subtopic and its descendants
                        self._collect_scores_from_node(subtopic_data, all_scores)
            except Exception as e:
                logger.warning(f"Failed to get subtopics for '{topic_name}': {e}")

            # 2. Get Knowledge nodes for this Topic (via has_knowledge)
            try:
                knowledge_nodes = topic.has_knowledge.all()
                logger.info(
                    f"Topic '{topic_name}' has {len(knowledge_nodes)} knowledge nodes"
                )

                # Build nested Knowledge tree for each Knowledge node
                visited_knowledge: Set[str] = set()

                for knowledge in knowledge_nodes:
                    knowledge_data = self._build_knowledge_node_tree(
                        knowledge, student_scores, visited_knowledge, all_scores
                    )
                    if knowledge_data:
                        children.append(knowledge_data)
            except Exception as e:
                logger.warning(f"Failed to get knowledge nodes for '{topic_name}': {e}")

            # Calculate average score for this Topic from all descendants
            avg_score = (
                round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0
            )

            # Build Topic node data
            topic_data = {
                "graph_id": topic_id_str,
                "topic": topic_name,
                "score": avg_score,
            }

            if children:
                topic_data["child"] = children

            return topic_data

        except Exception as e:
            logger.error(f"Failed to build topic node for {topic}: {e}")
            return None

    def _collect_scores_from_node(
        self, node_data: Dict[str, Any], all_scores: List[float]
    ) -> None:
        """
        Recursively collect all scores from a node and its descendants.

        Args:
            node_data: Node data dictionary
            all_scores: List to append scores to
        """
        # Add this node's score if it exists
        if "score" in node_data:
            all_scores.append(node_data["score"])

        # Recursively collect from children
        if "child" in node_data:
            for child in node_data["child"]:
                self._collect_scores_from_node(child, all_scores)

    def _build_knowledge_node_tree(
        self,
        knowledge: NeoKnowledge,
        student_scores: Dict[str, float],
        visited: Set[str],
        all_scores: List[float],
    ) -> Dict[str, Any] | None:
        """
        Recursively build a Knowledge node tree with nested children.

        Args:
            knowledge: Knowledge node
            student_scores: Dictionary mapping knowledge element_id to last_score
            visited: Set of visited node IDs to prevent cycles
            all_scores: List to collect all scores for average calculation

        Returns:
            Knowledge node data with nested children
        """
        try:
            # Get node ID
            node_id = getattr(knowledge, "element_id", None) or knowledge.name
            node_id = str(node_id)

            # Prevent infinite loops
            # if node_id in visited:
            #     return None

            visited.add(node_id)

            # Get score from student_scores dictionary (default to 0.0 if not found)
            score = student_scores.get(node_id, 0.0)
            all_scores.append(score)  # Add to scores list for average calculation

            # Build node data
            node_data = {
                "graph_id": node_id,
                "knowledge": knowledge.name,
                "score": round(score, 2),
            }

            # Get children (nodes that depend on this node via DEPENDS_ON)
            children = []
            try:
                # Use Cypher query to find nodes that depend on this one
                query = """
                MATCH (dependent:Knowledge)-[:DEPENDS_ON]->(current:Knowledge)
                WHERE elementId(current) = $node_id OR current.name = $node_name
                RETURN dependent
                """
                results, _ = db.cypher_query(
                    query, {"node_id": node_id, "node_name": knowledge.name}
                )

                for row in results:
                    if row and row[0]:
                        # Inflate the node to a NeoKnowledge instance
                        dependent_node = NeoKnowledge.inflate(row[0])
                        dependent_id = (
                            getattr(dependent_node, "element_id", None)
                            or dependent_node.name
                        )
                        dependent_id = str(dependent_id)

                        if dependent_id:
                            child_data = self._build_knowledge_node_tree(
                                dependent_node, student_scores, visited, all_scores
                            )
                            if child_data:
                                children.append(child_data)

            except Exception as e:
                logger.warning(f"Failed to get dependents for {node_id}: {e}")

            if children:
                node_data["child"] = children

            return node_data

        except Exception as e:
            logger.error(f"Failed to build knowledge node tree for {knowledge}: {e}")
            return None
