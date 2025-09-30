from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ValidationIssueType(Enum):
    """Types of validation issues"""
    SPELLING = "spelling"
    GRAMMAR = "grammar"
    LOGIC = "logic"
    CLARITY = "clarity"
    RELEVANCE = "relevance"


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    type: ValidationIssueType
    severity: ValidationSeverity
    description: str
    suggestion: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ValidationIssue':
        """Create ValidationIssue from dictionary"""
        return cls(
            type=ValidationIssueType(data.get("type", "clarity")),
            severity=ValidationSeverity(data.get("severity", "low")),
            description=data.get("description", ""),
            suggestion=data.get("suggestion", "")
        )


@dataclass
class ValidationDetails:
    """Detailed validation scores"""
    spelling_grammar_score: float
    single_correct_answer: bool
    explanation_quality_score: float
    knowledge_relevance_score: float
    clarity_score: float
    
    def __post_init__(self):
        """Validate score ranges"""
        scores = [
            self.spelling_grammar_score,
            self.explanation_quality_score,
            self.knowledge_relevance_score,
            self.clarity_score
        ]
        
        for score in scores:
            if not (0.0 <= score <= 1.0):
                raise ValueError(f"Scores must be between 0.0 and 1.0, got {score}")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ValidationDetails':
        """Create ValidationDetails from dictionary"""
        return cls(
            spelling_grammar_score=data.get("spelling_grammar_score", 0.0),
            single_correct_answer=data.get("single_correct_answer", False),
            explanation_quality_score=data.get("explanation_quality_score", 0.0),
            knowledge_relevance_score=data.get("knowledge_relevance_score", 0.0),
            clarity_score=data.get("clarity_score", 0.0)
        )
    
    @property
    def average_score(self) -> float:
        """Calculate average of all numeric scores"""
        scores = [
            self.spelling_grammar_score,
            self.explanation_quality_score,
            self.knowledge_relevance_score,
            self.clarity_score
        ]
        return sum(scores) / len(scores)


@dataclass
class ValidationResult:
    """Complete validation result for a question"""
    overall_score: float
    is_valid: bool
    validation_details: ValidationDetails
    issues: List[ValidationIssue]
    recommendations: List[str]
    question_text: Optional[str] = None
    
    def __post_init__(self):
        """Validate overall score range"""
        if not (0.0 <= self.overall_score <= 1.0):
            raise ValueError(f"Overall score must be between 0.0 and 1.0, got {self.overall_score}")
    
    @classmethod
    def from_ai_response(cls, ai_response: dict, question_text: str = "") -> 'ValidationResult':
        """Create ValidationResult from AI response"""
        # Parse issues
        issues = []
        for issue_data in ai_response.get("issues", []):
            try:
                issue = ValidationIssue.from_dict(issue_data)
                issues.append(issue)
            except (ValueError, KeyError) as e:
                # Skip invalid issues but log them
                print(f"Warning: Invalid issue data: {issue_data}, error: {e}")
        
        # Parse validation details
        details = ValidationDetails.from_dict(ai_response.get("validation_details", {}))
        
        return cls(
            overall_score=ai_response.get("overall_score", 0.0),
            is_valid=ai_response.get("is_valid", False),
            validation_details=details,
            issues=issues,
            recommendations=ai_response.get("recommendations", []),
            question_text=question_text
        )
    
    @property
    def quality_level(self) -> str:
        """Get quality level based on overall score"""
        if self.overall_score >= 0.9:
            return "HIGH"
        elif self.overall_score >= 0.7:
            return "MEDIUM"
        else:
            return "LOW"
    
    @property
    def quality_emoji(self) -> str:
        """Get emoji for quality level"""
        if self.overall_score >= 0.9:
            return "✅"
        elif self.overall_score >= 0.7:
            return "⚠️"
        else:
            return "❌"
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any high severity issues"""
        return any(issue.severity == ValidationSeverity.HIGH for issue in self.issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues filtered by severity"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def to_display_format(self) -> str:
        """Format validation result for terminal display"""
        lines = []
        lines.append(f"Overall Score: {self.overall_score:.2f}/1.0 {self.quality_emoji} {self.quality_level}")
        lines.append(f"Valid: {'Yes' if self.is_valid else 'No'}")
        lines.append("")
        
        # Detailed scores
        lines.append("Detailed Scores:")
        lines.append(f"  Spelling/Grammar: {self.validation_details.spelling_grammar_score:.2f}")
        lines.append(f"  Single Correct Answer: {'Yes' if self.validation_details.single_correct_answer else 'No'}")
        lines.append(f"  Explanation Quality: {self.validation_details.explanation_quality_score:.2f}")
        lines.append(f"  Knowledge Relevance: {self.validation_details.knowledge_relevance_score:.2f}")
        lines.append(f"  Clarity: {self.validation_details.clarity_score:.2f}")
        
        # Issues
        if self.issues:
            lines.append("")
            lines.append(f"Issues ({len(self.issues)}):")
            for issue in self.issues:
                severity_emoji = {"low": "🟡", "medium": "🟠", "high": "🔴"}
                emoji = severity_emoji.get(issue.severity.value, "⚪")
                lines.append(f"  {emoji} {issue.type.value.title()}: {issue.description}")
                if issue.suggestion:
                    lines.append(f"     Suggestion: {issue.suggestion}")
        
        # Recommendations
        if self.recommendations:
            lines.append("")
            lines.append(f"Recommendations ({len(self.recommendations)}):")
            for rec in self.recommendations:
                lines.append(f"  💡 {rec}")
        
        return "\n".join(lines)


@dataclass
class BatchValidationResult:
    """Result of validating multiple questions"""
    results: List[ValidationResult]
    total_questions: int
    average_score: float
    high_quality_count: int
    medium_quality_count: int
    low_quality_count: int
    total_issues: int
    total_recommendations: int
    
    @classmethod
    def from_results(cls, results: List[ValidationResult]) -> 'BatchValidationResult':
        """Create BatchValidationResult from individual results"""
        total = len(results)
        if total == 0:
            return cls([], 0, 0.0, 0, 0, 0, 0, 0)
        
        avg_score = sum(r.overall_score for r in results) / total
        high_count = sum(1 for r in results if r.quality_level == "HIGH")
        medium_count = sum(1 for r in results if r.quality_level == "MEDIUM")
        low_count = sum(1 for r in results if r.quality_level == "LOW")
        total_issues = sum(len(r.issues) for r in results)
        total_recs = sum(len(r.recommendations) for r in results)
        
        return cls(
            results=results,
            total_questions=total,
            average_score=avg_score,
            high_quality_count=high_count,
            medium_quality_count=medium_count,
            low_quality_count=low_count,
            total_issues=total_issues,
            total_recommendations=total_recs
        )
