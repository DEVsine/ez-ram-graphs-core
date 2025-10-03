from __future__ import annotations

from ...registry import register_task
from .nl2cypher import NL2CypherTask
from .summarize import SummarizeTask
from .classify import ClassifyTask
from .extract import ExtractTask
from .map_question_knowledge import MapQuestionKnowledgeTask
from .batch_map_questions_knowledge import BatchMapQuestionsKnowledgeTask

# Register builtin tasks on import
register_task(NL2CypherTask)
register_task(SummarizeTask)
register_task(ClassifyTask)
register_task(ExtractTask)
register_task(MapQuestionKnowledgeTask)
register_task(BatchMapQuestionsKnowledgeTask)
