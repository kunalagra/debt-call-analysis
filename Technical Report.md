# **Technical Report: Debt Collection Call Analysis Tool**

**Author:** Kunal Agrawal  
**Co-Authors:** Gemini & ChatGPT  
**Date:** 10 Apr, 2025  
**Project:** Call Analysis Tool for Compliance and Quality Metrics

---

## 1. Introduction

This report outlines the development and evaluation of a tool designed to analyze debt collection call transcripts. The tool aims to automatically assess calls for regulatory compliance (e.g., privacy violations), agent professionalism (e.g., profanity usage), and overall call quality (e.g., overtalk and silence metrics). Call transcripts are provided in JSON format and analyzed using both traditional pattern-matching (Regex) and modern AI techniques (Large Language Models - LLMs). 

An interactive Streamlit application allows users to perform single or batch call analysis, compare results across methods, and visualize insights. This project fulfills the requirements of the selection process assignment.

---

## 2. Project Objectives

The key objectives of this project were:

1.  **Profanity Detection:** Implement Regex and LLM-based methods to identify use of profane language by agents or borrowers (Q1).
2.  **Privacy Violation Detection:** Detect cases where agents share sensitive information before completing identity verification (Q2).
3.  **Call Quality Metrics:** Calculate overtalk and silence percentages per call (Q3a, Q3b).
4.  **Compare Analytical Methods:** Evaluate Regex vs. LLM effectiveness in profanity and privacy detection.
5.  **Develop Streamlit Application:** Create a UI for uploading transcripts, selecting analysis modes, and reviewing results.
6.  **Visualize Metrics:** Generate visual representations of silence and overtalk metrics across calls.
7.  **Offer Recommendations:** Recommend suitable approaches for production environments based on comparative findings.

---

## 3. Data Description

Input data consists of individual JSON files per call, each named with a unique `call_id`. Each file includes a list of utterances structured as:

- `speaker` (string): Identifies the speaker, e.g., `"agent"` or `"customer"`, standardized to lowercase.
- `text` (string): The transcribed content of the utterance.
- `stime` and `etime` (floats): Start and end timestamps (in seconds).

The `data_loader.py` module parses the JSON, performs cleaning (e.g., handling missing values, type conversion), and computes utterance durations.

> 📌 *Note: Although YAML was mentioned in the assignment, the codebase handles JSON. This report assumes JSON as the input format.*

---

## 4. Methodology and Implementation

The implementation is done in Python using Pandas, Plotly, Streamlit, and the Google Generative AI SDK. The code is modular, ensuring readability and ease of maintenance.

### 4.1. Profanity Detection (Q1)

#### 1. Regex-Based Approach
- **Location:** `analysis/regex_analyzer.py` → `detect_profanity_regex`
- **Logic:** Uses a predefined list of profane words from `config.PROFANE_WORDS`, compiled into a regex pattern.
- **Output:** Boolean flags for agent and borrower profanity.
- **Pros:** Fast, deterministic.
- **Cons:** Misses context, slang, misspellings, or nuance.

#### 2. LLM-Based Approach (Google Gemini)
- **Location:** `analysis/llm_analyzer.py` → `detect_profanity_llm`
- **Logic:** Formats transcript, constructs a prompt, and sends it to the Gemini model requesting JSON output.
- **Output Format:** `{"agent_profanity": "Yes/No", "borrower_profanity": "Yes/No"}`
- **Pros:** Understands context, captures subtle or indirect profanity.
- **Cons:** Slower, costlier, prompt-sensitive.

---

### 4.2. Privacy Violation Detection (Q2)

#### 1. Regex-Based Approach
- **Location:** `analysis/regex_analyzer.py` → `detect_privacy_violation_regex`
- **Logic:** Uses keyword matching for sensitive terms and verification phrases. Flags violations if sensitive data is shared before verification is confirmed (naively defined as any borrower response).
- **Pros:** Fast, simple.
- **Cons:** Lacks nuance, high risk of false positives/negatives.

