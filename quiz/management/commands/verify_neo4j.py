from django.core.management.base import BaseCommand, CommandError
from quiz.neo_models import Quiz, Choice
from knowledge.neo_models import Knowledge
from neomodel import db
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verify Neo4j database content and relationships for questions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--knowledge-name',
            type=str,
            help='Show questions for specific knowledge node',
        )
        parser.add_argument(
            '--session-id',
            type=str,
            help='Show questions for specific generation session',
        )
        parser.add_argument(
            '--show-relationships',
            action='store_true',
            help='Show detailed relationship information',
        )
        parser.add_argument(
            '--show-choices',
            action='store_true',
            help='Show choices for each question',
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🔍 Neo4j Database Verification")
        self.stdout.write("=" * 60)
        
        # Test Neo4j connection
        if not self.test_neo4j_connection():
            return
        
        # Show database statistics
        self.show_database_statistics()
        
        # Show questions based on filters
        if options['knowledge_name']:
            self.show_questions_by_knowledge(options['knowledge_name'], options)
        elif options['session_id']:
            self.show_questions_by_session(options['session_id'], options)
        else:
            self.show_all_questions(options)
        
        # Show relationships if requested
        if options['show_relationships']:
            self.show_relationships()
    
    def test_neo4j_connection(self) -> bool:
        """Test Neo4j connection"""
        try:
            result, meta = db.cypher_query("RETURN 1 as test")
            self.stdout.write("✅ Neo4j connection successful")
            return True
        except Exception as e:
            self.stdout.write(f"❌ Neo4j connection failed: {e}")
            return False
    
    def show_database_statistics(self):
        """Show overall database statistics"""
        self.stdout.write("\n📊 Database Statistics:")
        
        try:
            # Count nodes
            knowledge_count = len(Knowledge.nodes.all())
            quiz_count = len(Quiz.nodes.all())
            choice_count = len(Choice.nodes.all())
            
            self.stdout.write(f"   Knowledge Nodes: {knowledge_count}")
            self.stdout.write(f"   Quiz Nodes: {quiz_count}")
            self.stdout.write(f"   Choice Nodes: {choice_count}")
            
            # Count relationships
            quiz_knowledge_rels = db.cypher_query("MATCH (:Quiz)-[:RELATED_TO]->(:Knowledge) RETURN count(*) as count")[0][0][0]
            quiz_choice_rels = db.cypher_query("MATCH (:Quiz)-[:HAS_CHOICE]->(:Choice) RETURN count(*) as count")[0][0][0]
            choice_knowledge_rels = db.cypher_query("MATCH (:Choice)-[:RELATED_TO]->(:Knowledge) RETURN count(*) as count")[0][0][0]
            
            self.stdout.write(f"   Quiz→Knowledge Relations: {quiz_knowledge_rels}")
            self.stdout.write(f"   Quiz→Choice Relations: {quiz_choice_rels}")
            self.stdout.write(f"   Choice→Knowledge Relations: {choice_knowledge_rels}")
            
        except Exception as e:
            self.stdout.write(f"❌ Failed to get statistics: {e}")
    
    def show_questions_by_knowledge(self, knowledge_name: str, options: dict):
        """Show questions for a specific knowledge node"""
        self.stdout.write(f"\n📋 Questions for Knowledge: {knowledge_name}")
        self.stdout.write("-" * 60)
        
        try:
            knowledge_node = Knowledge.nodes.get(name=knowledge_name)
            questions = knowledge_node.related_quizzes.all()
            
            if not questions:
                self.stdout.write("No questions found for this knowledge node.")
                return
            
            for i, quiz in enumerate(questions, 1):
                self.display_quiz_info(quiz, i, options)
                
        except Knowledge.DoesNotExist:
            self.stdout.write(f"❌ Knowledge node '{knowledge_name}' not found")
        except Exception as e:
            self.stdout.write(f"❌ Error retrieving questions: {e}")
    
    def show_questions_by_session(self, session_id: str, options: dict):
        """Show questions for a specific generation session"""
        self.stdout.write(f"\n📋 Questions for Session: {session_id}")
        self.stdout.write("-" * 60)
        
        try:
            questions = Quiz.nodes.filter(generation_session_id=session_id)
            question_list = list(questions)
            
            if not question_list:
                self.stdout.write("No questions found for this session.")
                return
            
            for i, quiz in enumerate(question_list, 1):
                self.display_quiz_info(quiz, i, options)
                
        except Exception as e:
            self.stdout.write(f"❌ Error retrieving session questions: {e}")
    
    def show_all_questions(self, options: dict):
        """Show all questions in database"""
        self.stdout.write(f"\n📋 All Questions in Database:")
        self.stdout.write("-" * 60)
        
        try:
            questions = Quiz.nodes.all()
            
            if not questions:
                self.stdout.write("No questions found in database.")
                return
            
            # Group by knowledge node
            knowledge_groups = {}
            for quiz in questions:
                knowledge = quiz.related_to.single()
                knowledge_name = knowledge.name if knowledge else "Unknown"
                
                if knowledge_name not in knowledge_groups:
                    knowledge_groups[knowledge_name] = []
                knowledge_groups[knowledge_name].append(quiz)
            
            for knowledge_name, quizzes in knowledge_groups.items():
                self.stdout.write(f"\n📚 {knowledge_name} ({len(quizzes)} questions):")
                for i, quiz in enumerate(quizzes, 1):
                    self.display_quiz_info(quiz, i, options, indent="  ")
                    
        except Exception as e:
            self.stdout.write(f"❌ Error retrieving questions: {e}")
    
    def display_quiz_info(self, quiz: Quiz, index: int, options: dict, indent: str = ""):
        """Display information about a quiz"""
        self.stdout.write(f"{indent}[{index}] {quiz.quiz_text[:80]}...")
        self.stdout.write(f"{indent}    Style: {quiz.question_style}")
        
        if quiz.validation_score is not None:
            score_emoji = "✅" if quiz.validation_score >= 0.9 else "⚠️" if quiz.validation_score >= 0.7 else "❌"
            self.stdout.write(f"{indent}    Validation: {quiz.validation_score:.2f} {score_emoji}")
        
        if quiz.generation_session_id:
            self.stdout.write(f"{indent}    Session: {quiz.generation_session_id}")
        
        if quiz.created_at:
            self.stdout.write(f"{indent}    Created: {quiz.created_at}")
        
        # Show choices if requested
        if options.get('show_choices'):
            choices = quiz.has_choice.all()
            self.stdout.write(f"{indent}    Choices:")
            for choice in choices:
                correct_mark = "✅" if choice.is_correct else "❌"
                self.stdout.write(f"{indent}      {choice.choice_letter}) {choice.choice_text} {correct_mark}")
        
        self.stdout.write("")
    
    def show_relationships(self):
        """Show detailed relationship information"""
        self.stdout.write(f"\n🔗 Relationship Details:")
        self.stdout.write("-" * 60)
        
        try:
            # Quiz to Knowledge relationships
            query = """
            MATCH (q:Quiz)-[:RELATED_TO]->(k:Knowledge)
            RETURN k.name as knowledge, count(q) as quiz_count
            ORDER BY quiz_count DESC
            """
            results, meta = db.cypher_query(query)
            
            self.stdout.write("📚 Questions per Knowledge Node:")
            for row in results:
                knowledge_name, quiz_count = row
                self.stdout.write(f"   {knowledge_name}: {quiz_count} questions")
            
            # Choice distribution
            query = """
            MATCH (q:Quiz)-[:HAS_CHOICE]->(c:Choice)
            RETURN q.question_style as style, count(c) as choice_count
            ORDER BY choice_count DESC
            """
            results, meta = db.cypher_query(query)
            
            self.stdout.write("\n🎯 Choices per Question Style:")
            for row in results:
                style, choice_count = row
                self.stdout.write(f"   {style}: {choice_count} choices")
            
            # Validation score distribution
            query = """
            MATCH (q:Quiz)
            WHERE q.validation_score IS NOT NULL
            RETURN 
                count(CASE WHEN q.validation_score >= 0.9 THEN 1 END) as high,
                count(CASE WHEN q.validation_score >= 0.7 AND q.validation_score < 0.9 THEN 1 END) as medium,
                count(CASE WHEN q.validation_score < 0.7 THEN 1 END) as low
            """
            results, meta = db.cypher_query(query)
            
            if results:
                high, medium, low = results[0]
                self.stdout.write("\n📊 Validation Score Distribution:")
                self.stdout.write(f"   High Quality (≥0.9): {high} questions")
                self.stdout.write(f"   Medium Quality (0.7-0.9): {medium} questions")
                self.stdout.write(f"   Low Quality (<0.7): {low} questions")
            
        except Exception as e:
            self.stdout.write(f"❌ Error showing relationships: {e}")
        
        self.stdout.write("\n✅ Neo4j verification completed!")
