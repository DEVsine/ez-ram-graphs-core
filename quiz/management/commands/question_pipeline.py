from django.core.management.base import BaseCommand, CommandError
from quiz.services.pipeline_orchestrator import QuestionPipelineOrchestrator
from quiz.models.question_data import QuestionStyle
from ai_module.config import AIConfig
from neomodel import db
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Complete Question Management Pipeline: Select Node → Generate Questions → Validate Questions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Run in automatic mode (no user interaction)',
        )
        parser.add_argument(
            '--knowledge-id',
            type=str,
            help='Pre-select knowledge node by name',
        )
        parser.add_argument(
            '--style',
            type=str,
            choices=['multiple_choice', 'fill_in_blank', 'missing_word'],
            help='Pre-select question style',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Number of questions to generate (default: 3)',
        )
        parser.add_argument(
            '--create-sample',
            action='store_true',
            help='Create sample knowledge nodes for testing',
        )
        parser.add_argument(
            '--show-all',
            action='store_true',
            help='Display all generated questions with validation results',
        )
        parser.add_argument(
            '--show-details',
            action='store_true',
            help='Show detailed validation results for each question',
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🚀 Question Management Pipeline")
        self.stdout.write("=" * 70)
        self.stdout.write("Complete workflow: Knowledge Selection → Style Selection → Generation → Validation")
        self.stdout.write("=" * 70)
        
        # Test prerequisites
        if not self.test_prerequisites():
            return
        
        # Create sample data if requested
        if options['create_sample']:
            self.create_sample_knowledge()
        
        # Initialize pipeline orchestrator
        orchestrator = QuestionPipelineOrchestrator()
        
        try:
            # Parse style if provided
            selected_style = None
            if options['style']:
                selected_style = QuestionStyle(options['style'])
            
            # Run complete pipeline
            self.stdout.write("\n🎯 Starting complete pipeline...")
            
            result = orchestrator.run_complete_pipeline(
                knowledge_id=options['knowledge_id'],
                style=selected_style,
                count=options['count'],
                auto_mode=options['auto'],
                progress_callback=self.display_progress
            )
            
            if not result.success:
                self.stdout.write(
                    self.style.ERROR(f"\n❌ Pipeline failed: {result.error_message}")
                )
                return
            
            # Display results
            self.display_pipeline_results(result, options)
            
            # Success message
            self.stdout.write(
                self.style.SUCCESS(f"\n🎉 Pipeline completed successfully!")
            )
            
            # Final statistics
            self.stdout.write(f"\n📈 Final Statistics:")
            self.stdout.write(f"   Knowledge Node: {result.knowledge_node.name}")
            self.stdout.write(f"   Question Style: {result.question_style.value}")
            self.stdout.write(f"   Questions Generated: {result.questions_generated}/{result.questions_requested}")
            self.stdout.write(f"   Average Validation Score: {result.average_validation_score:.2f}/1.0")
            self.stdout.write(f"   High Quality Questions: {result.high_quality_questions}")
            self.stdout.write(f"   Total Pipeline Time: {result.pipeline_time:.1f}s")

            # Neo4j persistence results
            if result.saved_to_neo4j:
                self.stdout.write(f"\n💾 Neo4j Database:")
                self.stdout.write(f"   Status: ✅ Successfully saved to database")
                self.stdout.write(f"   Questions Saved: {result.saved_quiz_count}")
                self.stdout.write(f"   Session ID: {result.neo4j_session_id}")
            else:
                self.stdout.write(f"\n💾 Neo4j Database:")
                self.stdout.write(f"   Status: ❌ Not saved to database")
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            self.stdout.write(
                self.style.ERROR(f"\n❌ Pipeline execution failed: {str(e)}")
            )
            raise CommandError(f"Pipeline failed: {e}")
    
    def display_progress(self, progress):
        """Display pipeline progress"""
        overall_percentage = progress.overall_progress
        bar_length = 50
        filled_length = int(bar_length * overall_percentage)
        
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        print(f"\r🚀 Pipeline: [{bar}] {overall_percentage:.1%} - "
              f"Step {progress.current_step}/{progress.total_steps}: {progress.step_name}", 
              end='', flush=True)
    
    def display_pipeline_results(self, result, options):
        """Display comprehensive pipeline results"""
        print("\n\n" + "=" * 70)
        print("=== Complete Pipeline Results ===")
        print("=" * 70)
        
        # Generation summary
        gen_result = result.generation_result
        print(f"📊 Generation Summary:")
        print(f"   Knowledge: {result.knowledge_node.name}")
        print(f"   Style: {result.question_style.value.replace('_', ' ').title()}")
        print(f"   Requested: {gen_result.total_requested}")
        print(f"   Generated: {gen_result.total_generated}")
        print(f"   Failed: {gen_result.total_failed}")
        print(f"   Success Rate: {gen_result.success_rate:.1%}")
        print(f"   Generation Time: {gen_result.generation_time:.1f}s")
        
        # Validation summary
        val_result = result.validation_result
        print(f"\n🔍 Validation Summary:")
        print(f"   Average Score: {val_result.average_score:.2f}/1.0")
        print(f"   High Quality (≥0.9): {val_result.high_quality_count} questions")
        print(f"   Medium Quality (0.7-0.9): {val_result.medium_quality_count} questions")
        print(f"   Low Quality (<0.7): {val_result.low_quality_count} questions")
        print(f"   Total Issues: {val_result.total_issues}")
        print(f"   Total Recommendations: {val_result.total_recommendations}")
        
        # Questions preview or full display
        if options['show_all'] and gen_result.questions:
            print(f"\n📋 All Questions with Validation Results:")
            print("=" * 70)
            
            for i, (question, validation) in enumerate(zip(gen_result.questions, val_result.results), 1):
                print(f"\n--- Question {i}/{len(gen_result.questions)} ---")
                print(f"Score: {validation.overall_score:.2f}/1.0 {validation.quality_emoji} {validation.quality_level}")
                print(f"Q: {question.question}")
                
                # Show choices
                for choice in question.choices:
                    status = "✅" if choice.is_correct else "❌"
                    print(f"   {choice.letter}) {choice.text} [{status}]")
                    if options['show_details']:
                        print(f"      {choice.explanation}")
                
                # Show validation details if requested
                if options['show_details'] and validation.issues:
                    print(f"\n   Issues ({len(validation.issues)}):")
                    for issue in validation.issues:
                        severity_emoji = {"low": "🟡", "medium": "🟠", "high": "🔴"}
                        emoji = severity_emoji.get(issue.severity.value, "⚪")
                        print(f"   {emoji} {issue.description}")
                        if issue.suggestion:
                            print(f"      💡 {issue.suggestion}")
                
                if i < len(gen_result.questions):
                    print("-" * 50)
        
        elif gen_result.questions:
            # Show preview
            print(f"\n📋 Questions Preview (showing 3/{len(gen_result.questions)}):")
            print("=" * 70)
            
            for i, (question, validation) in enumerate(zip(gen_result.questions[:3], val_result.results[:3]), 1):
                print(f"\n[{i}] Score: {validation.overall_score:.2f}/1.0 {validation.quality_emoji}")
                print(f"    Q: {question.question}")
                correct_choice = question.get_correct_choice()
                print(f"    Correct: {correct_choice.letter}) {correct_choice.text}")
                
                if validation.issues:
                    print(f"    Issues: {len(validation.issues)} found")
            
            if len(gen_result.questions) > 3:
                print(f"\n... and {len(gen_result.questions) - 3} more questions")
                print("💡 Use --show-all to see all questions")
        
        print("=" * 70)
    
    def test_prerequisites(self) -> bool:
        """Test all prerequisites for pipeline execution"""
        self.stdout.write("🔍 Testing prerequisites...")
        
        # Test Neo4j connection
        try:
            result, meta = db.cypher_query("RETURN 1 as test")
            self.stdout.write("  ✅ Neo4j connection successful")
        except Exception as e:
            self.stdout.write(f"  ❌ Neo4j connection failed: {e}")
            return False
        
        # Test AI configuration
        try:
            ai_config = AIConfig()
            if not ai_config.api_key:
                self.stdout.write("  ❌ No OpenAI API key found")
                self.stdout.write("     💡 Set OPENAI_API_KEY environment variable")
                return False
            
            self.stdout.write(f"  ✅ AI configuration valid (provider: {ai_config.provider})")
            
        except Exception as e:
            self.stdout.write(f"  ❌ AI configuration failed: {e}")
            return False
        
        return True

    def create_sample_knowledge(self):
        """Create sample knowledge nodes for testing"""
        self.stdout.write("📝 Creating sample knowledge nodes...")

        from knowledge.neo_models import Knowledge

        sample_data = [
            {
                "name": "Common Errors",
                "description": "Learners often misuse time expressions, auxiliaries, and participles with the present perfect. Awareness prevents systematic mistakes.",
                "example": "I have went (incorrect) → I have gone (correct)."
            },
            {
                "name": "Present Perfect Tense",
                "description": "Formation and usage of present perfect tense for actions that started in the past and continue to the present or have relevance to the present.",
                "example": "She has lived here for 5 years."
            },
            {
                "name": "Modal Verbs",
                "description": "Usage of modal verbs (can, could, should, must, might, may) to express ability, possibility, permission, and obligation.",
                "example": "You should study harder for better results."
            },
            {
                "name": "Conditional Sentences",
                "description": "Formation and usage of conditional sentences (if-clauses) to express hypothetical situations and their consequences.",
                "example": "If I had studied harder, I would have passed the exam."
            }
        ]

        created_count = 0
        for data in sample_data:
            try:
                # Check if node already exists
                existing = Knowledge.nodes.filter(name=data["name"]).first()
                if not existing:
                    node = Knowledge(**data).save()
                    self.stdout.write(f"  ✅ Created: {node.name}")
                    created_count += 1
                else:
                    self.stdout.write(f"  ⏭️  Exists: {data['name']}")
            except Exception as e:
                self.stdout.write(f"  ❌ Failed to create {data['name']}: {e}")

        self.stdout.write(f"📊 Created {created_count} new knowledge nodes")
