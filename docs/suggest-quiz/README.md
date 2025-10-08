# Suggest Quiz Feature Documentation

> **Quick Navigation**: Start with [INDEX.md](INDEX.md) for a comprehensive overview.

## 📚 Documentation Files

### Core Documentation

- **[INDEX.md](INDEX.md)** - Complete feature overview, quick start, and navigation hub
- **[REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)** - Summary of 2025-10-08 refactoring

### Requirements

- **[suggest-quiz-requirements.md](requirements/suggest-quiz-requirements.md)** - Functional and non-functional requirements

### Design

- **[suggest-quiz-design-2025-10-08.md](design/suggest-quiz-design-2025-10-08.md)** - Architecture and detailed design

### ADRs (Architecture Decision Records)

- **[0001-weakness-based-quiz-suggestion.md](adr/0001-weakness-based-quiz-suggestion.md)** - Decision to use weakness-based approach

### Testing

- ⏳ Test plans and acceptance criteria (to be added)

---

## 🚀 Quick Start

### API Request Example

```bash
curl -X POST http://localhost:8000/student/v1/RAM1111/suggest-quiz/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student": {
      "username": "ceo",
      "id": "123-ceo"
    },
    "quiz_limit": 5,
    "scope_topic": "Simple Tense"
  }'
```

### Code Location

- **Service**: `student/services/suggest_quiz_service.py`
- **View**: `student/api_views.py` → `SuggestQuizAPI`
- **URL**: `student/urls.py`

---

## 📖 How to Use This Documentation

### For Developers

1. **Understanding the Feature**: Start with [INDEX.md](INDEX.md)
2. **Implementation Details**: Read [Design Document](design/suggest-quiz-design-2025-10-08.md)
3. **Requirements**: Check [Requirements Document](requirements/suggest-quiz-requirements.md)
4. **Decision Context**: Review [ADR 0001](adr/0001-weakness-based-quiz-suggestion.md)

### For Product Managers

1. **Feature Overview**: [INDEX.md](INDEX.md) - Quick Start section
2. **Requirements**: [Requirements Document](requirements/suggest-quiz-requirements.md)
3. **Change History**: [INDEX.md](INDEX.md) - Change History section

### For QA/Testers

1. **Test Requirements**: [Requirements Document](requirements/suggest-quiz-requirements.md) - Testing Requirements section
2. **Test Strategy**: [Design Document](design/suggest-quiz-design-2025-10-08.md) - Testing Strategy section
3. **Edge Cases**: [Requirements Document](requirements/suggest-quiz-requirements.md) - Edge Cases

---

## 🔄 Document Lifecycle

### Status Indicators

- ✅ **Approved**: Document is current and accurate
- 🔄 **In Review**: Document is being reviewed
- ⏳ **Draft**: Document is work in progress
- 🗄️ **Archived**: Document is outdated (moved to `/archive`)

### Last Validated

All documents in this folder were last validated on **2025-10-08**.

---

## 🔗 Related Features

- **[Submit Answer](../submit-answer/INDEX.md)**: Updates student knowledge scores
- **Get Student Graph**: Visualizes student knowledge progress

---

## 📞 Support

For questions or issues:
1. Check [INDEX.md](INDEX.md)
2. Review [ADR 0001](adr/0001-weakness-based-quiz-suggestion.md)
3. Check code comments in `student/services/suggest_quiz_service.py`
4. Contact feature owner: @ceofourfactplus

---

**Last Updated**: 2025-10-08  
**Status**: ✅ Active  
**Version**: 2.0 (Weakness-Based)

