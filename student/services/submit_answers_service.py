import logging
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone

from core.api import APIError
from core.services import BaseService, ServiceContext
from student.neo_models import Student as NeoStudent
from quiz.neo_models import Quiz as NeoQuiz, Choice as NeoChoice
from knowledge.neo_models import Knowledge as NeoKnowledge
from student.quiz_suggestion import (
    update_scores,
    load_quizzes_from_neo4j,
    KnowledgeGraph,
    UserProfile,
)
from student.quiz_suggestion.models.adapters import Quiz as PydanticQuiz

logger = logging.getLogger(__name__)


class SubmitAnswersService(BaseService[Dict[str, Any], Dict[str, Any]]):
    """
    Class-based service for submitting quiz answers and updating student progress.

    This service:
    - Validates answer submissions
    - Checks if answers are correct
    - Updates user profile scores using the quiz suggestion engine
    - Tracks knowledge graph adjustments
    - Saves updated profile
    """

    def run(self) -> Dict[str, Any]:
        data = self.inp or {}
        student_id = data.get("student_id", "")
        answers = data.get("answers", [])

        if not student_id:
            raise APIError(
                "student_id is required", code="invalid_input", status_code=400
            )

        if not answers:
            raise APIError(
                "At least one answer is required", code="invalid_input", status_code=400
            )

        logger.info(
            f"Processing {len(answers)} answer submissions for student {student_id}"
        )

        # Load or create student node
        student_node = self._get_student(student_id)

        # Load user profile
        profile = self._load_user_profile(student_id)

        # Load knowledge graph
        try:
            kg = KnowledgeGraph.from_neo4j()
            logger.info(f"Loaded knowledge graph with {len(kg.nodes())} nodes")
        except Exception as e:
            logger.error(f"Failed to load knowledge graph: {e}")
            raise APIError(
                "Failed to load knowledge graph",
                code="knowledge_graph_error",
                status_code=500,
                details={"error": str(e)},
            )

        # Track all knowledge adjustments
        all_adjustments: Dict[str, float] = {}

        # Process each answer
        for idx, answer_data in enumerate(answers):
            try:
                adjustments = self._process_answer(answer_data, profile, kg, student_id)

                # Accumulate adjustments
                for node_id, delta in adjustments.items():
                    all_adjustments[node_id] = all_adjustments.get(node_id, 0.0) + delta

            except Exception as e:
                logger.error(f"Failed to process answer {idx}: {e}")
                # Continue processing other answers
                continue

        # Save updated profile
        self._save_user_profile(profile, student_id)

        # Build response
        graph_updates = self._build_graph_updates(all_adjustments, kg)

        # Update Student-Knowledge relationships in Neo4j
        self._update_student_knowledge_links(student_node, all_adjustments, profile, kg)

        resp_student = {
            "name": student_node.username,
            "db_id": student_node.db_id,
        }

        logger.info(
            f"Completed answer submission for {student_id}. "
            f"Updated {len(graph_updates)} knowledge nodes."
        )

        return {"student": resp_student, "graph_update": graph_updates}

    def _get_student(self, student_id: str) -> NeoStudent | None:
        """Find student node in Neo4j."""
        try:
            qs = NeoStudent.nodes.filter(db_id=student_id)
            student_node = qs.first()
            return student_node
        except Exception as e:
            logger.warning(f"Failed to get student node: {e}")
            return None

    def _load_user_profile(self, student_id: str) -> UserProfile:
        """Load or create a UserProfile for the student."""
        profile_path = Path("data/profiles") / f"{student_id}.json"

        if profile_path.exists():
            try:
                profile = UserProfile.load_from_file(profile_path)
                logger.info(f"Loaded existing profile for {student_id}")
                return profile
            except Exception as e:
                logger.warning(
                    f"Failed to load profile for {student_id}: {e}. Creating new."
                )

        # Create new profile
        profile = UserProfile(user_id=student_id)
        logger.info(f"Created new profile for {student_id}")
        return profile

    def _save_user_profile(self, profile: UserProfile, student_id: str):
        """Save user profile to file."""
        profile_path = Path("data/profiles")
        profile_path.mkdir(parents=True, exist_ok=True)

        file_path = profile_path / f"{student_id}.json"
        profile.save_to_file(file_path)
        logger.info(f"Saved profile for {student_id}")

    def _process_answer(
        self,
        answer_data: Dict[str, Any],
        profile: UserProfile,
        kg: KnowledgeGraph,
        student_id: str,
    ) -> Dict[str, float]:
        """
        Process a single answer submission and return knowledge adjustments.

        Returns:
            Dict mapping knowledge node IDs to score adjustments
        """
        quiz_gid = answer_data.get("quiz_gid")
        answer_gid = answer_data.get("answer_gid")

        # Find the quiz in Neo4j
        neo_quiz = self._get_neo_quiz_by_id(quiz_gid)
        if neo_quiz is None:
            logger.warning(f"Quiz {quiz_gid} not found")
            return {}

        # Check if answer is correct
        is_correct = self._check_answer_correctness(neo_quiz, answer_gid)

        # Convert to Pydantic Quiz for the suggestion engine
        try:
            pydantic_quiz = PydanticQuiz.from_neo4j(neo_quiz)
        except Exception as e:
            logger.error(f"Failed to convert quiz {quiz_gid} to Pydantic: {e}")
            return {}

        # Store old scores to calculate adjustments
        old_scores = {
            node_id: profile.get_score(node_id)
            for node_id in pydantic_quiz.linked_nodes
        }

        # Update scores using the quiz suggestion engine
        try:
            profile = update_scores(profile, pydantic_quiz, is_correct, kg)
        except Exception as e:
            logger.error(f"Failed to update scores for quiz {quiz_gid}: {e}")
            return {}

        # Calculate adjustments
        adjustments = {}
        for node_id in pydantic_quiz.linked_nodes:
            new_score = profile.get_score(node_id)
            old_score = old_scores.get(node_id, 0.0)
            delta = new_score - old_score
            if delta != 0:
                adjustments[node_id] = delta

        logger.info(
            f"Processed answer for quiz {quiz_gid}: "
            f"correct={is_correct}, adjustments={len(adjustments)}"
        )

        return adjustments

    def _get_neo_quiz_by_id(self, quiz_id: str) -> NeoQuiz | None:
        """Get a Neo4j Quiz node by its element_id."""
        try:
            for quiz in NeoQuiz.nodes.all():
                if getattr(quiz, "element_id", None) == quiz_id:
                    return quiz
            return None
        except Exception as e:
            logger.error(f"Failed to fetch Neo4j quiz {quiz_id}: {e}")
            return None

    def _check_answer_correctness(self, neo_quiz: NeoQuiz, answer_gid: str) -> bool:
        """Check if the submitted answer is correct."""
        try:
            for choice in neo_quiz.has_choice.all():
                choice_id = getattr(choice, "element_id", None)
                if choice_id == answer_gid:
                    return bool(getattr(choice, "is_correct", False))

            # Answer not found in quiz choices
            logger.warning(f"Answer {answer_gid} not found in quiz choices")
            return False

        except Exception as e:
            logger.error(f"Failed to check answer correctness: {e}")
            return False

    def _build_graph_updates(
        self, adjustments: Dict[str, float], kg: KnowledgeGraph
    ) -> List[Dict[str, Any]]:
        """
        Build the graph_update response array.

        Args:
            adjustments: Dict mapping node IDs to score adjustments
            kg: Knowledge graph for looking up node names

        Returns:
            List of graph update objects
        """
        graph_updates = []

        for node_id, adjustment in adjustments.items():
            # Get knowledge node name from the graph
            node_data = kg.graph.nodes.get(node_id, {})
            knowledge_name = node_data.get("name", "Unknown")

            graph_updates.append(
                {
                    "graph_id": node_id,
                    "knowledge": knowledge_name,
                    "adjustment": round(adjustment, 2),
                }
            )

        # Sort by absolute adjustment (largest changes first)
        graph_updates.sort(key=lambda x: abs(x["adjustment"]), reverse=True)

        return graph_updates

    def _update_student_knowledge_links(
        self,
        student_node: NeoStudent,
        adjustments: Dict[str, float],
        profile: UserProfile,
        kg: KnowledgeGraph,
    ):
        """
        Update Student-Knowledge relationships in Neo4j based on quiz results.

        This method creates or updates relationships between the student and
        knowledge nodes, storing metadata about their learning progress.

        Args:
            student_node: Neo4j Student node
            adjustments: Dict mapping knowledge element_id to score adjustment
            profile: Student's UserProfile with current scores
            kg: KnowledgeGraph with knowledge nodes
        """
        if not adjustments:
            logger.info("No adjustments to update in graph")
            return

        updated_count = 0
        created_count = 0

        # Build knowledge nodes map for quick lookup
        knowledge_nodes_map = {}
        for k_node in NeoKnowledge.nodes.all():
            element_id = getattr(k_node, "element_id", None)
            if element_id:
                knowledge_nodes_map[element_id] = k_node

        logger.info(
            f"Updating Student-Knowledge links for {len(adjustments)} knowledge nodes"
        )

        for node_element_id, adjustment in adjustments.items():
            try:
                # Get knowledge node
                knowledge_node = knowledge_nodes_map.get(node_element_id)
                if not knowledge_node:
                    logger.warning(
                        f"Knowledge node {node_element_id} not found in Neo4j"
                    )
                    continue

                # Get current score from profile
                current_score = profile.get_score(node_element_id)

                # Check if relationship already exists
                if student_node.related_to.is_connected(knowledge_node):
                    # Update existing relationship
                    rel = student_node.related_to.relationship(knowledge_node)
                    rel.last_score = current_score + adjustment
                    rel.last_updated = datetime.now(timezone.utc)
                    rel.total_attempts = getattr(rel, "total_attempts", 0) + 1

                    # Increment total_correct if adjustment is positive (correct answer)
                    if adjustment > 0:
                        rel.total_correct = getattr(rel, "total_correct", 0) + 1

                    rel.save()
                    updated_count += 1

                    logger.debug(
                        f"Updated relationship: Student -> {knowledge_node.name}, "
                        f"score: {current_score}, attempts: {rel.total_attempts}"
                    )
                else:
                    # Create new relationship
                    rel_props = {
                        "last_score": current_score,
                        "last_updated": datetime.now(timezone.utc),
                        "total_attempts": 1,
                        "total_correct": adjustment,
                    }

                    student_node.related_to.connect(knowledge_node, rel_props)
                    created_count += 1

                    logger.debug(
                        f"Created relationship: Student -> {knowledge_node.name}, "
                        f"score: {current_score}"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to update Student-Knowledge link for {node_element_id}: {e}",
                    exc_info=True,
                )
                continue

        logger.info(
            f"Student-Knowledge links updated: {created_count} created, "
            f"{updated_count} updated"
        )
