AUDIO_FEEDBACK_PROMPT = """I have provided a script file and an audio file. The script
includes a 'Key Elements' section, which serves as a benchmark for evaluation.
The rest of the script outlines the information that should be conveyed in the
conversation.  The audio file contains a spoken version of this content. In a
section called "Feedback", Please analyze how closely the spoken content in the
audio aligns with the script, specifically assessing whether it covers the key
elements effectively and the language used completely correct.

Create a table with 3 columns:
- Key Element
- Recording Matches (with options Yes/No/Partially)
- Issues identified

Make sure you are strict about the word choice, formulation, clarity and conciseness.
Offer recommendations and corrections if necessary, especially if incorrect words or
ambiguous formulations are used.
Make sure the table is properly formatted and doesn't have any missing or extra columns
or rows.

Finally, at the end of your response, in a section called "Confidence
assesment", analyze and make some comments regarding the confidence level of
the person speaking and make some specific, actionable recommendations.
"""
