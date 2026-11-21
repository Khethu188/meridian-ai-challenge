# Meridian Adviser Notes Assistant

An AI-powered prototype that converts financial-adviser meeting notes or
an uploaded voice recording into a draft investment proposal in the
existing Meridian proposal generator.

The prototype is designed for the Meridian AI Engineer challenge. It
uses fictional sample data only.

## What it does

1.  Accepts typed or pasted adviser notes.
2.  Accepts an audio-file upload (MP3, WAV, M4A, AAC, OGG, WEBM or FLAC;
    maximum 20 MB).
3.  Uses Gemini to transcribe uploaded audio and displays the transcript
    so the user can review or correct it.
4.  Sends the notes or reviewed transcript to a Gemini extraction agent.
5.  Extracts proposal details into the structure defined by
    `schema.json`.
6.  Validates the generated object against the JSON Schema.
7.  Loads the proposal into the existing Meridian generator using its
    `window.loadProposal(...)` function.
8.  Leaves the draft open for a human reviewer to check and complete.

## Technology

-   **Python** for the extraction and server-side logic.
-   **Flask** for the local web application and API endpoints.
-   **Google Gemini (`gemini-3.5-flash-lite`)** for audio transcription
    and structured information extraction.
-   **JSON Schema (`jsonschema`)** for output validation.
-   **HTML, CSS and JavaScript** for the assistant interface.
-   **Existing Meridian proposal generator** embedded in the assistant
    page.

## Project structure

``` text
meridian-ai-challenge/
├── assistant.html             # Notes/audio interface and embedded proposal generator
├── challenge-generator.html   # Existing Meridian proposal generator
├── server.py                  # Flask application and API endpoints
├── agent.py                   # Gemini extraction, mapping and validation
├── schema.json                # Machine-readable proposal schema
├── proposal-schema.md          # Human-readable proposal data-model reference
├── sample-inputs/              # Fictional adviser-note test cases and expected outputs
├── .env                        # Local API key; do not commit this file
├── .gitignore
└── README.md
```

## Requirements

-   Python 3.10 or later
-   A Google Gemini API key
-   Internet access for Gemini API calls
-   A modern browser

Install the dependencies from PowerShell in the project directory:

``` powershell
python -m pip install flask python-dotenv google-genai jsonschema
```

## Configuration

Create a file named `.env` in the project root and add your Gemini API
key:

``` text
GEMINI_API_KEY=your_gemini_api_key
```

Keep the real key private. Do not paste it into source code,
screenshots, the README, or a public repository. Ensure `.env` is listed
in `.gitignore`.

## Run the application

From the project directory:

``` powershell
python server.py
```

Open the local assistant in your browser:

``` text
http://127.0.0.1:5000
```

The application runs locally. Gemini API requests require an internet
connection and a valid API key.

## How to use it

### Typed notes

1.  Open the assistant page.
2.  Paste or type the adviser's notes into the notes box.
3.  Select **Generate draft proposal**.
4.  Wait for the extracted proposal to load in the embedded Meridian
    generator.
5.  Review the generated fields and correct or complete them before
    using the proposal.

### Voice recording

1.  Select an audio file using **Upload voice recording**.
2.  Select **Transcribe recording**.
3.  Read and correct the transcript in the notes box. Pay particular
    attention to client names, amounts, currencies, fees, dates and
    investment horizons.
4.  Select **Generate draft proposal**.
5.  Review the resulting draft in the Meridian generator.

Audio upload is supported; live microphone recording is not implemented
in this prototype.

## Application endpoints

  -----------------------------------------------------------------------
  Endpoint                Method                  Purpose
  ----------------------- ----------------------- -----------------------
  `/`                     GET                     Serves the adviser
                                                  assistant interface

  `/generator`            GET                     Serves the existing
                                                  Meridian proposal
                                                  generator

  `/transcribe`           POST                    Accepts an audio file
                                                  and returns a
                                                  transcript

  `/extract`              POST                    Accepts adviser notes
                                                  as JSON and returns a
                                                  schema-validated
                                                  proposal object
  -----------------------------------------------------------------------

The `/extract` endpoint expects a JSON body with a `notes` string. The
`/transcribe` endpoint expects a multipart form upload with the field
name `audio`.

## Design decisions and safeguards

-   **Use the existing proposal generator:** The prototype integrates
    with the generator's documented
    `window.loadProposal(proposalObject)` interface rather than
    replacing the proposal workflow.
-   **Structured extraction:** The agent asks Gemini to return a
    proposal-shaped JSON object and validates it against `schema.json`
    before returning it to the browser.
-   **Avoid fabricated financial facts:** The extraction instructions
    tell the model to omit unknown values and not invent investment
    amounts, fees, benchmarks, holdings or asset-allocation percentages.
-   **Preserve uncertainty:** Incomplete or ambiguous information should
    remain absent or be described as requiring confirmation. The
    reviewer must resolve gaps before a proposal is treated as final.
-   **Human review:** The transcript is shown before proposal
    generation, and the generated proposal remains editable in the
    existing tool.
-   **Audio upload limit:** The server enforces a 20 MB maximum upload
    size and accepts common audio formats.
-   **Fictional data:** The included challenge examples are synthetic.
    Do not use real client information in this prototype.

## Testing

The four supplied sample cases were exercised through the browser
workflow:

-   `01-notes-retiree-income.txt` --- retirement income and investment
    objective.
-   `02-notes-growth-offshore.txt` --- offshore growth and trust-related
    details.
-   `03-notes-sparse.txt` --- incomplete notes and missing information.
-   `04-voice-note-transcript.txt` --- voice-note transcript, bespoke
    strategy and possible joint-client details.

An additional end-to-end audio test confirmed that an uploaded M4A
recording could be transcribed, reviewed and passed into proposal
generation.

Testing confirmed that key details such as client type, investment
amount, currency, investment horizon, strategy and stated adviser fee
could be mapped into the generator. The sparse-notes case also showed
that unknown investment amount and horizon values could remain blank
rather than being filled with invented figures.

## Known limitations and next steps

-   **Review generator defaults:** The existing Meridian generator may
    pre-fill practice-level fees or other defaults. These must not be
    mistaken for values extracted from adviser notes. The reviewer
    should verify every fee and distinguish source-provided facts from
    inherited defaults.
-   **Make provenance more visible:** A next iteration should label each
    populated field as adviser-provided, AI-inferred, practice default
    or awaiting confirmation, with a reference to the source note or
    transcript.
-   **Improve clarification workflow:** Present missing information and
    follow-up questions in a dedicated review panel, allowing the
    adviser or portfolio manager to resolve them before finalising the
    proposal.
-   **Handle joint clients explicitly:** Detect possible joint-client
    language and request confirmation of all client names and the
    correct client arrangement.
-   **Improve extraction tests:** Add automated regression tests
    comparing model output with expected values, including ambiguous
    names, amounts, currencies, fees and horizons.
-   **Production readiness:** Add authentication, secure secret
    management, audit logging, privacy controls, rate limiting and
    deployment configuration before handling any real client data.
-   **Voice experience:** Consider live microphone recording and a
    clearer transcript-editing step if the product requires them.

## Important

This is an assessment prototype, not a financial-advice system. It
creates a draft for human review and does not approve, recommend or
execute investments. All generated information must be checked by an
authorised professional before use.
