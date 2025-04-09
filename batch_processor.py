# batch_processor.py
import logging
from collections import defaultdict
from typing import Dict, Any, Callable, Optional

# Import necessary components
from data_loader import load_all_calls
from analysis.regex_analyzer import detect_profanity_regex, detect_privacy_violation_regex
from analysis.llm_analyzer import (
    detect_profanity_llm,
    detect_privacy_violation_llm,
    get_genai_client, # To check if LLM is available
    GENAI_AVAILABLE
)
from analysis.metrics_analyzer import calculate_call_metrics

def analyze_all_calls(
    directory: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Analyzes all valid call transcripts in a directory using all available methods.

    Args:
        directory: Path to the directory containing JSON call files.
        progress_callback: Optional function to report progress back to the UI.
                           Should accept (current_count, total_count, filename).

    Returns:
        A dictionary where keys are call_ids and values are dictionaries
        containing analysis results for that call.
    """
    results = defaultdict(dict)
    logging.info(f"Starting batch analysis for directory: {directory}")

    # Load calls, passing the progress callback directly if loader supports it
    # If load_all_calls doesn't accept callback, we handle progress in the loop below
    all_call_data = load_all_calls(directory) # Add callback here if loader is modified: , progress_callback=progress_callback

    if not all_call_data:
        logging.warning("Batch Analysis: No valid call data loaded.")
        # UI feedback handled by caller (app.py)
        return dict(results)

    # Check LLM availability *once* before the loop
    llm_available_and_ready = GENAI_AVAILABLE and (get_genai_client() is not None)
    if not llm_available_and_ready:
        logging.warning("LLM client not available or failed to initialize. LLM analysis will be skipped.")
        # UI should show a persistent warning in app.py

    total_calls = len(all_call_data)
    logging.info(f"Analyzing {total_calls} loaded calls...")

    for i, (call_id, df) in enumerate(all_call_data.items()):
        logging.info(f"Analyzing call: {call_id} ({i+1}/{total_calls})")
        current_results = {}

        # --- Run Regex Analysis ---
        try:
            agent_pr_re, borrower_pr_re = detect_profanity_regex(df)
            privacy_vr_re = detect_privacy_violation_regex(df)
            current_results.update({
                "agent_profanity_regex": agent_pr_re,
                "borrower_profanity_regex": borrower_pr_re,
                "privacy_violation_regex": privacy_vr_re,
            })
        except Exception as e:
            logging.error(f"Batch: Regex analysis error on {call_id}: {e}", exc_info=True)
            current_results["regex_error"] = str(e)

        # --- Run LLM Analysis (if available and ready) ---
        if llm_available_and_ready:
            try:
                agent_pr_llm, borrower_pr_llm = detect_profanity_llm(df)
                current_results.update({
                    "agent_profanity_llm": agent_pr_llm,
                    "borrower_profanity_llm": borrower_pr_llm,
                })
            except Exception as e:
                logging.error(f"Batch: LLM profanity error on {call_id}: {e}", exc_info=True)
                current_results["llm_profanity_error"] = str(e)
                # Set flags to None to indicate failure for this call
                current_results["agent_profanity_llm"] = None
                current_results["borrower_profanity_llm"] = None

            try:
                privacy_vr_llm = detect_privacy_violation_llm(df)
                current_results["privacy_violation_llm"] = privacy_vr_llm
            except Exception as e:
                logging.error(f"Batch: LLM privacy error on {call_id}: {e}", exc_info=True)
                current_results["llm_privacy_error"] = str(e)
                 # Set flag to None to indicate failure for this call
                current_results["privacy_violation_llm"] = None
        else:
            # Mark LLM results as explicitly unavailable if LLM wasn't ready
            current_results.update({
                "agent_profanity_llm": None,
                "borrower_profanity_llm": None,
                "privacy_violation_llm": None,
                "llm_skipped": True # Add a flag indicating LLM was skipped
            })

        # --- Run Metrics Calculation ---
        try:
            overtalk, silence, duration = calculate_call_metrics(df)
            current_results.update({
                "overtalk_percentage": overtalk,
                "silence_percentage": silence,
                "total_duration_seconds": duration,
            })
        except Exception as e:
            logging.error(f"Batch: Metrics calculation error on {call_id}: {e}", exc_info=True)
            current_results["metrics_error"] = str(e)
            # Set metrics to None or NaN to indicate failure
            current_results.update({
                "overtalk_percentage": None, "silence_percentage": None, "total_duration_seconds": None
            })


        results[call_id] = current_results

        # --- Report Progress (if callback provided and loader didn't handle it) ---
        if progress_callback:
             try:
                 # Use filename = call_id + ".json" for consistency if needed
                 progress_callback(i + 1, total_calls, f"{call_id}.json")
             except Exception as cb_e:
                 logging.warning(f"Progress callback failed during analysis loop: {cb_e}")


    logging.info(f"Batch analysis complete. Processed {len(results)} calls.")
    return dict(results)