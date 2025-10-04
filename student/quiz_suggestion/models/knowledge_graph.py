"""
Knowledge Graph wrapper using NetworkX.

This module provides a NetworkX-based representation of the knowledge graph
stored in Neo4j, with efficient prerequisite traversal and cycle detection.
"""

import networkx as nx
from typing import List, Set, Optional
import logging
from student.quiz_suggestion.exceptions import CycleDetectedError, MissingNodeError

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """
    NetworkX wrapper for the Neo4j knowledge graph.

    This class loads the knowledge graph from Neo4j and provides efficient
    methods for prerequisite traversal, topological sorting, and cycle detection.

    The graph is a directed acyclic graph (DAG) where:
    - Nodes represent knowledge concepts
    - Edges represent DEPENDS_ON relationships (prerequisites)

    Example:
        kg = KnowledgeGraph.from_neo4j()
        prereqs = kg.get_prerequisites("python_functions")
        if kg.is_prerequisite_met("python_functions", user_profile):
            print("Ready to learn functions!")
    """

    def __init__(self):
        """Initialize an empty knowledge graph"""
        self.graph = nx.DiGraph()
        self._topo_order = None  # Cached topological order

    def add_node(self, node_id: str, **attrs):
        """
        Add a knowledge node to the graph.

        Args:
            node_id: Unique identifier for the node
            **attrs: Additional node attributes (name, description, etc.)
        """
        self.graph.add_node(node_id, **attrs)
        self._topo_order = None  # Invalidate cache

    def add_edge(self, from_node: str, to_node: str):
        """
        Add a prerequisite edge (from_node depends on to_node).

        Args:
            from_node: The node that has a prerequisite
            to_node: The prerequisite node
        """
        self.graph.add_edge(from_node, to_node)
        self._topo_order = None  # Invalidate cache

    def nodes(self) -> List[str]:
        """Get all node IDs in the graph"""
        return list(self.graph.nodes())

    def edges(self) -> List[tuple]:
        """Get all edges in the graph"""
        return list(self.graph.edges())

    def has_node(self, node_id: str) -> bool:
        """Check if a node exists in the graph"""
        return self.graph.has_node(node_id)

    def get_node_attrs(self, node_id: str) -> dict:
        """Get attributes for a node"""
        if not self.has_node(node_id):
            raise MissingNodeError(f"Node {node_id!r} not found in graph")
        return dict(self.graph.nodes[node_id])

    def get_prerequisites(self, node_id: str) -> Set[str]:
        """
        Get immediate prerequisites for a node.

        Args:
            node_id: The node to get prerequisites for

        Returns:
            Set of prerequisite node IDs
        """
        if not self.has_node(node_id):
            raise MissingNodeError(f"Node {node_id!r} not found in graph")

        # In NetworkX, successors are nodes that this node points to
        # In our graph, edges point from dependent -> prerequisite
        return set(self.graph.successors(node_id))

    def get_all_prerequisites(self, node_id: str) -> Set[str]:
        """
        Get all prerequisites (transitive closure) for a node.

        This includes immediate prerequisites and their prerequisites, recursively.

        Args:
            node_id: The node to get prerequisites for

        Returns:
            Set of all prerequisite node IDs
        """
        if not self.has_node(node_id):
            raise MissingNodeError(f"Node {node_id!r} not found in graph")

        # Use NetworkX descendants (all reachable nodes)
        return set(nx.descendants(self.graph, node_id))

    def get_dependents(self, node_id: str) -> Set[str]:
        """
        Get immediate dependents for a node (nodes that depend on this one).

        Args:
            node_id: The node to get dependents for

        Returns:
            Set of dependent node IDs
        """
        if not self.has_node(node_id):
            raise MissingNodeError(f"Node {node_id!r} not found in graph")

        # Predecessors are nodes that point to this node
        return set(self.graph.predecessors(node_id))

    def is_acyclic(self) -> bool:
        """Check if the graph is acyclic (no circular dependencies)"""
        return nx.is_directed_acyclic_graph(self.graph)

    def find_cycles(self) -> List[List[str]]:
        """
        Find all cycles in the graph.

        Returns:
            List of cycles, where each cycle is a list of node IDs
        """
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except Exception:
            return []

    def topological_order(self) -> List[str]:
        """
        Get topological ordering of nodes (prerequisites before dependents).

        Returns:
            List of node IDs in topological order

        Raises:
            CycleDetectedError: If the graph has cycles
        """
        if self._topo_order is not None:
            return self._topo_order

        if not self.is_acyclic():
            cycles = self.find_cycles()
            raise CycleDetectedError(
                f"Graph has {len(cycles)} cycle(s). First cycle: {cycles[0] if cycles else 'unknown'}"
            )

        try:
            self._topo_order = list(nx.topological_sort(self.graph))
            return self._topo_order
        except nx.NetworkXError as e:
            raise CycleDetectedError(f"Failed to compute topological order: {e}")

    def get_learning_path(self, target_node: str) -> List[str]:
        """
        Get a suggested learning path to reach a target node.

        This returns all prerequisites in topological order.

        Args:
            target_node: The goal node

        Returns:
            List of node IDs to learn in order (including target)
        """
        if not self.has_node(target_node):
            raise MissingNodeError(f"Node {target_node!r} not found in graph")

        # Get all prerequisites
        prereqs = self.get_all_prerequisites(target_node)
        prereqs.add(target_node)

        # Filter topological order to only include these nodes
        topo = self.topological_order()
        return [n for n in topo if n in prereqs]

    @classmethod
    def from_neo4j(cls) -> "KnowledgeGraph":
        """
        Load the knowledge graph from Neo4j.

        This reads all Knowledge nodes and DEPENDS_ON relationships
        from the Neo4j database.

        Returns:
            KnowledgeGraph: Populated knowledge graph

        Example:
            kg = KnowledgeGraph.from_neo4j()
            print(f"Loaded {len(kg.nodes())} knowledge nodes")
        """
        from knowledge.neo_models import Knowledge as NeoKnowledge

        kg = cls()

        # Load all knowledge nodes
        logger.info("Loading knowledge nodes from Neo4j...")
        for neo_knowledge in NeoKnowledge.nodes.all():
            try:
                # Get unique ID (use element_id for Neo4j v5+, fallback to name)
                node_id = (
                    getattr(neo_knowledge, "element_id", None) or neo_knowledge.name
                )

                # Add node with attributes
                kg.add_node(
                    str(node_id),
                    name=neo_knowledge.name,
                    description=getattr(neo_knowledge, "description", None),
                    example=getattr(neo_knowledge, "example", None),
                )
            except Exception as e:
                logger.warning(f"Failed to load knowledge node {neo_knowledge}: {e}")
                continue

        logger.info(f"Loaded {len(kg.nodes())} knowledge nodes")

        # Load all DEPENDS_ON relationships
        logger.info("Loading prerequisite relationships...")
        edge_count = 0
        for neo_knowledge in NeoKnowledge.nodes.all():
            try:
                from_id = (
                    getattr(neo_knowledge, "element_id", None) or neo_knowledge.name
                )
                from_id = str(from_id)

                # Get prerequisites (nodes this one depends on)
                for prereq in neo_knowledge.depends_on.all():
                    to_id = getattr(prereq, "element_id", None) or prereq.name
                    to_id = str(to_id)

                    if kg.has_node(from_id) and kg.has_node(to_id):
                        kg.add_edge(from_id, to_id)
                        edge_count += 1
            except Exception as e:
                logger.warning(f"Failed to load prerequisites for {neo_knowledge}: {e}")
                continue

        logger.info(f"Loaded {edge_count} prerequisite relationships")

        # Validate graph is acyclic
        if not kg.is_acyclic():
            cycles = kg.find_cycles()
            logger.error(f"Knowledge graph has {len(cycles)} cycle(s)!")
            for i, cycle in enumerate(cycles[:3], 1):  # Show first 3 cycles
                logger.error(f"  Cycle {i}: {' -> '.join(cycle)}")
            raise CycleDetectedError(
                f"Knowledge graph has {len(cycles)} circular dependencies. "
                f"First cycle: {cycles[0] if cycles else 'unknown'}"
            )

        logger.info("Knowledge graph loaded successfully (acyclic)")
        return kg

    def __repr__(self) -> str:
        return f"KnowledgeGraph(nodes={len(self.nodes())}, edges={len(self.edges())})"
