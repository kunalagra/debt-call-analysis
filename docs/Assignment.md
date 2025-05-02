# Project Overview

As part of this selection process assignment, you will analyze a few conversations between debt collection agents and the borrowers. The goal is to evaluate compliance, professionalism, and call metrics. Each conversation is stored in a YAML file format with detailed utterance-level information.

## Data Structure

The name of each file represents the call ID.

Each YAML file (in `All_Conversations.zip`) contains the following fields:

- `speaker`: Identifies whether the utterance is from an agent or borrower  
- `text`: Contains the actual speech content  
- `stime`: Records the start timestamp of the utterance  
- `etime`: Records the end timestamp of the utterance  

## Analysis Tasks

### Question-1. Profanity Detection

- a. Identify all the call IDs where collection agents have used profane language.  
- b. Identify all the call IDs where borrowers have used profane language.  

### Question-2. Privacy and Compliance Violation

- a. Identify all the call IDs where agents have shared sensitive information (balance or account details) without the identity verification (i.e., without verification of date of birth or address or Social Security Number).  

### Question-3. Call Quality Metrics Analysis

- a. Calculate overtalk (i.e., simultaneous speaking) percentage per call.  
- b. Calculate silence percentage per call.  

## Implementation Requirements

### For Question-1 and Question-2:

- **Pattern Matching Approach**: Implement regex-based detection systems ([Reference]).  
- **Machine Learning Approach**: Choose one of the following:  
  - Develop a classification model (requires manual annotation of data)  
  - Implement a fine-tuned LLM prompt system  

- **Comparative Analysis Requirements**: Compare the pattern matching and selected machine learning approach to recommend the better approach for each scenario.  

- **Application Development**:  
  - Build and deploy a **Streamlit** application for the detection of the entities.  
  - **Input Requirements**: The tool should accept a YAML file (example file is in `All_Conversations.zip`) as input.  
  - **Include two dropdowns**:  
    - One for selecting the approach (Pattern Matching, Machine Learning, or LLM)  
    - One for selecting the entity (Profanity Detection or Privacy and Compliance Violation) to analyze  
  - **Output Requirements**: Output a flag indicating the presence or absence of an entity.  

### For Question-3:

- **Visualization Requirements**: Create visual representations of silence and overtalk metrics.  

## Deliverables

1. **GitHub Repository** must include:
   - Well-documented code and deployed Streamlit application for both selected approaches (valid for Question-1 and Question-2).  
   - Visualization code (valid for Question-3).  
   - `README` file with setup and execution instructions (if required).  

2. **Technical Report** must include:
   - Implementation recommendations for the different scenarios (valid for Question-1 and Question-2)  
   - Visualization analysis (valid for Question-3)  
