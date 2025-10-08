import logging
import random
from typing import Any, Dict, List, Optional, Set

from neomodel import db

from core.api import APIError
from core.services import BaseService
from student.neo_models import Student as NeoStudent
from quiz.neo_models import Quiz as NeoQuiz
from knowledge.neo_models import Knowledge as NeoKnowledge

logger = logging.getLogger(__name__)


class SuggestQuizService(BaseService[Dict[str, Any], Dict[str, Any]]):
    """
    Class-based service for suggesting quizzes based on student weakness knowledge.

    This service implements the following logic:
    1. Get student from Neo4j
    2. Query lowest student.related_to.last_score (StudentKnowledgeRel) to get weakness knowledge
    3. Query related knowledge quizzes but not duplicate with the last 5 quiz history
    4. Loop this process until quiz_limit is reached, scoped by scope_topic if provided
    5. If student has no knowledge links (new user), return random quizzes

    Quiz history is tracked in Neo4j Student-[ATTEMPTED]->Quiz relationships (last 15 quizzes).
    """

    def run(self) -> Dict[str, Any]:
        data = self.inp or {}
        student_inp = data.get("student") or {}
        quiz_limit = int(data.get("quiz_limit", 10) or 10)
        scope_topic = data.get("scope_topic")

        username = (student_inp or {}).get("username") or ""
        db_id = (student_inp or {}).get("id") or (student_inp or {}).get("db_id") or ""

        if not username:
            raise APIError(
                "student.username is required", code="invalid_input", status_code=400
            )

        if quiz_limit < 1:
            raise APIError(
                "quiz_limit must be >= 1", code="invalid_input", status_code=400
            )

        logger.info(f"Suggesting {quiz_limit} quizzes for student {username}")

        # Find/create Student node in Neo4j
        student_node = self._get_or_create_student(username, db_id)
        if not student_node:
            raise APIError(
                "Failed to create or find student node",
                code="student_error",
                status_code=500,
            )

        # Get last 5 quiz IDs from Neo4j quiz history for deduplication
        recent_quiz_ids = self._get_recent_quiz_ids(student_node, n=5)

        # Check if student has knowledge relationships
        has_knowledge = self._has_knowledge_relationships(student_node)

        suggested_quiz_nodes = []

        if has_knowledge:
            # Existing user: suggest based on weakness knowledge
            logger.info(
                f"Student {username} has knowledge relationships, using weakness-based suggestion"
            )

            # Get weakness knowledge nodes ordered by last_score (lowest first)
            weakness_knowledge_nodes = self._get_weakness_knowledge_nodes(
                student_node, scope_topic
            )

            # Collect quizzes from weakness knowledge until quiz_limit is reached
            for knowledge_node in weakness_knowledge_nodes:
                if len(suggested_quiz_nodes) >= quiz_limit:
                    break

                # Get quizzes related to this knowledge node
                related_quizzes = self._get_quizzes_for_knowledge(knowledge_node)

                # Filter out quizzes from recent history
                for quiz_node in related_quizzes:
                    if len(suggested_quiz_nodes) >= quiz_limit:
                        break

                    quiz_id = getattr(quiz_node, "element_id", None)
                    if quiz_id and quiz_id not in recent_quiz_ids:
                        # Avoid duplicates in current suggestion
                        if quiz_id not in [
                            getattr(q, "element_id", None) for q in suggested_quiz_nodes
                        ]:
                            suggested_quiz_nodes.append(quiz_node)
                            logger.debug(
                                f"Added quiz {quiz_id} from knowledge {knowledge_node.name}"
                            )

            logger.info(
                f"Collected {len(suggested_quiz_nodes)} quizzes from {len(weakness_knowledge_nodes)} weakness knowledge nodes"
            )
        else:
            # New user: suggest random quizzes
            logger.info(
                f"Student {username} has no knowledge relationships, using random suggestion"
            )
            suggested_quiz_nodes = self._get_random_quizzes(
                scope_topic, quiz_limit, recent_quiz_ids
            )

        # Convert Neo4j Quiz nodes to API response format
        quizzes_out = self._convert_quizzes_to_response(suggested_quiz_nodes)

        # Build student response
        resp_student = {
            "name": student_node.username,
            "db_id": student_node.db_id,
        }

        logger.info(f"Returning {len(quizzes_out)} quiz suggestions for {username}")

        return {"student": resp_student, "quiz": quizzes_out}

    def _get_or_create_student(self, username: str, db_id: str) -> NeoStudent | None:
        """Find or create a Student node in Neo4j."""
        if not username:
            return None

        # Try to find existing student
        if db_id:
            qs = NeoStudent.nodes.filter(username=username, db_id=db_id)
        else:
            qs = NeoStudent.nodes.filter(username=username)

        try:
            student_node = qs.first()
        except NeoStudent.DoesNotExist:
            student_node = None

        # Create if not found
        if student_node is None and db_id:
            student_node = NeoStudent(username=username, db_id=db_id).save()
            logger.info(f"Created new student node for {username}")

        return student_node

    def _has_knowledge_relationships(self, student_node: NeoStudent) -> bool:
        """
        Check if student has any knowledge relationships.

        Args:
            student_node: Neo4j Student node

        Returns:
            True if student has at least one RELATED_TO relationship
        """
        try:
            # Check if there's at least one relationship
            return student_node.related_to.all()[:1].count() > 0
        except Exception as e:
            logger.error(f"Failed to check knowledge relationships: {e}")
            return False

    def _get_weakness_knowledge_nodes(
        self, student_node: NeoStudent, scope_topic: Optional[str] = None
    ) -> List[NeoKnowledge]:
        """
        Get knowledge nodes ordered by last_score (lowest first) for weakness-based suggestion.

        Args:
            student_node: Neo4j Student node
            scope_topic: Optional topic filter (knowledge name contains this string)

        Returns:
            List of Knowledge nodes ordered by last_score ascending (weakest first)
        """
        try:
            # Build Cypher query to get knowledge nodes ordered by last_score
            query = """
            MATCH (s:Student)-[r:RELATED_TO]->(k:Knowledge)
            WHERE elementId(s) = $student_id
            """

            params = {"student_id": student_node.element_id}

            # Add topic filter if provided
            if scope_topic:
                query += " AND toLower(k.name) CONTAINS toLower($topic)"
                params["topic"] = scope_topic

            query += """
            RETURN k, r.last_score as score
            ORDER BY r.last_score ASC
            """

            results, _ = db.cypher_query(query, params)

            knowledge_nodes = []
            for row in results:
                # row[0] is the Knowledge node
                knowledge_node = NeoKnowledge.inflate(row[0])
                knowledge_nodes.append(knowledge_node)

            logger.info(
                f"Found {len(knowledge_nodes)} weakness knowledge nodes"
                + (f" for topic '{scope_topic}'" if scope_topic else "")
            )

            return knowledge_nodes

        except Exception as e:
            logger.error(f"Failed to get weakness knowledge nodes: {e}", exc_info=True)
            return []

    def _get_quizzes_for_knowledge(self, knowledge_node: NeoKnowledge) -> List[NeoQuiz]:
        """
        Get all quizzes related to a knowledge node.

        Args:
            knowledge_node: Neo4j Knowledge node

        Returns:
            List of Quiz nodes related to this knowledge
        """
        try:
            # Get quizzes that have RELATED_TO relationship with this knowledge
            quizzes = list(knowledge_node.related_quizzes.all())
            logger.debug(
                f"Found {len(quizzes)} quizzes for knowledge '{knowledge_node.name}'"
            )
            return quizzes
        except Exception as e:
            logger.error(
                f"Failed to get quizzes for knowledge {knowledge_node.name}: {e}"
            )
            return []

    def _get_recent_quiz_ids(self, student_node: NeoStudent, n: int = 5) -> Set[str]:
        """
        Get the last N quiz IDs from student's quiz attempt history in Neo4j.

        Args:
            student_node: Student node from Neo4j
            n: Number of recent quizzes to retrieve (default: 5)

        Returns:
            Set of quiz element IDs from recent attempts
        """
        try:
            # Query last N quizzes attempted by student, ordered by attempted_at DESC
            query = """
            MATCH (s:Student)-[r:ATTEMPTED]->(q:Quiz)
            WHERE elementId(s) = $student_id
            RETURN q, r.attempted_at as attempted_at
            ORDER BY r.attempted_at DESC
            LIMIT $limit
            """
            params = {"student_id": student_node.element_id, "limit": n}

            results, _ = db.cypher_query(query, params)

            quiz_ids = set()
            for row in results:
                quiz_node = NeoQuiz.inflate(row[0])
                if quiz_node and hasattr(quiz_node, "element_id"):
                    quiz_ids.add(quiz_node.element_id)

            logger.info(f"Found {len(quiz_ids)} recent quiz IDs for deduplication")
            return quiz_ids
        except Exception as e:
            logger.error(
                f"Failed to get recent quiz IDs from Neo4j: {e}", exc_info=True
            )
            return set()

    def _get_random_quizzes(
        self, scope_topic: Optional[str], limit: int, exclude_quiz_ids: Set[str]
    ) -> List[NeoQuiz]:
        """
        Get random quizzes for new users, optionally filtered by topic.

        Args:
            scope_topic: Optional topic filter (knowledge name contains this string)
            limit: Maximum number of quizzes to return
            exclude_quiz_ids: Set of quiz IDs to exclude (from recent history)

        Returns:
            List of random Quiz nodes
        """
        try:
            if scope_topic:
                # Get quizzes related to knowledge nodes matching the topic
                query = """
                MATCH (q:Quiz)-[:RELATED_TO]->(k:Knowledge)
                WHERE toLower(k.name) CONTAINS toLower($topic)
                RETURN DISTINCT q
                """
                params = {"topic": scope_topic}
                results, _ = db.cypher_query(query, params)

                all_quizzes = []
                for row in results:
                    quiz_node = NeoQuiz.inflate(row[0])
                    quiz_id = getattr(quiz_node, "element_id", None)
                    if quiz_id and quiz_id not in exclude_quiz_ids:
                        all_quizzes.append(quiz_node)

                logger.info(
                    f"Found {len(all_quizzes)} quizzes for topic '{scope_topic}' (excluding recent)"
                )
            else:
                # Get all quizzes
                all_quizzes = []
                for quiz in NeoQuiz.nodes.all():
                    quiz_id = getattr(quiz, "element_id", None)
                    if quiz_id and quiz_id not in exclude_quiz_ids:
                        all_quizzes.append(quiz)

                logger.info(
                    f"Found {len(all_quizzes)} total quizzes (excluding recent)"
                )

            # Randomly select up to limit quizzes
            if len(all_quizzes) <= limit:
                return all_quizzes
            else:
                return random.sample(all_quizzes, limit)

        except Exception as e:
            logger.error(f"Failed to get random quizzes: {e}", exc_info=True)
            return []

    def _convert_quizzes_to_response(
        self, neo_quizzes: List[NeoQuiz]
    ) -> List[Dict[str, Any]]:
        """
        Convert Neo4j Quiz nodes to API response format.

        Args:
            neo_quizzes: List of Neo4j Quiz nodes

        Returns:
            List of quiz dictionaries in API response format
        """
        quizzes_out = []

        for neo_quiz in neo_quizzes:
            try:
                quiz_id = getattr(neo_quiz, "element_id", None)
                if not quiz_id:
                    logger.warning("Quiz has no element_id, skipping")
                    continue

                # Build choices data
                choices_data = []
                try:
                    for choice in neo_quiz.has_choice.all():
                        # Get related knowledge for this choice
                        rel_k = [
                            {
                                "graph_id": getattr(k, "element_id", str(k)),
                                "knowledge": getattr(k, "name", ""),
                            }
                            for k in choice.related_to.all()
                        ]

                        choices_data.append(
                            {
                                "graph_id": getattr(choice, "element_id", str(choice)),
                                "choice_text": getattr(choice, "choice_text", ""),
                                "is_correct": bool(
                                    getattr(choice, "is_correct", False)
                                ),
                                "answer_explanation": getattr(
                                    choice, "answer_explanation", ""
                                )
                                or "",
                                "related_to": rel_k,
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to load choices for quiz {quiz_id}: {e}")
                    choices_data = []

                # Get quiz-level related knowledge
                try:
                    rel_k_q = [
                        {
                            "graph_id": getattr(k, "element_id", str(k)),
                            "knowledge": getattr(k, "name", ""),
                        }
                        for k in neo_quiz.related_to.all()
                    ]
                except Exception as e:
                    logger.warning(
                        f"Failed to load related knowledge for quiz {quiz_id}: {e}"
                    )
                    rel_k_q = []

                quizzes_out.append(
                    {
                        "graph_id": quiz_id,
                        "quiz_text": getattr(neo_quiz, "quiz_text", ""),
                        "choices": choices_data,
                        "related_to": rel_k_q,
                    }
                )

            except Exception as e:
                logger.error(f"Failed to convert quiz: {e}")
                continue

        return quizzes_out
