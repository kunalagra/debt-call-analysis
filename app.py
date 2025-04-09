import streamlit as st
import pandas as pd
import plotly.express as px
import os
import logging
from collections import defaultdict
from typing import Dict, Any

st.set_page_config(page_title="Call Analysis Tool", layout="wide", initial_sidebar_state="expanded")


from config import logging
from data_loader import parse_json_to_df
from batch_processor import analyze_all_calls
from analysis.regex_analyzer import detect_profanity_regex, detect_privacy_violation_regex
from analysis.llm_analyzer import (
    detect_profanity_llm,
    detect_privacy_violation_llm,
    get_genai_client,
    GENAI_AVAILABLE
)
from analysis.metrics_analyzer import calculate_call_metrics

APP_TITLE = "📞 Debt Collection Call Analysis Tool"
ANALYSIS_TYPES = ["Profanity Detection", "Privacy and Compliance Violation"]
APPROACHES_REGEX = "Pattern Matching (Regex)"
APPROACHES_LLM = "LLM (Google GenAI)"
APPROACHES = [APPROACHES_REGEX, APPROACHES_LLM]


# --- Helper Functions for UI ---

def display_analysis_result(entity_option: str, approach_option: str, call_df: pd.DataFrame):
    """Displays the result of a single analysis based on selected options."""
    st.markdown(f"##### Analysis: {entity_option} ({approach_option})")
    analysis_performed = False
    error_message = None

    try:
        # Regex Logic
        if approach_option == APPROACHES_REGEX:
            if entity_option == ANALYSIS_TYPES[0]: # Profanity
                a_f, b_f = detect_profanity_regex(call_df)
                col1, col2 = st.columns(2)
                col1.metric("Agent Profanity", "Yes" if a_f else "No")
                col2.metric("Borrower Profanity", "Yes" if b_f else "No")
                if a_f: st.warning("Agent profanity detected (Regex).", icon="🤬")
                if b_f: st.info("Borrower profanity detected (Regex).", icon="🗣️")
                analysis_performed = True
            elif entity_option == ANALYSIS_TYPES[1]: # Privacy
                v_f = detect_privacy_violation_regex(call_df)
                st.metric("Potential Privacy Violation", "Yes" if v_f else "No")
                if v_f: st.error("Potential violation detected (Regex).", icon="🔒")
                else: st.success("No violation detected (Regex).", icon="✅")
                analysis_performed = True

        # LLM Logic
        elif approach_option == APPROACHES_LLM:
            if not GENAI_AVAILABLE:
                error_message = "LLM analysis unavailable: `google-generai` library not installed."
                st.error(error_message, icon="🚨")
            elif get_genai_client() is None: # Check if client is ready
                error_message = "LLM analysis unavailable: Google GenAI Client connection failed. Check API Key/Network."
                st.error(error_message, icon="❌")
            else:
                with st.spinner("Analyzing with LLM..."):
                    if entity_option == ANALYSIS_TYPES[0]: # Profanity
                        a_f, b_f = detect_profanity_llm(call_df)
                        col1, col2 = st.columns(2)
                        col1.metric("Agent Profanity (LLM)", "Yes" if a_f else "No")
                        col2.metric("Borrower Profanity (LLM)", "Yes" if b_f else "No")
                        if a_f: st.warning("LLM detected Agent profanity.", icon="🤬")
                        if b_f: st.info("LLM detected Borrower profanity.", icon="🗣️")
                        analysis_performed = True
                    elif entity_option == ANALYSIS_TYPES[1]: # Privacy
                        v_f = detect_privacy_violation_llm(call_df)
                        st.metric("Potential Privacy Violation (LLM)", "Yes" if v_f else "No")
                        if v_f: st.error("LLM detected potential privacy violation.", icon="🔒")
                        else: st.success("LLM did not detect a privacy violation.", icon="✅")
                        analysis_performed = True
        else:
            error_message = "Internal Error: Invalid approach selected."
            st.error(error_message)

    except Exception as e:
        analysis_performed = False
        error_message = f"An error occurred during analysis: {e}"
        logging.error(f"Error during single file analysis: {e}", exc_info=True)
        st.error(f"Analysis Error: {e}", icon="🔥")

    if not analysis_performed and not error_message:
         st.info("Select options and click 'Analyze Call'.")


