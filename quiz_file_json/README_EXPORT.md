# Quiz JSON Export System

## Overview

The Enhanced Quiz JSON Export System automatically exports AI-generated questions to JSON files with complete metadata matching the Neo4j database schema. This enables seamless data interchange, backup, and external system integration.

## Features

- **Three Export Formats**: Complete, Legacy, and Mapping formats
- **Automatic Export**: Integrated into the question generation pipeline
- **Complete Metadata**: Includes all Quiz and Choice properties from Neo4j models
- **Flexible Configuration**: Customizable output directory and format selection
- **Batch Export**: Export all formats at once

## Export Formats

### 1. Complete Format (Recommended)

Full metadata matching Neo4j schema with all Quiz and Choice properties.

**File naming**: `quiz_complete_{knowledge_name}_{session_id}_{timestamp}.json`

**Structure**:
```json
{
  "export_metadata": {
    "export_timestamp": "2025-01-15T10:30:00",
    "export_version": "1.0",
    "knowledge_name": "Adverbs of Frequency",
    "total_questions": 10,
    "average_validation_score": 0.92,
    "generation_session_id": "session123"
  },
  "questions": [
    {
      "id": "quiz_001",
      "quiz_text": "She is ___ for class.",
      "question_style": "fill_in_blank",
      "generation_metadata": {
        "created_at": "2025-01-15T10:30:00",
        "ai_model_used": "openai",
        "question_index": 1
      },
      "choices": [
        {
          "choice_letter": "A",
          "choice_text": "often late",
          "is_correct": true,
          "answer_explanation": "Correct! Adverb of frequency comes after be verb."
        },
        {
          "choice_letter": "B",
          "choice_text": "late often",
          "is_correct": false,
          "answer_explanation": "Wrong! Incorrect word order."
        }
      ],
      "knowledge_reference": {
        "name": "Adverbs of Frequency",
        "description": "Position of adverbs of frequency in sentences"
      }
    }
  ]
}
```

### 2. Legacy Format

Backward compatible with existing `example_quiz_file.json` format.

**File naming**: `quiz_legacy_{knowledge_name}_{timestamp}.json`

**Structure**:
```json
[
  {
    "question": "She is ___ for class.",
    "choices": [
      "often late",
      "late often",
      "is often",
      "often is late"
    ],
    "answer": "often late",
    "answer_description": "Correct! Adverb of frequency comes after be verb."
  }
]
```

### 3. Mapping Format

With knowledge ID mappings like `example_quiz_mapping_file.json`.

**File naming**: `quiz_mapping_{knowledge_name}_{timestamp}.json`

**Structure**:
```json
[
  {
    "question": "She is ___ for class.",
    "answer_description": "Correct! Adverb of frequency comes after be verb.",
    "question_knowledge_ids": [1, 2],
    "choices": [
      {
        "index": 1,
        "text": "often late",
        "knowledge_ids": [1],
        "is_correct": true
      },
      {
        "index": 2,
        "text": "late often",
        "knowledge_ids": [2],
        "is_correct": false
      }
    ]
  }
]
```

## Usage

### Command Line Interface

#### Basic Export (Complete Format)
```bash
python manage.py question_pipeline --export-json
```

#### Export with Specific Format
```bash
# Legacy format
python manage.py question_pipeline --export-json --export-format legacy

# Mapping format
python manage.py question_pipeline --export-json --export-format mapping

# All formats at once
python manage.py question_pipeline --export-json --export-format all
```

#### Custom Export Directory
```bash
python manage.py question_pipeline --export-json --export-dir /path/to/exports
```

#### Complete Example
```bash
python manage.py question_pipeline \
  --knowledge-id "AdverbsOfFrequency" \
  --style fill_in_blank \
  --count 10 \
  --export-json \
  --export-format complete \
  --export-dir quiz_file_json
```

#### Disable Export
```bash
python manage.py question_pipeline --no-export
```

### Programmatic Usage

