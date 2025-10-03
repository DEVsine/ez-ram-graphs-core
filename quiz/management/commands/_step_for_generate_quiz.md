# Step for Generate Quiz

0. Create Folder for Knowledge example RAM1111 in `./subject/RAM1111`
1. Export Knowledge graph from Neo4j to a JSON file in a hierarchical format, starting from a specified TopicKnowledge node `RAM1111` to `./subject/RAM1111/knowledge_graph.json`.

```bash
python manage.py export_knowledge_graph "RAM1111" --output ./subject/RAM1111/knowledge_graph.json
```

2. Select Quiz file in format `RAM1111/quiz_{topic_knowledge}.json`

```json
[
  {
    "question": "Do you like pizza? Yes, I ___.",
    "choices": [
      "do",
      "does",
      "am",
      "did"
    ],
    "answer": "do",
    "answer_description": "คำตอบ 'do' เพราะคำตอบ (Short Answer) ต้องใช้กริยาช่วย 'do' ในคำถาม เช่น Do you…? → Yes, I do."
  },
  ...
]
```

3. Run the command to generate quizzes and link them to the knowledge graph.

```bash
python manage.py generate_quiz_from_json \
    --knowledge-graph-json RAM1111/knowledge_graph.json \
    --quiz-json RAM1111/quiz_{topic_knowledge}.json \
    --output ./subject/RAM1111/knowledge_map_quiz/qmk_{topic_knowledge}.json
```

export format

```json
[
  {
    "quiz_text": "Do you like pizza? Yes, I ___.",
    "choices": [
      {
        "choice_text": "do",
        "is_correct": true,
        "answer_explanation": "คำตอบ 'do' เพราะคำตอบ (Short Answer) ต้องใช้กริยาช่วย 'do' ในคำถาม เช่น Do you…? → Yes, I do.",
        "related_to": [
            {
                "graph_id": "4:abc123:456",
                "knowledge": "Short Answers"
            },
            {
                "graph_id": "4:def456:789",
                "knowledge": "Yes/No Questions"
            },
            {
                "graph_id": "4:ghi789:012",
                "knowledge": "Do/Does"
            }
        ]
      },
    ]
    "related_to": [
      {
        "graph_id": "4:abc123:456",
        "knowledge": "Short Answers"
      },
      {
        "graph_id": "4:def456:789",
        "knowledge": "Yes/No Questions"
      },
      {
        "graph_id": "4:ghi789:012",
        "knowledge": "Do/Does"
      }
    ]
  },
  ...
]
```

4. Import quizzes to Neo4j. let preview before import or use `--force` to skip preview

```bash
Let Verify Quiz before import (1/10)
Quiz: Do you like pizza? Yes, I ___. (Knowledge: Short Answers, Yes/No Questions, Do/Does)
Choice: do (correct) (Knowledge: Short Answers, Yes/No Questions, Do/Does)
Choice: does (wrong) (Knowledge: Short Answers, Yes/No Questions, Do/Does)
Choice: am (wrong) (Knowledge: Short Answers, Yes/No Questions, Do/Does)
Choice: did (wrong) (Knowledge: Short Answers, Yes/No Questions, Do/Does)
do you want to submit? (y/n)
```

```bash
python manage.py import_quiz_json_to_neo4j ./subject/RAM1111/knowledge_map_quiz/qmk_{topic_knowledge}.json --force
```