def display_metrics(call_df: pd.DataFrame):
    """Calculates and displays call quality metrics and visualization."""
    st.subheader("📊 Call Quality Metrics")
    try:
        ot_pct, sil_pct, tot_dur = calculate_call_metrics(call_df)

        c1, c2, c3 = st.columns(3)
        c1.metric("Overtalk %", f"{ot_pct:.2f}%")
        c2.metric("Silence %", f"{sil_pct:.2f}%")
        c3.metric("Duration (s)", f"{tot_dur:.2f}s")

        # Visualization (Bar Chart)
        if tot_dur > 0:
            # Ensure percentages add up reasonably (handle potential float issues)
            # We only explicitly plot overtalk and silence. Speech is implied.
            m_data = []
            m_data.append({"Metric": "Overtalk", "Percentage": ot_pct})
            m_data.append({"Metric": "Silence", "Percentage": sil_pct})
            # Add calculated speech time if needed for completeness (optional)
            # speech_pct = max(0, 100 - sil_pct) # Approximation, as it includes overtalk
            # m_data.append({"Metric": "Speech (inc. Overtalk)", "Percentage": speech_pct})


            if m_data:
                m_df = pd.DataFrame(m_data)
                fig = px.bar(
                    m_df,
                    x="Percentage",
                    y="Metric",
                    orientation="h",
                    color="Metric",
                    color_discrete_map={
                        "Silence": "#118AB2", # Blueish
                        "Overtalk": "#EF476F", # Reddish/Pink
                        # "Speech (inc. Overtalk)": "#06D6A0", # Greenish
                    },
                    title="Call Time Usage Breakdown",
                    text_auto=".1f", # Show percentage on bars
                    range_x=[0,100] # Ensure scale is 0-100
                )
                fig.update_layout(
                     yaxis_title=None,
                     xaxis_title="Percentage of Call Duration",
                     showlegend=False # Legend might be redundant if colors are clear
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                 st.info("No significant silence or overtalk detected to plot.")

        else:
            st.warning("Metrics chart unavailable (call duration is zero or negative).")

    except Exception as e:
        logging.error(f"Error calculating or displaying metrics: {e}", exc_info=True)
        st.error(f"Could not calculate/display metrics: {e}", icon="⚠️")


def display_batch_results_summary(results: Dict[str, Dict[str, Any]]):
    """Displays the summary table and visualizations for batch results."""
    if not results:
        st.warning("No batch results to display.")
        return

    st.subheader("Batch Analysis Summary")

    # Check if any LLM results exist (handles cases where LLM failed/was skipped)
    has_llm_results = any(r.get("agent_profanity_llm") is not None or r.get("privacy_violation_llm") is not None
                          for r in results.values())
    llm_skipped_all = all(r.get("llm_skipped", False) for r in results.values())


    # --- Create Summary DataFrame ---
    summary_data = []
    error_counts = defaultdict(int)
    valid_metric_calls = 0
    for call_id, res in results.items():
        row = {"Call ID": call_id}
        # Regex Results
        row["Agent Profanity (Regex)"] = res.get("agent_profanity_regex", "Error")
        row["Borrower Profanity (Regex)"] = res.get("borrower_profanity_regex", "Error")
        row["Privacy Violation (Regex)"] = res.get("privacy_violation_regex", "Error")
        # LLM Results
        if has_llm_results and not llm_skipped_all:
             row["Agent Profanity (LLM)"] = res.get("agent_profanity_llm", "N/A")
             row["Borrower Profanity (LLM)"] = res.get("borrower_profanity_llm", "N/A")
             row["Privacy Violation (LLM)"] = res.get("privacy_violation_llm", "N/A")
        elif llm_skipped_all:
             row["LLM Analysis"] = "Skipped (Check Config/Key)"
        # Metrics
        row["Overtalk %"] = res.get("overtalk_percentage")
        row["Silence %"] = res.get("silence_percentage")
        row["Duration (s)"] = res.get("total_duration_seconds")

        # Check for errors
        has_error = False
        if "regex_error" in res: error_counts["Regex Error"] += 1; has_error = True
        if "llm_profanity_error" in res: error_counts["LLM Profanity Error"] += 1; has_error = True
        if "llm_privacy_error" in res: error_counts["LLM Privacy Error"] += 1; has_error = True
        if "metrics_error" in res: error_counts["Metrics Error"] += 1; has_error = True
        row["Errors"] = "Yes" if has_error else "No"

        if not has_error and row["Overtalk %"] is not None:
             valid_metric_calls += 1

        summary_data.append(row)

    summary_df = pd.DataFrame(summary_data)

    # --- Display Summary Table ---
    st.dataframe(summary_df, use_container_width=True)

    # --- Display Aggregate Counts ---
    st.markdown("**Aggregate Findings:**")
    cols = st.columns(3 if not llm_skipped_all else 2)

    with cols[0]:
         st.markdown("**Regex**")
         st.metric("Agent Profanity", summary_df[summary_df["Agent Profanity (Regex)"] == True].shape[0])
         st.metric("Borrower Profanity", summary_df[summary_df["Borrower Profanity (Regex)"] == True].shape[0])
         st.metric("Privacy Violations", summary_df[summary_df["Privacy Violation (Regex)"] == True].shape[0])

    if not llm_skipped_all:
         with cols[1]:
             st.markdown("**LLM**")
             if has_llm_results:
                 st.metric("Agent Profanity", summary_df[summary_df["Agent Profanity (LLM)"] == True].shape[0])
                 st.metric("Borrower Profanity", summary_df[summary_df["Borrower Profanity (LLM)"] == True].shape[0])
                 st.metric("Privacy Violations", summary_df[summary_df["Privacy Violation (LLM)"] == True].shape[0])
             else:
                 st.caption("LLM results unavailable or failed.")

    metric_col_index = 2 if not llm_skipped_all else 1
    with cols[metric_col_index]:
         st.markdown("**Average Metrics**")
         if valid_metric_calls > 0:
            # Calculate means only on valid numeric rows
            valid_metrics = summary_df[pd.to_numeric(summary_df["Overtalk %"], errors='coerce').notna()]
            st.metric("Avg. Overtalk %", f"{valid_metrics['Overtalk %'].mean():.2f}%")
            st.metric("Avg. Silence %", f"{valid_metrics['Silence %'].mean():.2f}%")
            st.metric("Avg. Duration (s)", f"{valid_metrics['Duration (s)'].mean():.2f}s")
            st.caption(f"Based on {valid_metric_calls} calls with valid metrics.")
         else:
             st.caption("No valid metrics found.")


    # --- Display Metric Distributions ---
    st.markdown("**Metric Distributions (for calls with valid metrics):**")
    metrics_df = summary_df.dropna(subset=["Overtalk %", "Silence %", "Duration (s)"]).copy()
    metrics_df = metrics_df[pd.to_numeric(metrics_df["Overtalk %"], errors='coerce').notna()] # Ensure numeric
    metrics_df["Overtalk %"] = metrics_df["Overtalk %"].astype(float)
    metrics_df["Silence %"] = metrics_df["Silence %"].astype(float)


    if not metrics_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig_ot = px.histogram(metrics_df, x="Overtalk %", title="Overtalk % Distribution", nbins=15)
            st.plotly_chart(fig_ot, use_container_width=True)
        with col2:
            fig_sil = px.histogram(metrics_df, x="Silence %", title="Silence % Distribution", nbins=15)
            st.plotly_chart(fig_sil, use_container_width=True)
    else:
        st.warning("No valid metrics data available for distribution plots.")

    # --- Display Errors ---
    if error_counts:
        st.divider()
        with st.expander(f"⚠️ View Batch Processing Errors ({sum(error_counts.values())} total issues found)"):
            for error_type, count in error_counts.items():
                 st.error(f"**{error_type}:** {count} call(s) affected.")
            # Optional: List specific Call IDs with errors if needed (more verbose)
            error_details = defaultdict(list)
            for call_id, res in results.items():
                 for key in res.keys():
                     if "error" in key:
                         error_details[key].append(f"{call_id}: {res[key]}")

            for error_type, messages in error_details.items():
                 st.markdown(f"**Details for {error_type}:**")
                 st.text("\n".join(messages[:10])) # Show first 10 errors
                 if len(messages) > 10: st.caption("...")


# --- Main Streamlit Application Logic ---
def run_streamlit_app():
    """Defines and runs the Streamlit UI."""

    st.title(APP_TITLE)
    st.markdown("""
        Analyze call transcripts (`.json`) for compliance, professionalism, and quality metrics.
        Upload a single file or specify a directory for batch analysis.
        LLM analysis uses Google's Gemini (`google-genai` SDK). Ensure API key is configured via Streamlit Secrets (`GOOGLE_API_KEY`) or environment variables.
    """)

    # Check LLM Status Once and Display Persistent Message if Needed
    llm_status_msg = None
    llm_status_icon = "✅"
    if not GENAI_AVAILABLE:
        llm_status_msg = "LLM features unavailable: `google-genai` not installed."
        llm_status_icon = "⚠️"
    elif get_genai_client() is None:
        llm_status_msg = "LLM client connection failed. Check API Key/Network."
        llm_status_icon = "❌"
    else:
         llm_status_msg = "LLM (Google GenAI) client connected."

    st.sidebar.header("Mode")
    analysis_mode = st.sidebar.radio(
        "Select Analysis Mode:",
        ("Analyze Single File", "Analyze Directory (Batch)"),
        key="analysis_mode_radio"
    )
    st.sidebar.divider()


    # --- Single File Mode ---
    if analysis_mode == "Analyze Single File":
        st.sidebar.header("Single File Analysis")
        uploaded_file = st.sidebar.file_uploader(
            "Upload call transcript (JSON)", type=["json"], key="single_uploader"
        )
        entity_option = st.sidebar.selectbox(
            "Analysis Type", ANALYSIS_TYPES, key="entity_single"
        )
        # Filter approaches based on LLM availability
        available_approaches = APPROACHES if GENAI_AVAILABLE and get_genai_client() else [APPROACHES_REGEX]
        approach_option = st.sidebar.selectbox(
            "Approach", available_approaches, key="approach_single",
            help="LLM option requires google-genai library and a configured API key."
        )

        analyze_button = st.sidebar.button(
            "📊 Analyze Call", key="analyze_single", use_container_width=True, type="primary"
        )

        st.header("Single File Analysis Results")

        if analyze_button and uploaded_file is not None:
            uploaded_file.seek(0) # Reset file pointer before reading again
            call_df = None
            parse_error = False
            try:
                # Pass the file object directly to the parser
                call_df = parse_json_to_df(uploaded_file)
            except Exception as e:
                 st.error(f"Fatal error parsing file: {e}")
                 logging.error(f"File parsing failed in UI: {e}", exc_info=True)
                 parse_error = True


            if call_df is not None and not call_df.empty:
                st.success(f"Successfully parsed '{uploaded_file.name}' ({len(call_df)} utterances).")
                with st.expander("View Raw Data"):
                    st.dataframe(call_df, height=300)

                # Containers for results
                res_c = st.container(border=True)
                met_c = st.container(border=True)

                with res_c:
                    display_analysis_result(entity_option, approach_option, call_df)
                with met_c:
                    display_metrics(call_df)

            elif not parse_error: # If parsing didn't throw error but returned None/empty
                st.error(f"Could not parse or process the data in '{uploaded_file.name}'. Check file format and content (see logs for details).")

        elif analyze_button and uploaded_file is None:
            st.warning("Please upload a JSON file first.", icon="⬆️")
        else:
            st.info("Upload a file and select options in the sidebar, then click 'Analyze Call'.")


    # --- Batch Mode ---
    elif analysis_mode == "Analyze Directory (Batch)":
        st.sidebar.header("Batch Analysis")
        data_dir = st.sidebar.text_input(
            "Directory Path containing JSON files:",
            value="All_Conversations", # Default value
            key="batch_dir_input",
            help="Enter the relative or absolute path to the directory.",
        )

        batch_btn = st.sidebar.button(
            "🚀 Run Batch Analysis", key="analyze_batch", use_container_width=True, type="primary"
        )

        st.header("Batch Analysis Results")

        # Define progress callback for batch processor
        progress_bar = st.progress(0, text="Starting batch analysis...")
        progress_bar.empty() # Hide initially

        def update_progress(current, total, filename):
            progress_bar.progress(current / total, text=f"Analyzing ({current}/{total}): {filename}...")


        if batch_btn:
            if data_dir and os.path.isdir(data_dir):
                st.info(f"Starting batch analysis for directory: {data_dir}")
                progress_bar.progress(0, text="Loading files...") # Show progress bar
                results = None
                try:
                     # Pass the UI callback function to the batch processor
                     results = analyze_all_calls(data_dir, progress_callback=update_progress)
                     st.session_state["batch_results"] = results # Store results
                     progress_bar.empty() # Hide progress bar on completion
                     if results:
                         st.success("Batch analysis complete.")
                     else:
                         st.warning("Batch analysis finished, but no results were generated. Check directory contents and logs.")

                except Exception as e:
                     progress_bar.empty() # Hide progress bar on error
                     st.error(f"An unexpected error occurred during batch processing: {e}", icon="🔥")
                     logging.error(f"Fatal error during batch processing: {e}", exc_info=True)
                     if "batch_results" in st.session_state:
                         del st.session_state["batch_results"] # Clear potentially incomplete results

                # Display results if any were generated
                if "batch_results" in st.session_state and st.session_state["batch_results"]:
                    display_batch_results_summary(st.session_state["batch_results"])
                # elif not results: # Handled above
                #     pass # Message already shown

            elif not data_dir:
                st.error("Please enter a directory path.", icon="📁")
            else: # Directory not found
                st.error(f"Directory not found or is not accessible: `{data_dir}`", icon="❌")

        # Option to display previous results if they exist in session state
        elif "batch_results" in st.session_state and st.session_state["batch_results"]:
            st.info("Displaying previous batch results. Run analysis again to update.")
            display_batch_results_summary(st.session_state["batch_results"])
        else:
            st.info("Enter a directory path in the sidebar and click 'Run Batch Analysis'.")

    st.sidebar.divider()
    st.sidebar.header("Configuration")
    st.sidebar.info(f"LLM Status: {llm_status_msg}", icon=llm_status_icon)

# --- Main Execution Guard ---
if __name__ == "__main__":
    # Setup (like logging) can happen here or be imported from config
    logging.info("Starting Streamlit App")
    run_streamlit_app()