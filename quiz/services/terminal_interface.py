from typing import Optional
from quiz.models.question_data import QuestionStyle
import logging

logger = logging.getLogger(__name__)


class TerminalInterface:
    """Service for handling terminal interactions with Quiz Team"""
    
    def display_question_style_menu(self) -> None:
        """Display the question style selection menu"""
        print("\n" + "=" * 60)
        print("=== Question Style Selection ===")
        print("=" * 60)
        print("Choose the format for your questions:")
        print()
        print("[1] Multiple Choice")
        print("    • 4 options (A, B, C, D) with explanations")
        print("    • One correct answer")
        print("    • Best for testing comprehension")
        print()
        print("[2] Fill in the Blanks")
        print("    • Complete the sentence with correct word/phrase")
        print("    • Tests specific vocabulary or grammar")
        print("    • Format: 'She _____ to school every day.'")
        print()
        print("[3] Missing Word")
        print("    • Identify which word is missing from a sentence")
        print("    • Tests understanding of sentence structure")
        print("    • Format: 'She goes school every day. What word is missing?'")
        print()
        print("=" * 60)
    
    def get_question_style_selection(self) -> Optional[QuestionStyle]:
        """Get user selection for question style"""
        self.display_question_style_menu()
        
        style_map = {
            1: QuestionStyle.MULTIPLE_CHOICE,
            2: QuestionStyle.FILL_IN_BLANK,
            3: QuestionStyle.MISSING_WORD
        }
        
        while True:
            try:
                choice = input("\nSelect question style (1-3) or 'q' to quit: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                selection = int(choice)
                
                if selection in style_map:
                    selected_style = style_map[selection]
                    print(f"\n✅ Selected: {selected_style.value.replace('_', ' ').title()}")
                    return selected_style
                else:
                    print("Invalid selection. Please enter 1, 2, or 3.")
                    
            except ValueError:
                print("Invalid input. Please enter a number (1-3) or 'q' to quit.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return None
    
    def confirm_question_generation(self, knowledge_name: str, style: QuestionStyle, count: int = 10) -> bool:
        """Confirm question generation parameters"""
        print("\n" + "=" * 60)
        print("=== Generation Confirmation ===")
        print("=" * 60)
        print(f"Knowledge Node: {knowledge_name}")
        print(f"Question Style: {style.value.replace('_', ' ').title()}")
        print(f"Number of Questions: {count}")
        print("=" * 60)
        
        while True:
            try:
                choice = input("\nProceed with question generation? (y/n): ").strip().lower()
                
                if choice in ['y', 'yes']:
                    return True
                elif choice in ['n', 'no']:
                    return False
                else:
                    print("Please enter 'y' for yes or 'n' for no.")
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return False
    
    def display_style_examples(self, style: QuestionStyle) -> None:
        """Display examples for the selected question style"""
        print(f"\n📝 Examples for {style.value.replace('_', ' ').title()}:")
        print("-" * 50)
        
        if style == QuestionStyle.MULTIPLE_CHOICE:
            print("Example:")
            print("Q: Which sentence uses the present perfect correctly?")
            print("A) I have went to Paris last year")
            print("B) I have gone to Paris many times")
            print("C) I have go to Paris yesterday") 
            print("D) I have going to Paris tomorrow")
            print("Correct: B")
            
        elif style == QuestionStyle.FILL_IN_BLANK:
            print("Example:")
            print("Q: She _____ to school every day.")
            print("A) go")
            print("B) goes") 
            print("C) going")
            print("D) gone")
            print("Correct: B")
            
        elif style == QuestionStyle.MISSING_WORD:
            print("Example:")
            print("Q: 'She goes school every day.' What word is missing?")
            print("A) to")
            print("B) at")
            print("C) in") 
            print("D) on")
            print("Correct: A")
        
        print("-" * 50)
    
    def get_question_count(self, default: int = 10) -> int:
        """Get the number of questions to generate"""
        while True:
            try:
                choice = input(f"\nHow many questions to generate? (default: {default}): ").strip()
                
                if not choice:
                    return default
                
                count = int(choice)
                
                if 1 <= count <= 50:
                    return count
                else:
                    print("Please enter a number between 1 and 50.")
                    
            except ValueError:
                print("Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return default
