import logging
import time
import json
import os
from typing import Tuple, Optional, List, Dict, Any

import pandas as pd
from pydantic import BaseModel, ValidationError
import streamlit as st # Needed for caching and secrets

# Attempt to import Google GenAI libraries
try:
    from google import genai
    from google.genai import types
    from google.api_core import exceptions as google_api_exceptions
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    google_api_exceptions = None
    GENAI_AVAILABLE = False
    logging.warning("`google-generativeai` library not installed. LLM features will be unavailable.")
    # UI warnings should be handled in app.py based on GENAI_AVAILABLE

# Import constants from config
from config import (
    GEMINI_MODEL_NAME,
    AGENT_SPEAKER_ID,
    BORROWER_SPEAKER_ID
    # GOOGLE_API_KEY is loaded from config, but secrets take precedence
)

# --- Pydantic Models for Response Validation ---
class ProfanityResult(BaseModel):
    agent_profanity: str
    borrower_profanity: str

class PrivacyResult(BaseModel):
    agent_violation: str

# --- Default LLM Settings ---
DEFAULT_SAFETY_SETTINGS = (
    [
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    ]
    if types # Only define if types module was imported
    else []
)

# --- GenAI Client Initialization (Cached) ---
@st.cache_resource(show_spinner="Connecting to Google GenAI...")
def get_genai_client():
    """Initializes and returns the Google GenAI client, cached per session."""
    if not GENAI_AVAILABLE:
        logging.error("Attempted to get GenAI client, but library is not available.")
        return None

    client = None
    # Prioritize Streamlit secrets, then environment variable
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if api_key:
        try:
            logging.info("Attempting to initialize Google GenAI Client...")

            client = genai.Client(api_key=api_key)



            # Basic verification (optional, might consume quota)
            # _ = client.generate_content("test", generation_config=types.GenerationConfig(max_output_tokens=5))
            logging.info("Google GenAI Client appears initialized.")
            return client # Return the model instance directly or a client object if needed
        except Exception as e:
            logging.error(f"Failed to initialize Google GenAI client/model: {e}", exc_info=True)
            # Let the caller handle UI error reporting
            return None
    else:
        logging.warning("Google API Key not found in Streamlit Secrets or environment variables.")
        # Let the caller handle UI error reporting
        return None

# --- LLM Helper Functions ---
def _format_transcript_for_llm(call_df: pd.DataFrame) -> str:
    """Formats the DataFrame transcript into a string for the LLM prompt."""
    if call_df is None or call_df.empty:
        return ""
    transcript = []
    # Ensure sorting by time
    call_df_sorted = call_df.sort_values(by="stime")
    for _, row in call_df_sorted.iterrows():
        speaker_label = "Agent" if row["speaker"] == AGENT_SPEAKER_ID else "Customer"
        text_content = str(row["text"]) if pd.notna(row["text"]) else "[empty utterance]"
        transcript.append(f"{speaker_label}: {text_content}")
    return "\n".join(transcript)


