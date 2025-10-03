from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExportFormat(Enum):
    """Enumeration of supported export formats"""
    COMPLETE = "complete"
    LEGACY = "legacy"
    MAPPING = "mapping"


@dataclass
class ExportConfig:
    """Configuration for JSON export"""
    format: ExportFormat = ExportFormat.COMPLETE
    output_directory: str = "quiz_file_json"
    include_metadata: bool = True
    pretty_print: bool = True
    indent: int = 2
    ensure_ascii: bool = False  # Support Thai characters
    filename_prefix: Optional[str] = None
    create_subdirectories: bool = True
    
    def __post_init__(self):
        """Validate configuration"""
        if self.indent < 0:
            raise ValueError("Indent must be non-negative")
        
        if not self.output_directory:
            raise ValueError("Output directory cannot be empty")


@dataclass
class ExportResult:
    """Result of a JSON export operation"""
    success: bool
    file_path: str
    questions_exported: int
    export_format: ExportFormat
    file_size_bytes: int = 0
    error_message: Optional[str] = None

    @property
    def file_size_kb(self) -> float:
        """Get file size in kilobytes"""
        return self.file_size_bytes / 1024.0
    
    @property
    def file_size_kb(self) -> float:
        """Get file size in KB"""
        return self.file_size_bytes / 1024
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB"""
        return self.file_size_bytes / (1024 * 1024)
    
    def __str__(self) -> str:
        """String representation"""
        if self.success:
            return (f"Export successful: {self.questions_exported} questions "
                   f"exported to {self.file_path} ({self.file_size_kb:.2f} KB)")
        else:
            return f"Export failed: {self.error_message}"

