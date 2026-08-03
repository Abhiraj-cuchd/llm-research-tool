# AI-Assisted Qualitative Research Platform

## Technical Specification (v1.0)

## Project Overview

### Goal

Develop a Streamlit-based web application that assists qualitative
researchers in analyzing interview transcripts related to **precarity**,
**intimate partner violence (IPV)**, and **psychological wellbeing**.

The system is **not** intended to replace researchers. Instead, it acts
as an AI-assisted qualitative coding platform that:

-   Reads interview transcripts
-   Performs theory-driven coding using an LLM
-   Extracts evidence
-   Assigns multidimensional precarity scores
-   Generates visual analytics
-   Exports structured datasets

The application should be generic enough that future research projects
can define their own codebooks.

------------------------------------------------------------------------

# Primary Users

-   Researchers
-   Psychology researchers
-   PhD scholars
-   Social science researchers

------------------------------------------------------------------------

# Input

Researchers upload a ZIP file.

    Study.zip
    ├── Participant1.docx
    ├── Participant2.docx
    ├── ...
    └── Participant14.docx

Each DOCX contains a complete interview transcript.

------------------------------------------------------------------------

# Processing Pipeline

``` text
ZIP Upload
    ↓
Extract DOCX Files
    ↓
Read DOCX
    ↓
Parse Transcript
    ↓
Identify Questions & Responses
    ↓
Create Structured Interview JSON
    ↓
LLM Qualitative Coding
    ↓
Generate Scores
    ↓
Extract Evidence
    ↓
Generate Dashboards
    ↓
Export Results
```

------------------------------------------------------------------------

# Interview Parsing

Each transcript is converted into structured JSON.

Example:

``` json
{
  "participant": "P11",
  "questions": [
    {
      "question": "How was life after divorce?",
      "answer": "Many won't understand this but peace is a luxury..."
    }
  ]
}
```

------------------------------------------------------------------------

# AI Coding

The system **does not perform generic sentiment analysis**.

Instead, it performs **theory-driven qualitative coding** using a
configurable codebook.

## Coding Dimensions (v1)

-   Financial Precarity
-   Employment Precarity
-   Housing Precarity
-   Social Support Precarity
-   Institutional Precarity
-   Psychological Precarity

Future dimensions should be configurable.

------------------------------------------------------------------------

## Expected LLM Output

``` json
{
  "financial_precarity": {
    "score": 5,
    "confidence": 0.95,
    "evidence": [
      "My whole gold was taken by him.",
      "Leaving her in daycare wasn't affordable."
    ],
    "reason": "Participant experienced severe financial abuse and inability to work."
  }
}
```

------------------------------------------------------------------------

# Overall Score

The application should derive an overall score from weighted dimensions.

Example weights:

  Dimension         Weight
  --------------- --------
  Financial             20
  Employment            20
  Housing               15
  Institutional         20
  Psychological         15
  Social                10

Researchers should be able to edit these weights.

------------------------------------------------------------------------

# Study Dashboard

## KPI Cards

-   Total Participants
-   Average Overall Score
-   Highest Dimension
-   Lowest Dimension
-   Most Frequent Theme
-   Most Frequent Evidence
-   Average AI Confidence

## Visualizations

-   Overall precarity distribution
-   Dimension averages
-   Theme frequency
-   Evidence frequency
-   Participant ranking
-   Question-wise comparison
-   Correlation heatmaps (if demographic/quantitative data available)

------------------------------------------------------------------------

# Question-wise Analysis

Researchers can select a question and view:

-   All participant responses
-   AI-generated synthesis
-   Common themes
-   Contrasting perspectives

------------------------------------------------------------------------

# Individual Dashboard

Each participant page includes:

-   Overall precarity score
-   Radar chart
-   Dimension cards
-   Timeline of significant life events
-   AI-generated summary
-   Supporting evidence with quotations
-   Confidence scores

Each dimension card contains:

-   Score
-   Evidence
-   Reasoning
-   Confidence

------------------------------------------------------------------------

# Search

Researchers can search concepts such as:

-   Financial abuse
-   Child custody
-   Police
-   Education
-   Financial independence

The system highlights relevant transcript sections.

------------------------------------------------------------------------

# Export

Supported formats:

-   CSV
-   Excel
-   JSON
-   PDF Report

CSV fields:

-   Participant
-   Financial
-   Employment
-   Housing
-   Institutional
-   Psychological
-   Social
-   Overall

------------------------------------------------------------------------

# Configuration

Researchers can configure:

-   Codebook
-   Dimension names
-   Prompt template
-   Scoring scale
-   Weighting

Supported scoring scales:

-   0--5
-   0--10
-   0--100

------------------------------------------------------------------------

# Technology Stack

## Frontend

-   Streamlit

## Backend

-   Python

## LLM Providers

-   OpenAI
-   Anthropic
-   Gemini
-   OpenRouter-compatible APIs

## Parsing

-   python-docx

## Visualization

-   Plotly
-   Altair

## Data Processing

-   Pandas
-   NumPy

## Configuration

-   YAML

## Export

-   openpyxl
-   reportlab

------------------------------------------------------------------------

# System Architecture

``` text
Streamlit UI
      ↓
Upload Module
      ↓
DOCX Parser
      ↓
Transcript Cleaner
      ↓
Prompt Builder
      ↓
LLM Client
      ↓
JSON Validator
      ↓
Score Calculator
      ↓
Analytics Engine
      ↓
Dashboards
      ↓
Export Engine
```

------------------------------------------------------------------------

# Design Principles

## 1. Research Transparency

Every score must include:

-   Evidence (quotes)
-   Explanation
-   Transcript location
-   Confidence

No unexplained scores.

## 2. Human-in-the-Loop

Researchers can:

-   Edit scores
-   Modify evidence
-   Add/remove codes
-   Save reviewed annotations

AI suggestions are editable.

## 3. Reproducibility

Store:

-   LLM model
-   Prompt version
-   Codebook version
-   Timestamp
-   Configuration

------------------------------------------------------------------------

# Future Enhancements

-   Multi-coder comparison
-   Cohen's Kappa / Krippendorff's Alpha
-   Custom codebook builder
-   Automatic thematic analysis
-   NVivo / Atlas.ti export
-   Collaboration
-   REST API
-   Longitudinal studies

------------------------------------------------------------------------

# Research Positioning

This platform should be presented as an **AI-Assisted Qualitative Coding
Platform**, not a generic sentiment analysis tool.

Core workflow:

1.  Upload interview transcripts.
2.  Parse interview structure.
3.  Apply theory-driven qualitative coding using an LLM.
4.  Extract evidence and reasoning.
5.  Compute multidimensional precarity scores.
6.  Visualize participant-level and study-level insights.
7.  Export structured data for further statistical analysis.

The emphasis is on **augmenting** qualitative researchers with
transparent, evidence-backed AI assistance rather than replacing human
judgment.
