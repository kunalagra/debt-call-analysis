# Debt Collection Call Analysis Tool

## Project Overview

This project analyzes debt collection call transcripts (provided as JSON files) to evaluate agent compliance, professionalism, and call quality metrics. It implements and compares different approaches (Pattern Matching Regex, Large Language Models) for detecting specific events like profanity usage and potential privacy violations. The results are presented through an interactive Streamlit application.

## Features

*   **Profanity Detection:** Identifies calls where agents or borrowers used profane language using:
    *   Regex-based keyword matching.
    *   LLM (Google Gemini) analysis for contextual understanding.
*   **Privacy & Compliance Violation Detection:** Detects potential instances where agents shared sensitive information (e.g., balance, account details) *before* completing identity verification, using:
    *   Regex-based heuristics looking for verification and sensitive keywords in sequence.
    *   LLM (Google Gemini) analysis assessing the conversational flow for violations.
*   **Call Quality Metrics:** Calculates per-call metrics:
    *   **Overtalk Percentage:** Time duration where both agent and borrower were speaking simultaneously.
    *   **Silence Percentage:** Time duration where neither agent nor borrower was speaking.
    *   **Total Duration:** Overall length of the conversation.
*   **Multiple Analysis Approaches:** Implements both traditional pattern matching (Regex) and modern AI (LLM) techniques for comparative analysis.
*   **Interactive Streamlit UI:**
    *   Analyze single JSON call files via upload.
    *   Analyze all JSON files within a specified directory (Batch Mode).
    *   Select analysis type (Profanity, Privacy Violation).
    *   Select analysis approach (Regex, LLM).
    *   Visualize call metrics for single calls and aggregated batch results.
*   **Modular Code Structure:** Organized code for better readability, maintainability, and potential reuse.

## Project Structure

```
debt-call-analysis/
├── app.py                  # Main Streamlit application UI
├── config.py               # Configuration, constants, API keys (env), regex patterns
├── data_loader.py          # Data loading and parsing logic (JSON -> DataFrame)
├── batch_processor.py      # Orchestrates analysis for multiple files
├── analysis/
│   ├── __init__.py         # Makes 'analysis' a Python package
│   ├── regex_analyzer.py   # Regex-based detection functions
│   ├── llm_analyzer.py     # LLM (Google Gemini) based detection functions & client setup
│   └── metrics_analyzer.py # Overtalk and silence calculation functions
├── requirements.txt        # Python package dependencies
└── README.md               # This file
└── All_Conversations.zip   # Zip File of the Data

```

*(Note: The original assignment mentioned YAML files. This implementation uses JSON as per the provided Dataset)*

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd your_project_directory
    ```
2. **Use uv (Recommended):**
    ```bash
    uv sync
    uv run streamlit run app.py
    ```
###        OR 

2.  **Use pip:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    streamlit run app.py
    ```

## Configuration

*   **LLM Analysis (Google Gemini):**
    *   This feature requires a Google API Key enabled for the Gemini API (Generative Language API).
    *   **Recommended:** Store your API key using Streamlit Secrets. Create a file named `.streamlit/secrets.toml` in your project's root directory with the following content:
        ```toml
        GOOGLE_API_KEY = "YOUR_ACTUAL_GOOGLE_API_KEY"
        ```
    *   **Alternative:** Set the API key as an environment variable named `GOOGLE_API_KEY`. The application will check for secrets first, then this environment variable.
    *   If no API key is found or the `google-generativeai` library is not installed, the LLM approach option will be disabled or show an error in the Streamlit sidebar.

## Usage



*   **Select Mode (Sidebar):** Choose between "Analyze Single File" or "Analyze Directory (Batch)".
*   **Single File Mode:**
    *   Use the "Upload call transcript (JSON)" button to select a file.
    *   Choose the "Analysis Type" (Profanity or Privacy).
    *   Choose the "Approach" (Regex or LLM, if configured).
    *   Click "Analyze Call".
    *   Results (flags/metrics/visuals) will be displayed on the main page.
*   **Batch Mode:**
    *   Enter the path to the directory containing your JSON files in the "Directory Path" input field (defaults to `All_Conversations`).
    *   Click "Run Batch Analysis".
    *   A progress bar will show the analysis status.
    *   A summary table, aggregate statistics, and metric distribution plots will be displayed upon completion. Error summaries (if any) are available in an expander.



## Future Work / Potential Improvements

*   **YAML Input Support:** Modify `data_loader.py` to directly parse YAML files if needed.
*   **Model Switching:** Use different models or Unified solutions to easily use Models from any provider
*   **Enhanced Regex:** Develop more sophisticated regex patterns to handle variations and reduce false positives/negatives.
*   **Alternative ML:** Implement and compare a fine-tuned classification model (e.g., using BERT or similar) for profanity/privacy detection as an alternative ML approach.
*   **Error Handling:** Provide more granular error details in the UI for specific file failures during batch processing.
*   **Advanced Metrics:** Incorporate additional metrics like sentiment analysis, talk ratio, or speech rate.
*   **User Authentication:** Add user login if deploying in a shared environment.
*   **Configuration File:** Move more settings (like speaker IDs, model names) from `config.py` to a separate configuration file (e.g., YAML/JSON) for easier modification.

## License

This project is licensed under the AGPL License.
