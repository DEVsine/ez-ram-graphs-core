# Quick Start: JSON Export System

## 🚀 Get Started in 3 Steps

### Step 1: Run the Pipeline with Export Enabled

```bash
python manage.py question_pipeline --export-json
```

This will:
1. Guide you through the question generation pipeline
2. Save approved questions to Neo4j database
3. **Automatically export to JSON** in complete format

### Step 2: Check Your Exported Files

```bash
ls -lh quiz_file_json/complete/
```

You should see a file like:
```
quiz_complete_AdverbsOfFrequency_session123_20250115_103000.json
```

### Step 3: View the Exported JSON

```bash
cat quiz_file_json/complete/quiz_complete_*.json | jq .
```

Or open it in your favorite text editor!

---

## 📋 Common Use Cases

### Export in All Formats

```bash
python manage.py question_pipeline --export-json --export-format all
```

This creates three files:
- `quiz_file_json/complete/quiz_complete_*.json` - Full metadata
- `quiz_file_json/legacy/quiz_legacy_*.json` - Backward compatible
- `quiz_file_json/mapping/quiz_mapping_*.json` - With knowledge IDs

### Generate 20 Questions and Export

```bash
python manage.py question_pipeline \
  --count 20 \
  --export-json \
  --export-format complete
```

### Auto-Approve and Export

```bash
python manage.py question_pipeline \
  --auto \
  --count 10 \
  --export-json
```

Questions with validation score ≥ 0.8 will be auto-approved and exported.

### Export to Custom Directory

```bash
python manage.py question_pipeline \
  --export-json \
  --export-dir /path/to/my/exports
```

---

## 🎯 What Gets Exported?

### Complete Format (Default)

```json
{
  "export_metadata": {
    "export_timestamp": "2025-01-15T10:30:00",
    "knowledge_name": "Adverbs of Frequency",
    "total_questions": 10,
    "average_validation_score": 0.92
  },
  "questions": [
    {
      "id": "quiz_001",
      "quiz_text": "She is ___ for class.",
      "question_style": "fill_in_blank",
      "choices": [
        {
          "choice_letter": "A",
          "choice_text": "often late",
          "is_correct": true,
          "answer_explanation": "Correct! Adverb after be verb."
        }
      ]
    }
  ]
}
```

### Legacy Format

```json
[
  {
    "question": "She is ___ for class.",
    "choices": ["often late", "late often", "is often", "often is late"],
    "answer": "often late",
    "answer_description": "Correct! Adverb after be verb."
  }
]
```

---

## ✅ Verify It Works

### Run Tests

```bash
python manage.py test quiz.tests.test_json_export_service
```

Expected output:
```
........
----------------------------------------------------------------------
Ran 8 tests in 0.123s

OK
```

### Check Pipeline Output

Look for this in the output:

```
📤 Exporting questions to complete format...
  ✅ Exported 10 questions
  📁 File: quiz_file_json/complete/quiz_complete_AdverbsOfFrequency_session123_20250115_103000.json
  📊 Size: 45.67 KB
```

---

## 🔧 Troubleshooting

### "Export failed: Permission denied"

**Solution**: Check directory permissions
```bash
chmod 755 quiz_file_json
```

### "No such file or directory"

**Solution**: Create the directory
```bash
mkdir -p quiz_file_json
```

### Export not happening

**Solution**: Make sure you used `--export-json` flag
```bash
python manage.py question_pipeline --export-json
```

---

## 📚 Learn More

- **Full Documentation**: See `quiz_file_json/README_EXPORT.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **Test Suite**: See `quiz/tests/test_json_export_service.py`

---

## 💡 Pro Tips

1. **Use `--export-format all`** to get all three formats at once
2. **Check file size** to ensure export completed successfully
3. **Use `jq` tool** to pretty-print and query JSON files
4. **Enable auto mode** (`--auto`) for batch processing
5. **Review export results** in the pipeline output

---

## 🎉 That's It!

You're now ready to use the Enhanced Quiz JSON Export System!

**Next Steps**:
- Generate some questions and export them
- Integrate the JSON files with your application
- Customize the export configuration as needed

Happy exporting! 🚀

