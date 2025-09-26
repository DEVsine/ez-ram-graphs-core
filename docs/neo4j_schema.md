# Neo4j Schema

## Knowledge

**field**

- description: "Learners often misuse time expressions, auxiliaries, and participles with the present perfect. Awareness prevents systematic mistakes."
- example: "I have went (incorrect) → I have gone (correct)."
- name: "Common Errors"

**relationship**

- depends_on -> Knowledge (self)

## Quiz

**field**

- quiz_text: "She is \_\_\_ for class."

**relationship**

- has_choice -> Choice
- related_to -> Knowledge

## Choice

**field**

- question_id: string
- choice_text: string
- is_correct: bool
- answer_explanation: string

**relationship**

- related_to -> Knowledge