def _call_gemini_api_sdk(
    contents: str,
    generation_config: Optional[types.GenerationConfig] = None,
    safety_settings: Optional[List[types.SafetySetting]] = None,  # Default to None here
    response_mime_type: Optional[str] = None,
    response_schema: Optional[str] = None,
    max_retries: int = 2,
    delay: int = 5,
) -> Optional[str]:
    """
    Helper function to call the Gemini API using google-genai SDK
    with error handling and retries.
    """
    # Assign the actual default inside the function
    if safety_settings is None:
        safety_settings = DEFAULT_SAFETY_SETTINGS
    genai_client = get_genai_client()

    if not genai_client or not types or not genai:
        if "genai_client_error_shown" not in st.session_state:
            # Error shown by get_genai_client or import block
            # Optionally show a generic error here if needed for API calls
            st.error("Cannot call LLM: GenAI client/library not available.", icon="❌")
            st.session_state.genai_client_error_shown = True  # Avoid repeating
        logging.error(
            "Attempted to call Gemini API, but client/types are not configured."
        )
        return None

    if "genai_client_error_shown" in st.session_state:
        del st.session_state["genai_client_error_shown"]

    # Ensure client and types are available (check genai_client specifically)
    if not genai_client or not types or not genai:
        # Avoid showing duplicate errors if client failed initialization
        if "genai_client_error_shown" not in st.session_state:
            st.error("Google GenAI client is not configured. Cannot call LLM.")
            st.session_state.genai_client_error_shown = True
        logging.error(
            "Attempted to call Gemini API, but client/types are not configured."
        )
        return None

    try:
        config_dict = {}
        if generation_config:
            # Add specific config elements if provided
            if hasattr(generation_config, "temperature"):
                config_dict["temperature"] = generation_config.temperature
            if hasattr(generation_config, "max_output_tokens"):
                config_dict["max_output_tokens"] = generation_config.max_output_tokens
            if hasattr(generation_config, "response_schema"):
                config_dict["response_schema"] = generation_config.response_schema

            # Add others like top_p, top_k if needed
        if safety_settings:
            config_dict["safety_settings"] = safety_settings
        if response_mime_type:
            config_dict["response_mime_type"] = response_mime_type
        if response_schema:
            config_dict["response_schema"] = response_schema

        api_config = types.GenerateContentConfig(**config_dict) if config_dict else None
        model_path = f"models/{GEMINI_MODEL_NAME}"  # Use the model path format

        logging.info(
            f"Sending request to Gemini ({model_path}). MimeType: {response_mime_type or 'text/plain'}"
        )
        response = None
        for attempt in range(max_retries + 1):
            try:
                response = genai_client.models.generate_content(
                    model=model_path, contents=contents, config=api_config
                )
                logging.info(f"Received response from Gemini (attempt {attempt + 1}).")

                # Refined Response Validation
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason.name
                    logging.warning(f"Gemini response blocked. Reason: {block_reason}")
                    st.warning(f"LLM response blocked due to: {block_reason}.")
                    return None  # Failed due to blocking

                if not response.candidates:
                    logging.warning("Gemini response has no candidates.")
                    if attempt < max_retries:
                        logging.info(
                            f"Retrying LLM call (attempt {attempt + 2}/{max_retries + 1}) after empty candidates..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        st.warning(
                            "LLM response was empty (no candidates) after retries."
                        )
                        return None  # Failed after retries

                try:
                    response_text = response.text
                    logging.debug(f"LLM Raw Response Text: {response_text[:200]}...")
                    return response_text  # SUCCESS
                except ValueError as ve:
                    logging.warning(
                        f"Could not access response.text (potentially blocked). Error: {ve}"
                    )
                    st.warning(
                        "LLM response structure prevents text extraction (potentially blocked)."
                    )
                    return None  # Failed

            except (
                google_api_exceptions.ResourceExhausted,
                google_api_exceptions.InternalServerError,
                google_api_exceptions.ServiceUnavailable,
            ) as api_error:
                logging.warning(
                    f"API Error (attempt {attempt + 1}/{max_retries + 1}): {type(api_error).__name__} - {api_error}"
                )
                if attempt < max_retries:
                    logging.info(f"Retrying LLM call in {delay}s...")
                    time.sleep(delay)
                else:
                    st.error(
                        f"LLM API call failed after {max_retries + 1} attempts due to {type(api_error).__name__}."
                    )
                    logging.error(f"LLM API call failed definitively: {api_error}")
                    return None
            except Exception as e:
                logging.error(
                    f"Unexpected Error calling Gemini API (attempt {attempt + 1}/{max_retries + 1}): {e}",
                    exc_info=True,
                )
                st.error(f"LLM API call failed unexpectedly: {e}")
                return None  # Failed on unexpected error

    except Exception as e:
        logging.error(
            f"Failed to prepare or execute Gemini request: {e}", exc_info=True
        )
        st.error(f"Failed to interact with LLM: {e}")
        return None

    return None  # Fallback if all retries fail

# --- LLM Analysis Functions ---


