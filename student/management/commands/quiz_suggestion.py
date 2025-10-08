"""
Django management command for quiz suggestion engine testing.

Usage:
    python manage.py quiz_suggestion test --user=student123
    python manage.py quiz_suggestion progress --user=student123
    python manage.py quiz_suggestion reset --user=student123
    python manage.py quiz_suggestion stats
    python manage.py quiz_suggestion demo
"""

from django.core.management.base import BaseCommand, CommandError
from student.quiz_suggestion import (
    reset_user_progress,
    KnowledgeGraph,
    UserProfile,
    load_quizzes_from_neo4j,
)
from student.quiz_suggestion.cli_helpers import (
    QuizSession,
    display_progress,
    display_quiz,
    get_user_answer,
    display_graph_stats,
)
import json
from pathlib import Path


class Command(BaseCommand):
    help = "Interactive quiz suggestion engine for testing and demonstration"

    def add_arguments(self, parser):
        # Subcommands
        parser.add_argument(
            "action",
            type=str,
            choices=["test", "progress", "reset", "stats", "demo"],
            help="Action to perform",
        )

        # Options
        parser.add_argument("--user", type=str, help="User ID for the session")

        parser.add_argument(
            "--quizzes",
            type=int,
            default=10,
            help="Number of quizzes in test session (default: 10)",
        )

        parser.add_argument(
            "--profile-path",
            type=str,
            default="data/profiles",
            help="Path to store user profiles (default: data/profiles)",
        )

    def handle(self, *args, **options):
        action = options["action"]

        if action == "test":
            self.run_test_session(options)
        elif action == "progress":
            self.show_progress(options)
        elif action == "reset":
            self.reset_progress(options)
        elif action == "stats":
            self.show_stats(options)
        elif action == "demo":
            self.run_demo(options)

    def run_test_session(self, options):
        """Run an interactive quiz session"""
        user_id = options.get("user")
        if not user_id:
            raise CommandError("--user is required for test sessions")

        num_quizzes = options["quizzes"]

        self.stdout.write(
            self.style.SUCCESS(f"\n🎓 Starting quiz session for {user_id}\n")
        )

        # Load or create user profile
        profile = self.load_profile(user_id, options["profile_path"])

        # Load knowledge graph
        self.stdout.write("Loading knowledge graph...")
        try:
            kg = KnowledgeGraph.from_neo4j()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Loaded {len(kg.nodes())} knowledge nodes\n")
            )
        except Exception as e:
            raise CommandError(f"Failed to load knowledge graph: {e}")

        # Load quiz bank
        self.stdout.write("Loading quiz bank...")
        try:
            quizzes = load_quizzes_from_neo4j()
            self.stdout.write(self.style.SUCCESS(f"✓ Loaded {len(quizzes)} quizzes\n"))
        except Exception as e:
            raise CommandError(f"Failed to load quizzes: {e}")

        if not quizzes:
            raise CommandError("No quizzes available in the database")

        # Run session
        session = QuizSession(profile, kg, quizzes)

        for i in range(num_quizzes):
            self.stdout.write(f"\n{'=' * 60}")
            self.stdout.write(f"Quiz {i + 1}/{num_quizzes}")
            self.stdout.write(f"{'=' * 60}\n")

            try:
                # Get suggestion
                quiz = session.get_next_quiz()

                # Display quiz
                display_quiz(quiz, self.stdout, self.style)

                # Get user answer
                is_correct = get_user_answer(quiz, self.stdout, self.style)

                # Update profile
                session.submit_answer(quiz, is_correct)

                # Show feedback
                if is_correct:
                    self.stdout.write(self.style.SUCCESS("\n✓ Correct!\n"))
                else:
                    self.stdout.write(self.style.ERROR("\n✗ Incorrect\n"))
                    if quiz.content.explanation:
                        self.stdout.write(f"Explanation: {quiz.content.explanation}\n")

            except KeyboardInterrupt:
                self.stdout.write(
                    self.style.WARNING("\n\nSession interrupted by user\n")
                )
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\nError: {e}\n"))
                break

        # Show final progress
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("Session Complete!")
        self.stdout.write(f"{'=' * 60}\n")

        display_progress(session.profile, kg, self.stdout, self.style)

        # Save profile
        self.save_profile(session.profile, options["profile_path"])
        self.stdout.write(self.style.SUCCESS(f"\n✓ Profile saved for {user_id}\n"))

    def show_progress(self, options):
        """Show learning progress for a user"""
        user_id = options.get("user")
        if not user_id:
            raise CommandError("--user is required")

        profile = self.load_profile(user_id, options["profile_path"])

        try:
            kg = KnowledgeGraph.from_neo4j()
        except Exception as e:
            raise CommandError(f"Failed to load knowledge graph: {e}")

        self.stdout.write(self.style.SUCCESS(f"\n📊 Progress for {user_id}\n"))
        display_progress(profile, kg, self.stdout, self.style)

    def reset_progress(self, options):
        """Reset user progress"""
        user_id = options.get("user")
        if not user_id:
            raise CommandError("--user is required")

        # Confirm
        confirm = input(f"Reset all progress for {user_id}? (yes/no): ")
        if confirm.lower() != "yes":
            self.stdout.write("Cancelled")
            return

        profile = reset_user_progress(user_id)
        self.save_profile(profile, options["profile_path"])

        self.stdout.write(self.style.SUCCESS(f"✓ Reset progress for {user_id}"))

    def show_stats(self, options):
        """Show knowledge graph statistics"""
        try:
            kg = KnowledgeGraph.from_neo4j()
            quizzes = load_quizzes_from_neo4j()
        except Exception as e:
            raise CommandError(f"Failed to load data: {e}")

        display_graph_stats(kg, quizzes, self.stdout, self.style)

    def run_demo(self, options):
        """Run a demo session with simulated answers"""
        self.stdout.write(self.style.SUCCESS("\n🎬 Running demo session...\n"))

        # Create demo user
        profile = reset_user_progress("demo_user")

        try:
            kg = KnowledgeGraph.from_neo4j()
            quizzes = load_quizzes_from_neo4j()
        except Exception as e:
            raise CommandError(f"Failed to load data: {e}")

        if not quizzes:
            raise CommandError("No quizzes available")

        session = QuizSession(profile, kg, quizzes)

        # Simulate 20 quizzes with 70% accuracy
        import random

        random.seed(42)

        for i in range(20):
            try:
                quiz = session.get_next_quiz()
                is_correct = random.random() < 0.7  # 70% correct
                session.submit_answer(quiz, is_correct)

                status = "✓" if is_correct else "✗"
                self.stdout.write(f"{status} Quiz {i + 1}: {quiz.content.stem[:50]}...")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {e}"))
                break

        self.stdout.write("\n")
        display_progress(session.profile, kg, self.stdout, self.style)

        # Optionally save demo profile
        save_demo = input("\nSave demo profile? (yes/no): ")
        if save_demo.lower() == "yes":
            self.save_profile(session.profile, options["profile_path"])
            self.stdout.write(self.style.SUCCESS("✓ Demo profile saved"))

    # Helper methods

    def load_profile(self, user_id: str, profile_path: str) -> UserProfile:
        """Load user profile from file or create new"""
        path = Path(profile_path) / f"{user_id}.json"

        if path.exists():
            try:
                return UserProfile.load_from_file(path)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Failed to load profile: {e}. Creating new.")
                )
                return UserProfile(user_id=user_id)
        else:
            return UserProfile(user_id=user_id)

    def save_profile(self, profile: UserProfile, profile_path: str):
        """Save user profile to file"""
        path = Path(profile_path)
        path.mkdir(parents=True, exist_ok=True)

        file_path = path / f"{profile.user_id}.json"
        profile.save_to_file(file_path)