```python
from quiz.services.json_export_service import JSONExportService
from quiz.models.export_data import ExportConfig, ExportFormat

# Create export service with custom config
config = ExportConfig(
    output_directory='quiz_file_json',
    create_subdirectories=True,
    pretty_print=True,
    indent=2
)
service = JSONExportService(config)

# Export in complete format
result = service.export_questions_complete(
    questions=questions,
    knowledge_node=knowledge,
    generation_result=generation_result,
    validation_result=validation_result
)

if result.success:
    print(f"Exported {result.questions_exported} questions")
    print(f"File: {result.file_path}")
    print(f"Size: {result.file_size_kb:.2f} KB")
else:
    print(f"Export failed: {result.error_message}")

# Export all formats
results = service.export_all_formats(
    questions=questions,
    knowledge_node=knowledge,
    generation_result=generation_result,
    validation_result=validation_result
)

for fmt, result in results.items():
    print(f"{fmt.value}: {result.file_path}")
```

## Configuration

### ExportConfig Options

```python
@dataclass
class ExportConfig:
    format: ExportFormat = ExportFormat.COMPLETE
    output_directory: str = "quiz_file_json"
    create_subdirectories: bool = True  # Create format-specific subdirectories
    pretty_print: bool = True           # Format JSON with indentation
    indent: int = 2                     # Indentation spaces
    ensure_ascii: bool = False          # Allow Unicode characters
```

## File Organization

When `create_subdirectories=True` (default):

```
quiz_file_json/
├── complete/
│   ├── quiz_complete_AdverbsOfFrequency_session123_20250115_103000.json
│   └── quiz_complete_PresentSimple_session124_20250115_110000.json
├── legacy/
│   ├── quiz_legacy_AdverbsOfFrequency_20250115_103000.json
│   └── quiz_legacy_PresentSimple_20250115_110000.json
└── mapping/
    ├── quiz_mapping_AdverbsOfFrequency_20250115_103000.json
    └── quiz_mapping_PresentSimple_20250115_110000.json
```

When `create_subdirectories=False`:

```
quiz_file_json/
├── quiz_complete_AdverbsOfFrequency_session123_20250115_103000.json
├── quiz_legacy_AdverbsOfFrequency_20250115_103000.json
└── quiz_mapping_AdverbsOfFrequency_20250115_103000.json
```

## Pipeline Integration

The export system is fully integrated into the Question Management Pipeline:

1. **Step 1-4**: Generate and validate questions
2. **Step 5**: Review results
   - User approves questions
   - Questions saved to Neo4j database
   - **Automatic JSON export** (if `--export-json` flag is set)
3. Display export results

## Output Example

```
✅ Questions approved and saved to Neo4j database!

📤 Exporting questions to complete format...
  ✅ Exported 10 questions
  📁 File: quiz_file_json/complete/quiz_complete_AdverbsOfFrequency_session123_20250115_103000.json
  📊 Size: 45.67 KB

🎉 Pipeline completed successfully!

📈 Final Statistics:
   Knowledge Node: Adverbs of Frequency
   Question Style: fill_in_blank
   Questions Generated: 10/10
   Average Validation Score: 0.92/1.0
   Pipeline Time: 45.2s

💾 Neo4j Database:
   Status: ✅ Successfully saved to database
   Questions Saved: 10
   Session ID: session123

📤 JSON Export:
   ✅ Complete: 10 questions
      File: quiz_file_json/complete/quiz_complete_AdverbsOfFrequency_session123_20250115_103000.json
      Size: 45.67 KB
```

## Testing

Run the test suite:

```bash
python manage.py test quiz.tests.test_json_export_service
```

## Troubleshooting

### Export Failed: Permission Denied
- Check write permissions for the output directory
- Ensure the directory exists or can be created

### Export Failed: Invalid Format
- Use one of: `complete`, `legacy`, `mapping`, `all`
- Check command line arguments

### File Not Found
- Verify the export was successful (check for success message)
- Check the output directory path
- Ensure `create_subdirectories` setting matches your expectation

## Best Practices

1. **Use Complete Format** for new integrations (most comprehensive)
2. **Use Legacy Format** for backward compatibility with existing systems
3. **Use Mapping Format** when you need knowledge ID references
4. **Export All Formats** for maximum flexibility
5. **Enable Subdirectories** for better organization with multiple exports
6. **Review Export Results** in the pipeline output to confirm success

## Future Enhancements

- [ ] Compression support (gzip)
- [ ] Custom filename templates
- [ ] Export filtering (by validation score, style, etc.)
- [ ] Incremental exports (only new questions)
- [ ] Export to other formats (CSV, XML, YAML)
- [ ] Cloud storage integration (S3, GCS)
- [ ] Export scheduling and automation

