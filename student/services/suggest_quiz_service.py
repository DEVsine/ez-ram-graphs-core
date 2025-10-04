import logging
from pathlib import Path
from typing import Any, Dict, List

from core.api import APIError
from core.services import BaseService, ServiceContext
from student.neo_models import Student as NeoStudent
from quiz.neo_models import Quiz as NeoQuiz
from student.quiz_suggestion import (
    suggest_next_quiz,
    load_quizzes_from_neo4j,
    KnowledgeGraph,
    UserProfile,
)
from student.quiz_suggestion.exceptions import NoQuizAvailableError

logger = logging.getLogger(__name__)


class SuggestQuizService(BaseService[Dict[str, Any], Dict[str, Any]]):
    """
    Class-based service for suggesting quizzes using the quiz suggestion engine.

    This service:
    - Loads or creates a UserProfile for the student
    - Uses the KnowledgeGraph and quiz suggestion engine for intelligent recommendations
    - Returns quizzes in the expected API format
    """

    def run(self) -> Dict[str, Any]:
        data = self.inp or {}
        student_inp = data.get("student") or {}
        quiz_limit = int(data.get("quiz_limit", 10) or 10)
        scope_topic = data.get("scope_topic")
        replay = data.get("replay", False)

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

        # Load or create UserProfile for the suggestion engine
        profile = self._load_user_profile(username)

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

        # Load quiz bank
        try:
            quizzes = load_quizzes_from_neo4j()
            logger.info(f"Loaded {len(quizzes)} quizzes from Neo4j")
        except Exception as e:
            logger.error(f"Failed to load quizzes: {e}")
            raise APIError(
                "Failed to load quizzes",
                code="quiz_load_error",
                status_code=500,
                details={"error": str(e)},
            )

        if not quizzes:
            raise APIError(
                "No quizzes available in the database",
                code="no_quizzes",
                status_code=404,
            )

        # Filter by scope_topic if provided
        if scope_topic:
            quizzes = self._filter_by_topic(quizzes, scope_topic, kg)
            logger.info(f"Filtered to {len(quizzes)} quizzes for topic '{scope_topic}'")

        # Get quiz suggestions using the suggestion engine
        suggested_quizzes = []
        seen_quiz_ids = set()

        for _ in range(quiz_limit):
            try:
                # Get next suggestion
                quiz = suggest_next_quiz(profile, kg, quizzes)

                # Avoid duplicates unless replay is enabled
                if not replay and quiz.id in seen_quiz_ids:
                    # Try to find a different quiz by temporarily removing this one
                    remaining_quizzes = [
                        q for q in quizzes if q.id not in seen_quiz_ids
                    ]
                    if remaining_quizzes:
                        quiz = suggest_next_quiz(profile, kg, remaining_quizzes)

                suggested_quizzes.append(quiz)
                seen_quiz_ids.add(quiz.id)

            except NoQuizAvailableError:
                logger.warning(
                    f"No more quizzes available after {len(suggested_quizzes)} suggestions"
                )
                break

        # Convert Pydantic Quiz models to API response format
        quizzes_out = self._convert_quizzes_to_response(suggested_quizzes)

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
        except NeoStudent.DoesNotExist as e:
            student_node = None

        # Create if not found
        if student_node is None and db_id:
            student_node = NeoStudent(username=username, db_id=db_id).save()
            logger.info(f"Created new student node for {username}")

        return student_node

    def _load_user_profile(self, username: str) -> UserProfile:
        """Load or create a UserProfile for the student."""
        profile_path = Path("data/profiles") / f"{username}.json"

        if profile_path.exists():
            try:
                profile = UserProfile.load_from_file(profile_path)
                logger.info(f"Loaded existing profile for {username}")
                return profile
            except Exception as e:
                logger.warning(
                    f"Failed to load profile for {username}: {e}. Creating new."
                )

        # Create new profile
        profile = UserProfile(user_id=username)
        logger.info(f"Created new profile for {username}")
        return profile

    def _filter_by_topic(self, quizzes: list, topic: str, kg: KnowledgeGraph) -> list:
        """Filter quizzes by topic (knowledge node name)."""
        # Find knowledge nodes matching the topic
        matching_node_ids = set()
        for node_id in kg.nodes():
            node_data = kg.graph.nodes.get(node_id, {})
            node_name = node_data.get("name", "")
            if topic.lower() in node_name.lower():
                matching_node_ids.add(node_id)

        if not matching_node_ids:
            logger.warning(f"No knowledge nodes found matching topic '{topic}'")
            return quizzes

        # Filter quizzes that link to these nodes
        filtered = [
            q
            for q in quizzes
            if any(node_id in matching_node_ids for node_id in q.linked_nodes)
        ]

        return filtered if filtered else quizzes

    def _convert_quizzes_to_response(
        self, pydantic_quizzes: list
    ) -> List[Dict[str, Any]]:
        """
        Convert Pydantic Quiz models to API response format.

        This fetches the original Neo4j Quiz objects to get full choice details.
        """
        quizzes_out = []

        for pydantic_quiz in pydantic_quizzes:
            try:
                # Fetch the original Neo4j quiz to get full details
                neo_quiz = self._get_neo_quiz_by_id(pydantic_quiz.id)

                if neo_quiz is None:
                    logger.warning(
                        f"Could not find Neo4j quiz for ID {pydantic_quiz.id}"
                    )
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
                    logger.warning(
                        f"Failed to load choices for quiz {pydantic_quiz.id}: {e}"
                    )
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
                        f"Failed to load related knowledge for quiz {pydantic_quiz.id}: {e}"
                    )
                    rel_k_q = []

                quizzes_out.append(
                    {
                        "graph_id": pydantic_quiz.id,
                        "quiz_text": pydantic_quiz.content.stem,
                        "choices": choices_data,
                        "related_to": rel_k_q,
                    }
                )

            except Exception as e:
                logger.error(f"Failed to convert quiz {pydantic_quiz.id}: {e}")
                continue

        return quizzes_out

    def _get_neo_quiz_by_id(self, quiz_id: str) -> NeoQuiz | None:
        """Get a Neo4j Quiz node by its element_id."""
        try:
            # Try to find by element_id
            for quiz in NeoQuiz.nodes.all():
                if getattr(quiz, "element_id", None) == quiz_id:
                    return quiz
            return None
        except Exception as e:
            logger.error(f"Failed to fetch Neo4j quiz {quiz_id}: {e}")
            return None