#### 2. LLM-Based Approach
- **Location:** `analysis/llm_analyzer.py` → `detect_privacy_violation_llm`
- **Logic:** Prompt guides LLM to check for disclosure of sensitive info before verifying identity, with structured output.
- **Output Format:** `{"agent_violation": "Yes/No"}`
- **Pros:** Strong contextual awareness, better at understanding verification flow.
- **Cons:** Same limitations as LLM Profanity Detection.

---

### 4.3. Call Quality Metrics (Q3a & Q3b)

- **Location:** `analysis/metrics_analyzer.py` → `calculate_call_metrics`
- **Steps:**
    1. Clean data: Remove utterances with invalid/negative timestamps.
    2. Compute total call duration.
    3. Build timeline of speaker activity changes.
    4. Calculate merged speech and overlapping durations.
    5. Derive:
        - `overtalk_percentage = overlap_duration / total_duration`
        - `silence_percentage = (total_duration - merged_speech_duration) / total_duration`
    6. Return: overtalk %, silence %, and total duration.

---

### 4.4. Streamlit Application

- **Location:** `app.py`
- **Features:**
    - **Modes:** Single File & Batch
    - **Options:** Choose between Profanity or Privacy analysis, and Regex vs. LLM approach.
    - **Visuals:** Displays flags, bar charts (for single files), summary tables, histograms (for batch).
    - **Optimizations:** LLM client cached with `st.cache_resource`; uses Plotly Express for graphs.
    - **Batch Mode:** Includes LLM availability checks; displays processing progress and results.

---

## 5. Comparative Analysis (Q1 & Q2)

### 5.1. Profanity Detection

| Metric | Regex | LLM (Gemini) |
|--------|-------|--------------|
| **Speed** | Very fast | Slower (API latency) |
| **Accuracy** | Good for exact matches; high false positives in some contexts | Better contextual understanding; fewer false positives |
| **Recommendation** | Efficient for clear-cut cases | Preferable for nuanced cases or production |

### 5.2. Privacy Violation Detection

| Metric | Regex | LLM (Gemini) |
|--------|-------|--------------|
| **Speed** | Very fast | Slower (API latency) |
| **Accuracy** | Unreliable (e.g., flagged call `"6eec7cee..."` falsely) | More accurate; handled `"877e2349..."` inconsistently but generally reliable |
| **Recommendation** | Not suitable for production | Strongly preferred due to contextual reasoning capabilities |

---

## 6. Visualization Analysis (Q3)

The Streamlit app generates histograms to visualize Overtalk and Silence metrics across calls.

- **Overtalk Distribution:** Most calls exhibit low overtalk (0–5%), indicating cooperative dialogue. A few outliers (>10%) may suggest argumentative interactions or frequent interruptions.
- **Silence Distribution:** Centered around 15–25%, suggesting natural pauses. High silence (>40%) could reflect hold times or disengagement. Low silence (<10%) may indicate high-pressure environments or scripted calls.
- **Insights:** These visualizations help identify behavioral patterns, outlier calls, and potential agent training needs.

---

## 7. Implementation Recommendations

1. **Profanity Detection:**
    - **Use Case:** General analysis, training insights.
    - **Recommendation:** **Hybrid approach.**
    - **Why:** Start with Regex for quick flagging; escalate to LLM for nuanced review or high-stakes cases.

2. **Privacy Violation Detection:**
    - **Use Case:** Regulatory compliance.
    - **Recommendation:** **LLM approach only.**
    - **Why:** Regex is insufficient for evaluating verification flow. LLMs provide necessary contextual reasoning.

3. **Call Quality Metrics:**
    - **Use Case:** Performance evaluation, process improvement.
    - **Recommendation:** **Retain current implementation.**
    - **Why:** Timeline-based calculation is efficient, interpretable, and does not require external services. It serves as a robust foundation for silence/overtalk insights.

