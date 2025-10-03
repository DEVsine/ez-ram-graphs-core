"""
Django management command for creating question graphs in Neo4j.

This command processes quiz questions from a JSON file, uses AI to map them
to knowledge nodes, and creates the corresponding graph structure in Neo4j.

Usage:
    python manage.py create_question_graph --file questions.json
    python manage.py create_question_graph --from-predictions predictions.json --yes
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from django.core.management.base import BaseCommand, CommandError

from quiz.services.question_knowledge_mapping_service import (
    QuestionKnowledgeMappingService,
)
from quiz.services.batch_question_mapping_service import BatchQuestionMappingService
from quiz.services.neo4j_quiz_service import Neo4jQuizService


class Command(BaseCommand):
    """
    Create question graphs in Neo4j from an input file.

    Process:
    1. Fetch knowledge nodes from Neo4j
    2. For each question, use AI to map it to knowledge nodes
    3. Save all mappings to JSON for review
    4. On confirmation, write question graphs to Neo4j
    """

    help = (
        "Create question graphs in Neo4j from an input file. "
        "Process: fetch knowledge nodes, loop AI mapping per question, "
        "dump all mappings to JSON for review, then on confirmation write to Neo4j."
    )

    def add_arguments(self, parser):
        """Define command-line arguments."""
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Path to JSON file containing questions with {question: str, choices: [str, ...]}",
        )
        parser.add_argument(
            "--labels",
            type=str,
            nargs="*",
            default=["Knowledge"],
            help="Knowledge labels to include when fetching nodes (default: Knowledge)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=400,
            help="Limit number of knowledge nodes fetched for AI context (default: 400)",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Where to save the aggregated mapping JSON (default: predictions/<input-name>_mappings.json)",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation and write all question graphs to Neo4j immediately",
        )
        parser.add_argument(
            "--from-predictions",
            type=str,
            default=None,
            help="Path to aggregated predictions JSON (skip AI mapping and write to Neo4j)",
        )
        parser.add_argument(
            "--ai-provider",
            type=str,
            default=None,
            help="AI provider to use (e.g., 'openai', 'gemini')",
        )
        parser.add_argument(
            "--ai-model",
            type=str,
            default=None,
            help="AI model to use (e.g., 'gpt-4o-mini')",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Process questions in batches (parallel). 0=sequential (default), >0=batch size",
        )
        parser.add_argument(
            "--parallelism",
            type=int,
            default=10,
            help="Number of parallel AI requests when using batch mode (default: 5)",
        )
        parser.add_argument(
            "--rps",
            type=float,
            default=2.0,
            help="Requests per second limit for AI provider (default: 2.0)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Fast path: apply from an existing predictions file (skip AI)
        if options["from_predictions"]:
            self._handle_from_predictions(options)
            return

        # Normal path: generate new mappings using AI
        self._handle_generate_mappings(options)

    def _handle_from_predictions(self, options: Dict[str, Any]) -> None:
        """Handle the --from-predictions path."""
        pred_path = Path(options["from_predictions"])

        if not pred_path.exists():
            raise CommandError(f"Predictions file not found: {pred_path}")

        # Load predictions
        with open(pred_path, "r", encoding="utf-8") as f:
            aggregated: List[Dict[str, Any]] = json.load(f)

        if not isinstance(aggregated, list) or not aggregated:
            raise CommandError("Predictions must be a non-empty JSON list.")

        self.stdout.write(
            f"Loaded {len(aggregated)} mappings from predictions: {pred_path}"
        )

        # Confirm before writing
        proceed = options["yes"]
        if not proceed:
            ans = (
                input(
                    "Proceed to create ALL question graphs in Neo4j from predictions? [y/N]: "
                )
                .strip()
                .lower()
            )
            proceed = ans in ("y", "yes")

        if not proceed:
            self.stdout.write(
                self.style.WARNING(
                    "Aborted. Re-run with --yes to apply the predictions."
                )
            )
            return

        # Write to Neo4j
        created = self._write_to_neo4j(aggregated)

        self.stdout.write(self.style.SUCCESS("\nWrite complete from predictions."))
        self.stdout.write(
            json.dumps(
                {"created": created, "total": len(aggregated)},
                ensure_ascii=False,
                indent=2,
            )
        )

    def _handle_generate_mappings(self, options: Dict[str, Any]) -> None:
        """Handle the normal path: generate new mappings using AI."""
        input_path = Path(options["file"])

        if not input_path.exists():
            raise CommandError(f"Input file not found: {input_path}")

        # Load questions
        with open(input_path, "r", encoding="utf-8") as f:
            items: List[Dict[str, Any]] = json.load(f)
            if not isinstance(items, list):
                items = items.get("quizzes", [])

        if not isinstance(items, list) or not items:
            raise CommandError("Input must be a non-empty JSON list of items.")

        # Prepare output path
        if options["out"]:
            out_path = Path(options["out"])
        else:
            out_dir = Path("predictions")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{input_path.stem}_mappings.json"

        # Fetch knowledge nodes once (shared across all questions)
        self.stdout.write("Fetching knowledge nodes from Neo4j...")
        service = QuestionKnowledgeMappingService(
            inp={
                "question": "dummy",  # Will be replaced
                "choices": ["dummy"],
                "knowledge_labels": options["labels"],
                "knowledge_limit": options["limit"],
            }
        )
        knowledge_nodes = service._fetch_knowledge_nodes(
            labels=options["labels"], limit=options["limit"]
        )
        self.stdout.write(f"Fetched {len(knowledge_nodes)} knowledge nodes.")

        # Build mappings for all items
        aggregated: List[Dict[str, Any]] = []

        self.stdout.write(f"Loaded {len(items)} items from {input_path}.")

        self.stdout.write(
            f"Using batch processing (batch_size={options.get('batch_size', 10)}, "
            f"parallelism={options.get('parallelism', 10)}, "
            f"rps={options.get('rps', 2.0)}, "
            f"knowledge_nodes={len(knowledge_nodes)})"
        )
        aggregated = self._process_batch(items, knowledge_nodes, options)

        # Dump all predictions for review
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(aggregated, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS("\nPredictions written for review:"))
        self.stdout.write(f"  {out_path}")

        # Confirm before writing
        proceed = options["yes"]
        if not proceed:
            ans = (
                input("Proceed to create ALL question graphs in Neo4j? [y/N]: ")
                .strip()
                .lower()
            )
            proceed = ans in ("y", "yes")

        if not proceed:
            self.stdout.write(
                self.style.WARNING(
                    "Aborted. You can edit the JSON and re-run with --yes to apply."
                )
            )
            return

        # Write all to Neo4j
        created = self._write_to_neo4j(aggregated)

        self.stdout.write(self.style.SUCCESS("\nWrite complete."))
        self.stdout.write(
            json.dumps(
                {"created": created, "total": len(aggregated)},
                ensure_ascii=False,
                indent=2,
            )
        )

    def _process_batch(
        self,
        items: List[Dict[str, Any]],
        knowledge_nodes: List[Dict[str, Any]],
        options: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Process questions in batches (parallel processing)."""
        batch_size = options.get("batch_size", 10)
        parallelism = options.get("parallelism", 5)
        rps = options.get("rps", 2.0)

        all_results: List[Dict[str, Any]] = []

        # Process in batches
        for batch_start in range(0, len(items), batch_size):
            batch_end = min(batch_start + batch_size, len(items))
            batch_items = items[batch_start:batch_end]

            self.stdout.write(
                f"Processing batch {batch_start // batch_size + 1} "
                f"(questions {batch_start + 1}-{batch_end})..."
            )

            # Prepare batch input
            questions_data = []
            for item in batch_items:
                question = (item or {}).get("question")
                choices = (item or {}).get("choices") or []

                if not question or not isinstance(choices, list) or len(choices) < 2:
                    continue

                questions_data.append(
                    {
                        "question": question,
                        "choices": choices,
                    }
                )

            # Use batch service
            try:
                batch_input = {
                    "questions": questions_data,
                    "knowledge_nodes": knowledge_nodes,
                    "ai_provider": options.get("ai_provider"),
                    "ai_model": options.get("ai_model"),
                    "parallelism": parallelism,
                    "rps": rps,
                }

                batch_results = BatchQuestionMappingService.execute(batch_input)
                all_results.extend(batch_results)

                self.stdout.write(
                    f"  ✓ Completed {len(batch_results)}/{len(questions_data)} questions"
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Batch failed: {e}"))

        return all_results

    def _write_to_neo4j(self, mappings: List[Dict[str, Any]]) -> int:
        """Write all mappings to Neo4j."""
        created = 0

        for idx, m in enumerate(mappings, start=1):
            question_text = m.get("question", "")
            choices_payload = m.get("choices", [])
            qids = [int(x) for x in (m.get("question_knowledge_ids") or [])]

            if not question_text or not choices_payload:
                self.stdout.write(
                    self.style.WARNING(f"[{idx}] Skipping incomplete mapping: {m}")
                )
                continue

            Neo4jQuizService.create_question_graph(
                question_text=question_text,
                choices=choices_payload,
                question_knowledge_ids=qids,
            )
            created += 1

        return created
