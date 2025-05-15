COACHING_RECOMMENDATIONS_PROMPTS = {
    True: {
        "coaching_column_mention": "- Coaching Recommendations",
        "table_example": """
| **Key Elements**                                     | **Recording matches** |   **Score** | **Coaching Recommendations** |
|-----------------------------------------------------|--------------|-----------|-------------------|
| - **understand**, **the prospect**, **needs**              | ✅ Yes       | 100% | The prospect's scenario is correctly introduced (Chris moving from Glasgow and comparing banks). |
| - **confidently**, **differentiate**, **Bank A**, **Bank B**  | ⚠️ Partially | 75% | There is an error in the sentence: “confidentially differentiate Bank A from Bank B & emphasizing...”. The word “confidentially” should be “confidently.” Also, the structure of the sentence is unclear. |
| - **showcase**, **Bank B**, **premium customer experience** | ✅ Yes       | 100% | Mention of relationship management and 24/7 support is present. However, wording is awkward: “showcase premium experience including relationship management and 24-7.” It should be “showcase Bank A’s premium customer experience, including relationship managers and 24/7 support.” |
| - **guide the prospect**, **toward**, **making an informed decison**    | ✅ Yes       | 100% | The final section about onboarding and making a decision is included, but the sentence is awkward: “making an informed decision to open a brand new account with Bank A.” A smoother transition would improve clarity. |
---
""",
        "coaching_column_instructions": """
- NEVER mention brand names or commercial entities other than the ones provided as part of this conversation
- Each recommendation you make should be SPECIFIC and ACTIONABLE. Don't make any generic recommendations
- Do not refer to the audio or the student, just to the quality and assesment of the recording.
- Instead of making a suggestion like "Incorporate real-world examples to illustrate the benefits of X", give
a specific example like "X proves useful when you are at the gas station and you forgot your credit card in the car".
- Regarding word choice, use clear and professional terms, try to avoid artistic or overly
abstract words (e.g. instead of "palpable" use terms like "clear", "noticeable", "real" or "strong")
- In your answer, whenever you are quoting from the audio, use italics
- In the "Coaching Recommendations" column:
    - Analyze how closely the spoken content in the audio aligns with the script, 
    specifically assessing whether it covers the key elements effectively and the
    language used is completely correct
    - make sure you are strict about the word choice, formulation, clarity and conciseness.
    - Offer recommendations and corrections if necessary, especially if incorrect words,
    misspellings or ambiguous formulations are used.
    - Emphasize the missing keywords
    - Make sure to pay special attention, mention and emphasize mispronounced words
    - In your answer, whenever you are referring to the keywords, bold them
    - Don't only mention the missing keywords, EXPLAIN for each of them why that specific wording is essential,
    based on the information from the briefing and the best industry practices""",
    },
    False: {
        "coaching_column_mention": "",
        "table_example": """
| **Key Elements**                                    | **Recording matches** |   **Score** |
|-----------------------------------------------------|-----------------------|-------------|
| - **understand**, **the prospect**, **needs**              | ✅ Yes       | 100% |
| - **confidently**, **differentiate**, **Bank A**, **Bank B**  | ⚠️ Partially | 75% |
| - **showcase**, **Bank B**, **premium customer experience** | ✅ Yes       | 100% |
| - **guide the prospect**, **toward**, **making an informed decison**    | ✅ Yes       | 100% |
---
""",
        "coaching_column_instructions": "- Only output the table and nothing else",
    },
}
