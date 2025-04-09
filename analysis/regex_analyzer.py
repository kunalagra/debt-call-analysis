# analysis/regex_analyzer.py
import logging
import pandas as pd
from typing import Tuple

# Import constants and regex patterns from config
from config import (
    PROFANITY_REGEX,
    SENSITIVE_REGEX,
    VERIFY_REGEX,
    AGENT_SPEAKER_ID,
    BORROWER_SPEAKER_ID,
)

def detect_profanity_regex(call_df: pd.DataFrame) -> Tuple[bool, bool]:
    """Detects profanity using regex for agent and borrower."""
    agent_profane = False
    borrower_profane = False

    if call_df is None or call_df.empty:
        logging.debug("Regex Profanity: Input DataFrame is empty or None.")
        return agent_profane, borrower_profane

    for _, row in call_df.iterrows():
        text = row.get("text") # Use .get for safety
        speaker = row.get("speaker")

        if pd.isna(text) or not isinstance(text, str) or pd.isna(speaker):
            continue # Skip rows with missing essential data

        if PROFANITY_REGEX.search(text):
            if speaker == AGENT_SPEAKER_ID:
                agent_profane = True
                logging.debug(f"Regex: Agent profanity detected in text: '{text[:50]}...'")
            elif speaker == BORROWER_SPEAKER_ID:
                borrower_profane = True
                logging.debug(f"Regex: Borrower profanity detected in text: '{text[:50]}...'")

        # Optimization: exit early if both found
        if agent_profane and borrower_profane:
            break

    return agent_profane, borrower_profane

def detect_privacy_violation_regex(call_df: pd.DataFrame) -> bool:
    """Detects potential privacy violations using regex (sensitive info before verification)."""
    is_verified = False
    agent_asked_verification_in_last_turn = False
    violation_detected = False

    if call_df is None or call_df.empty:
        logging.debug("Regex Privacy: Input DataFrame is empty or None.")
        return False

    # Ensure data is sorted by time
    call_df = call_df.sort_values(by="stime").reset_index(drop=True)

    for index, row in call_df.iterrows():
        speaker = row.get("speaker")
        text = row.get("text")

        if pd.isna(text) or not isinstance(text, str) or pd.isna(speaker):
            continue

        # Check if borrower responded after agent asked for verification
        if speaker == BORROWER_SPEAKER_ID and agent_asked_verification_in_last_turn:
            # Simple heuristic: Assume any response from borrower after verification question means verification happened.
            # This is a potential weakness of the regex approach.
            is_verified = True
            logging.debug(f"Regex: Verification assumed at index {index} based on borrower response.")
            agent_asked_verification_in_last_turn = False # Reset flag after borrower response

        # Check agent utterances
        elif speaker == AGENT_SPEAKER_ID:
            asked_verification_this_turn = False
            mentioned_sensitive_this_turn = False

            # Did agent ask for verification?
            if VERIFY_REGEX.search(text):
                agent_asked_verification_in_last_turn = True
                asked_verification_this_turn = True
                logging.debug(f"Regex: Agent asked verification keywords at index {index}.")

            # Did agent mention sensitive info?
            if SENSITIVE_REGEX.search(text):
                mentioned_sensitive_this_turn = True
                logging.debug(f"Regex: Agent mentioned sensitive keywords at index {index}.")

            # Check for violation: Sensitive info mentioned *before* verification is confirmed
            if mentioned_sensitive_this_turn and not is_verified:
                logging.warning(f"Regex: Potential PRIVACY VIOLATION detected at index {index}. Sensitive info mentioned before verification confirmed.")
                violation_detected = True
                return True # Violation found, no need to check further

            # Reset verification flag if agent speaks again without asking for verification
            if not asked_verification_this_turn:
                 agent_asked_verification_in_last_turn = False

        # Reset flag if borrower speaks and didn't just verify
        elif speaker == BORROWER_SPEAKER_ID:
             agent_asked_verification_in_last_turn = False # Reset flag if borrower speaks


    return violation_detected # Return final status after checking all rows