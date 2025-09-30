from typing import List, Optional
from knowledge.neo_models import Knowledge
from neomodel import db
import logging

logger = logging.getLogger(__name__)


class KnowledgeQueryService:
    """Service for querying and managing knowledge nodes"""
    
    def list_all_knowledge_nodes(self) -> List[Knowledge]:
        """Query all knowledge nodes from Neo4j"""
        try:
            nodes = Knowledge.nodes.all()
            logger.info(f"Retrieved {len(nodes)} knowledge nodes")
            return list(nodes)
        except Exception as e:
            logger.error(f"Error querying knowledge nodes: {e}")
            raise
    
    def get_knowledge_by_index(self, nodes: List[Knowledge], index: int) -> Optional[Knowledge]:
        """Get knowledge node by list index (1-based)"""
        if 1 <= index <= len(nodes):
            return nodes[index - 1]
        return None
    
    def display_knowledge_terminal(self, nodes: List[Knowledge]) -> None:
        """Display knowledge nodes in formatted terminal output"""
        print("\n" + "=" * 50)
        print("=== Available Knowledge Nodes ===")
        print("=" * 50)
        
        if not nodes:
            print("No knowledge nodes found in the database.")
            return
        
        for i, node in enumerate(nodes, 1):
            print(f"\n[{i}] {node.name}")
            
            if node.description:
                # Truncate long descriptions for display
                desc = node.description[:100] + "..." if len(node.description) > 100 else node.description
                print(f"    Description: {desc}")
            
            if node.example:
                print(f"    Example: {node.example}")
        
        print(f"\nTotal nodes found: {len(nodes)}")
        print("=" * 50)
    
    def get_user_selection(self, nodes: List[Knowledge]) -> Optional[Knowledge]:
        """Get user selection from terminal input"""
        if not nodes:
            return None
        
        while True:
            try:
                choice = input(f"\nSelect a knowledge node (1-{len(nodes)}) or 'q' to quit: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                index = int(choice)
                selected = self.get_knowledge_by_index(nodes, index)
                
                if selected:
                    return selected
                else:
                    print(f"Invalid selection. Please enter a number between 1 and {len(nodes)}")
                    
            except ValueError:
                print("Invalid input. Please enter a number or 'q' to quit.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return None
    
    def display_selected_knowledge(self, knowledge: Knowledge) -> None:
        """Display detailed information about selected knowledge node"""
        print("\n" + "=" * 50)
        print("=== Selected Knowledge Node ===")
        print("=" * 50)
        print(f"Name: {knowledge.name}")
        print(f"Description: {knowledge.description or 'No description available'}")
        print(f"Example: {knowledge.example or 'No example available'}")
        
        # Show relationships if any
        try:
            dependencies = list(knowledge.depends_on.all())
            if dependencies:
                print(f"Dependencies: {', '.join([dep.name for dep in dependencies])}")
        except Exception as e:
            logger.warning(f"Could not load dependencies: {e}")
        
        print("=" * 50)
