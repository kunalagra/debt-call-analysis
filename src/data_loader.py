# data_loader.py
import json
import logging
import os
from typing import Any

import pandas as pd

# We avoid streamlit imports here for better separation


def parse_json_to_df(json_file_content: Any) -> pd.DataFrame | None:
    """Parses JSON content (from uploaded file or opened file) into a Pandas DataFrame."""
    try:
        # Handle file-like objects (uploaded file) vs. lists (direct data)
        if hasattr(json_file_content, "read"):
            json_data_str = json_file_content.read()
            # Decode if bytes
            if isinstance(json_data_str, bytes):
                json_data_str = json_data_str.decode("utf-8")
            data = json.loads(json_data_str)
        elif isinstance(
            json_file_content, (str, bytes)
        ):  # Handle raw string/bytes content
            if isinstance(json_file_content, bytes):
                json_data_str = json_file_content.decode("utf-8")
            else:
                json_data_str = json_file_content
            data = json.loads(json_data_str)
        elif isinstance(json_file_content, list):
            data = json_file_content  # Assume it's already parsed list of dicts
        else:
            logging.error(
                f"Unsupported input type for JSON parsing: {type(json_file_content)}"
            )
            # Raise error or return None, depending on desired handling
            # raise TypeError(f"Unsupported input type: {type(json_file_content)}")
            return None  # Keep consistent with original return type

        df = pd.DataFrame(data)
        required_cols = ["speaker", "text", "stime", "etime"]
        if not all(col in df.columns for col in required_cols):
            missing_cols = [col for col in required_cols if col not in df.columns]
            logging.error(f"JSON data is missing required columns: {missing_cols}")
            # Optionally raise an exception here too
            return None

        # Data cleaning and validation
        df["stime"] = pd.to_numeric(df["stime"], errors="coerce")
        df["etime"] = pd.to_numeric(df["etime"], errors="coerce")
        df["speaker"] = df["speaker"].astype(str).str.strip().str.lower()
        df["text"] = df["text"].astype(str)

        df = df.dropna(subset=["stime", "etime", "speaker"])
        if df.empty:
            logging.warning("DataFrame is empty after dropping NaNs in core columns.")
            return None

        # Ensure etime >= stime and calculate duration
        df["duration"] = df["etime"] - df["stime"]
        df = df[df["duration"] >= 0]

        if df.empty:
            logging.warning(
                "DataFrame is empty after filtering negative duration utterances."
            )
            return None

        return df

    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {e}")
        # Let the caller handle UI feedback
        return None
    except Exception as e:
        logging.error(
            f"An unexpected error occurred during JSON parsing: {e}", exc_info=True
        )
        # Let the caller handle UI feedback
        return None


def load_all_calls(directory: str, progress_callback=None) -> dict[str, pd.DataFrame]:
    """
    Loads all JSON call transcripts from a specified directory into a dictionary.

    Args:
        directory: The path to the directory containing JSON files.
        progress_callback: An optional function to report progress (e.g., lambda i, total, filename: ...)

    Returns:
        A dictionary mapping call_id (filename without extension) to DataFrame.
    """
    call_data = {}
    logging.info(f"Attempting to load calls from directory: {directory}")
    if not os.path.isdir(directory):
        logging.error(f"Directory not found: {directory}")
        # Caller should handle UI feedback (e.g., st.error)
        return call_data  # Return empty dict

    try:
        files_to_process = [f for f in os.listdir(directory) if f.endswith(".json")]
    except OSError as e:
        logging.error(f"Error listing directory {directory}: {e}")
        return call_data  # Return empty dict

    if not files_to_process:
        logging.warning(f"No JSON files found in directory: {directory}")
        # Caller should handle UI feedback (e.g., st.warning)
        return call_data

    total_files = len(files_to_process)
    for i, filename in enumerate(files_to_process):
        call_id = filename.replace(".json", "")
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, encoding="utf-8") as file:
                # Pass the raw file content string/bytes to the parser
                content = file.read()
                df = parse_json_to_df(content)
                if df is not None and not df.empty:
                    call_data[call_id] = df
                    logging.debug(f"Successfully loaded and parsed {filename}")
                else:
                    # parse_json_to_df logs specific errors
                    logging.warning(
                        f"Skipping file {filename} due to parsing errors or empty data."
                    )
        except Exception as e:
            logging.error(f"Failed to load or process file {filename}: {e}")
            # Optionally report this specific file error via callback or just log it

        # Report progress if callback is provided
        if progress_callback:
            try:
                progress_callback(i + 1, total_files, filename)
            except Exception as cb_e:
                logging.warning(f"Progress callback failed: {cb_e}")

    logging.info(
        f"Successfully loaded {len(call_data)} calls out of {total_files} files found."
    )
    if not call_data and files_to_process:
        logging.warning(
            "Finished loading, but no valid call data could be processed from the found files."
        )
    return call_data
