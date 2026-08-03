# LangChain Integration Specification

## AI-Assisted Qualitative Research Platform (v1.0)

### Purpose

This document defines how LangChain should be integrated into the AI-Assisted Qualitative Research Platform.

LangChain is used as an orchestration layer for LLM workflows—not as a replacement for application logic.

---

# Why LangChain?

The application performs multiple sequential AI tasks:

- Parse transcript
- Build prompts
- Run LLM analysis
- Validate outputs
- Aggregate scores
- Generate summaries
- Feed dashboards

LangChain provides reusable abstractions for this workflow.

---

# Core Responsibilities

## Prompt Management

Use ChatPromptTemplate to create reusable prompts.

Prompt variables:

- Research objective
- Codebook
- Scoring rubric
- Interview question
- Participant response

Prompts should be version-controlled.

---

## Structured Outputs

Use Pydantic schemas with LangChain structured outputs.

Example fields:

- score
- confidence
- evidence
- reason

Avoid manual JSON parsing.

---

## Runnable Pipeline

Pipeline:

Transcript
→ Prompt Template
→ LLM
→ Structured Output
→ Validation
→ Analytics

Each stage should be independently testable.

---

## Model Abstraction

Support:

- OpenAI
- Anthropic
- Gemini
- OpenRouter

Provider changes should only require configuration changes.

---

## Retry & Validation

Implement:

- Automatic retries
- Timeout handling
- Output validation
- Optional fallback model

---

# Recommended Folder Structure

```text
app/
├── prompts/
├── chains/
├── parsers/
├── models/
├── services/
├── dashboard/
└── config/
```

---

# Chains

## Transcript Chain

- Clean transcript
- Preserve Q&A
- Produce structured interview object

## Coding Chain

- Load codebook
- Score each dimension
- Extract evidence
- Generate reasoning

## Summary Chain

- Participant summary
- Themes
- Key findings

## Analytics Chain

Aggregate all interviews into:

- Overall scores
- Dimension averages
- Theme frequencies
- Dashboard metrics

---

# Why Not LangGraph?

Version 1 is a deterministic pipeline:

Upload
→ Parse
→ Analyze
→ Visualize

There are no autonomous agents.

LangGraph can be introduced later for multi-agent workflows.

---

# Why No Vector Database?

The initial dataset contains a small number of interviews.

No retrieval or semantic search infrastructure is required.

Avoid:

- FAISS
- ChromaDB
- Pinecone
- Weaviate

---

# Recommended Packages

Core:

- langchain
- langchain-openai
- langchain-anthropic
- pydantic
- python-docx
- pandas
- plotly
- streamlit
- pyyaml

Optional:

- langsmith
- tenacity

---

# Design Principles

- LangChain orchestrates the workflow.
- Prompts remain separate from business logic.
- Structured outputs are mandatory.
- Every score must include evidence and reasoning.
- Store prompt version, model, timestamp, and configuration for reproducibility.
