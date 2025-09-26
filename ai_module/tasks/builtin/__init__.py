from __future__ import annotations

from ...registry import register_task
from .nl2cypher import NL2CypherTask
from .summarize import SummarizeTask
from .classify import ClassifyTask
from .extract import ExtractTask

# Register builtin tasks on import
register_task(NL2CypherTask)
register_task(SummarizeTask)
register_task(ClassifyTask)
register_task(ExtractTask)

