# Meridian AI Challenge -- Solution Write-up

## 1. What I built

I developed an AI-powered Adviser Notes Assistant that converts
financial advisers' meeting notes and voice recordings into structured
draft investment proposals.

The solution supports typed notes and audio uploads. Audio is
transcribed using Google Gemini, allowing the adviser to review and
correct the transcript before generating a proposal.

The extracted information is then validated against the provided JSON
schema and loaded into the existing Meridian proposal generator.

## 2. Why I chose this approach

I chose to extend the existing Meridian proposal generator rather than
replace it.

This preserves the existing proposal workflow and allows the AI
assistant to focus on reducing manual data entry, interpreting
unstructured adviser notes and preparing an initial proposal for review.

## 3. Key design decisions

-   Used Gemini for audio transcription and structured information
    extraction.
-   Used Flask to connect the assistant interface with the AI processing
    logic.
-   Used JSON Schema validation to check the generated proposal
    structure.
-   Preserved the existing Meridian generator and integrated through its
    proposal-loading function.
-   Designed the workflow to allow human review before a proposal is
    finalised.

## 4. Assumptions and limitations

The solution assumes that advisers provide meeting notes containing
relevant client and investment information.

Missing information should remain unpopulated rather than being
invented. Ambiguous details, including possible joint-client
arrangements, should be confirmed by a human reviewer.

The existing generator may populate practice-level defaults, such as
certain fees. These must be distinguished from information extracted
from adviser notes.

The current prototype supports audio-file uploads rather than live
microphone recording.

## 5. Testing

I tested the solution using four fictional challenge examples:

1.  Retirement income planning.
2.  Offshore growth and family trust investment.
3.  Sparse adviser notes with missing information.
4.  Voice-note transcript containing a bespoke investment strategy.

I also tested an actual M4A audio upload through transcription and
proposal generation.

The tests demonstrated that the assistant could extract key client and
investment details, preserve missing values and load structured
proposals into the existing generator.

## 6. Recommended future improvements

-   Display the source of every field, distinguishing adviser-provided
    information, AI inference and practice defaults.
-   Provide a dedicated panel for missing information and follow-up
    questions.
-   Improve detection and confirmation of joint-client arrangements.
-   Add automated regression tests for extraction accuracy.
-   Introduce authentication, audit logging and stronger privacy
    controls before production deployment.

## Conclusion

The prototype demonstrates how AI can reduce the administrative effort
involved in preparing investment proposals while retaining the existing
Meridian workflow and human oversight.

It provides a foundation for a more efficient, traceable and reviewable
proposal preparation process.
