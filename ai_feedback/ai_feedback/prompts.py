AUDIO_FEEDBACK_PROMPT = """I have provided some script details and an audio file.

The script details json contains the following fields:
- "question" - The question that should be answered in the audio answer
- "briefing" - The description of the educational module the student is taking part in.
It outlines what the questions will be about, their purpose and what skills the student
should have at the end.
- "keyElements" - a list of important aspects that have to be covered in the audio answer
Each "keyElement" has:
- a "script", which is a sentence whose meaning has to be part of the audio answer, in one way or another
- a list of "keywords", which need to be mentioned exactly as part of the audio answer, when talking
about this specific keyElement

In a section called "Feedback", Please analyze how closely the spoken content in the
audio aligns with the script, specifically assessing whether it covers the key
elements effectively and the language used is completely correct.

Create a markdown table with 3 columns:
- Key Element
- Issues identified
- Recording Matches (with options Yes/No/Partially)

For each "key element", the "recording matches" options should be assigned as follows:
- "Yes":
    - ALL of the "keywords" are EXPLICITLY MENTIONED EXACTLY
    - The meaning of the "script" is transmitted well
- "Partially":
    - ALL of the "keywords" are EXPLICITLY MENTIONED EXACTLY
    - The meaning of the "script" is partially transmitted or has errors
- "No":
    - AT LEAST ONE of the "keywords" is NOT EXPLICITLY MENTIONED EXACTLY
    - Other issues with following the "script" might also exist

Make sure you are strict about the word choice, formulation, clarity and conciseness.
Offer recommendations and corrections if necessary, especially if incorrect words or
ambiguous formulations are used.

Finally, at the end of your response, in a section called "Confidence
assesment", analyze and make some comments regarding the confidence level of
the person speaking and make some specific, actionable recommendations.

Important notes:
- You answer needs to be in markdown format
- In the "Issues Identified" column, explicitly mention the missing keywords
- In your answer, whenever you are referring to the keywords, bold them
- In your answer, whenever you are quoting from the audio, use italics
- Make sure the table is properly formatted and doesn't have any missing or extra columns or rows.
- In the "Recording Matches" column of the table:
    - The "Yes" option should be preceded by ✅
    - The "Partially" option should be preceded by ⚠️
    - The "No" option should be preceded by ❌
"""