def detect_profanity_llm(call_df: pd.DataFrame) -> Tuple[bool, bool]:
    agent_profane = False
    borrower_profane = False
    if call_df is None or call_df.empty:
        return agent_profane, borrower_profane
    if not get_genai_client():
        return agent_profane, borrower_profane  # Cannot run if client failed init

    transcript = _format_transcript_for_llm(call_df)
    if not transcript:
        logging.warning("LLM Profanity: Transcript empty.")
        return agent_profane, borrower_profane
    prompt = f"""Analyze the following debt collection call transcript for profanity.
    Profanity includes strong swear words and insults (e.g., 'fuck', 'shit', 'asshole', 'bitch', 'damn').

    Transcript:
    ---
    {transcript}
    ---

    Based **only** on the transcript provided:
    1. Did the **Agent** use any profane language? Answer "Yes" or "No".
    2. Did the **Customer** use any profane language? Answer "Yes" or "No".

    Return the answer **only** in JSON format conforming to the following schema:
    {{
    "agent_profanity": "string (Yes/No)",
    "borrower_profanity": "string (Yes/No)"
    }}
    """

    response_text = _call_gemini_api_sdk(
        contents=prompt,
        response_mime_type="application/json",
        response_schema=ProfanityResult,
    )

    if response_text:
        try:
            result = ProfanityResult.model_validate_json(response_text)
            agent_answer = result.agent_profanity.strip().lower()
            borrower_answer = result.borrower_profanity.strip().lower()
            agent_profane = agent_answer == "yes"
            borrower_profane = borrower_answer == "yes"
            logging.info(
                f"LLM Profanity Result (Pydantic validated): Agent={agent_profane}, Borrower={borrower_profane}"
            )
        except json.JSONDecodeError as e:
            logging.error(
                f"LLM Profanity JSON Decode Error: {e}. Response: {response_text[:200]}..."
            )
            st.warning(
                f"LLM profanity response wasn't valid JSON: '{response_text[:100]}...'"
            )
        except Exception as e:
            logging.error(f"LLM Profanity Processing Error: {e}", exc_info=True)
            st.warning(f"Error processing LLM profanity response: {e}")
    return agent_profane, borrower_profane


def detect_privacy_violation_llm(call_df: pd.DataFrame) -> bool:
    violation_detected = False
    if call_df is None or call_df.empty:
        return violation_detected
    if not get_genai_client():
        return violation_detected

    transcript = _format_transcript_for_llm(call_df)
    if not transcript:
        logging.warning("LLM Privacy: Transcript empty.")
        return violation_detected
    prompt = f"""Analyze the following debt collection call transcript for a potential privacy violation by the Agents.
    It is considered a violation  when agents have shared sensitive information like balance
    or account details without the identity verification (i.e. without verification of date
    of birth or address or Social Security Number or some personal identifier).

    Transcript:
    ---
    {transcript}
    ---

    Based **only** on the transcript provided:
    1. Did the **Agent** had any privacy or compliance Violation? Answer "Yes" or "No".

    Return the answer **only** in JSON format conforming to the following schema:
    {{
    "agent_violation": "string (Yes/No)",
    }}
    """
    response_text = _call_gemini_api_sdk(
        contents=prompt,
        response_mime_type="application/json",
        response_schema=PrivacyResult,
    )
    if response_text:
        try:
            result = PrivacyResult.model_validate_json(response_text)
            agent_answer = result.agent_violation.strip().lower()
            violation_detected = agent_answer == "yes"
            logging.info(f"LLM Privacy Result: Agent={violation_detected}")
        except json.JSONDecodeError as e:
            logging.error(
                f"LLM Privacy JSON Decode Error: {e}. Response: {response_text[:200]}..."
            )
            st.warning(
                f"LLM Privacy response wasn't valid JSON: '{response_text[:100]}...'"
            )
        except Exception as e:
            logging.error(f"LLM Privacy Processing Error: {e}", exc_info=True)
            st.warning(f"Error processing LLM Privacy response: {e}")
    return violation_detected

