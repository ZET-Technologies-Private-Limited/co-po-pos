# Supported LLM Models & Configuration

## Overview

The system supports multiple LLM providers with automatic fallback mechanisms. All providers offer similar capabilities for CO generation, Bloom detection, semantic mapping, and report generation.

---

## OpenAI Models

### Primary Models
- **GPT-4 Turbo** (gpt-4-turbo-preview)
  - Context: 128K tokens
  - Best for: Complex reasoning, precise CO generation
  - Cost: Higher
  - Recommended: Default choice

- **GPT-3.5 Turbo** (gpt-3.5-turbo)
  - Context: 4K tokens
  - Best for: Fast processing
  - Cost: Lower
  - Recommended: Quick operations

### Configuration
```python
from app.ai_engine.llm.llm_client import LLMClient

# Use OpenAI (default)
client = LLMClient(provider="openai")

# Generate CO from syllabus
response = await client.generate_structured(prompt)
```

### Requirements
- Environment Variable: `OPENAI_API_KEY`
- Python Package: `langchain-openai==0.0.8`, `openai==1.3.9`

---

## Google Gemini Models

### Primary Models
- **Gemini 1.5 Pro** (gemini-1.5-pro)
  - Context: 1M tokens (extended)
  - Best for: Large document analysis, comprehensive syllabi
  - Cost: Competitive
  - Recommended: For long contexts

- **Gemini 1.5 Flash** (gemini-1.5-flash)
  - Context: 1M tokens
  - Best for: Fast processing
  - Cost: Lower
  - Recommended: Quick turnaround

- **Gemini 1.0 Pro** (gemini-pro)
  - Context: 32K tokens
  - Best for: Standard operations
  - Cost: Budget-friendly
  - Recommended: General use

### Configuration
```python
from app.ai_engine.llm.llm_client import LLMClient

# Use Gemini
client = LLMClient(provider="gemini")

# Generate response
response = await client.generate_completion(prompt)
```

### Requirements
- Environment Variable: `GEMINI_API_KEY`
- Python Package: `langchain-google-genai==0.0.10`, `google-generativeai==0.3.0`

---

## Anthropic Claude Models

### Primary Models
- **Claude 3 Opus** (claude-3-opus-20240229)
  - Context: 200K tokens
  - Best for: Complex analysis, nuanced understanding
  - Cost: Higher
  - Recommended: Critical operations

- **Claude 3 Sonnet** (claude-3-sonnet-20240229)
  - Context: 200K tokens
  - Best for: Balanced performance
  - Cost: Moderate
  - Recommended: Most operations

- **Claude 3 Haiku** (claude-3-haiku-20240307)
  - Context: 200K tokens
  - Best for: Fast processing
  - Cost: Lower
  - Recommended: Quick operations

### Configuration
```python
from app.ai_engine.llm.llm_client import LLMClient

# Use Claude
client = LLMClient(provider="claude")

# Generate response
response = await client.generate_completion(prompt)
```

### Requirements
- Environment Variable: `ANTHROPIC_API_KEY`
- Python Package: `langchain-anthropic==0.1.1`, `anthropic==0.7.10`

---

## Multi-Provider Usage

### Dynamic Provider Selection
```python
from app.ai_engine.llm.llm_client import multi_llm_client

# Use OpenAI
response = await multi_llm_client.generate(
    prompt="Generate CO from syllabus",
    provider="openai"
)

# Use Gemini
response = await multi_llm_client.generate(
    prompt="...",
    provider="gemini"
)

# Use Claude
response = await multi_llm_client.generate(
    prompt="...",
    provider="claude"
)
```

### Provider Comparison
```python
# Get responses from all providers
results = await multi_llm_client.compare_providers(prompt)
# Returns: {"openai": "...", "gemini": "...", "claude": "..."}
```

### Automatic Fallback
```python
# If OpenAI fails, automatically try Gemini, then Claude
response = await client.generate_with_fallback(
    prompt="Generate CO outcomes",
    fallback_response="Default CO outcomes"
)
```

---

## Embedding Models

### OpenAI Embeddings
- **text-embedding-3-large**
  - Dimensions: 3072
  - Best for: High-quality semantic search
  - Recommended: Default choice

- **text-embedding-3-small**
  - Dimensions: 1536
  - Best for: Fast processing
  - Recommended: Quick operations

### Google Embeddings
- **models/embedding-001**
  - Dimensions: 768
  - Best for: Semantic similarity
  - Recommended: Gemini integration

### Configuration
```python
from app.ai_engine.embeddings.embedding_service import embedding_service

# Generate single embedding
embedding = await embedding_service.embed_text("Course outcome statement")

# Generate batch embeddings
embeddings = await embedding_service.embed_texts(["CO1", "CO2", "CO3"])

# Calculate similarity
similarity = embedding_service.cosine_similarity(emb1, emb2)
```

---

## Agent-to-Model Mapping

### CO Generation Agent
**Recommended**: Claude 3 Opus (best for nuanced CO statements)
**Fallback**: GPT-4 Turbo, Gemini 1.5 Pro

### Bloom Taxonomy Agent
**Recommended**: GPT-4 Turbo (best for keyword recognition)
**Fallback**: Claude 3 Opus, Gemini 1.5 Pro

### CO-PO Mapping Agent
**Recommended**: Gemini 1.5 Pro (large context for all outcomes)
**Fallback**: Claude 3 Opus, GPT-4 Turbo

### Exam Configuration Agent
**Recommended**: GPT-4 Turbo (structured output)
**Fallback**: Claude 3 Sonnet, Gemini 1.5 Flash

### Attainment Calculation Agent
**Recommended**: GPT-3.5 Turbo (simple calculations)
**Fallback**: Claude 3 Haiku, Gemini 1.5 Flash

### Reporting Agent
**Recommended**: Claude 3 Opus (narrative generation)
**Fallback**: GPT-4 Turbo, Gemini 1.5 Pro

---

## Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Gemini
GEMINI_API_KEY=...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# LLM Configuration
LLM_PROVIDER=openai              # Default provider
LLM_MODEL=gpt-4-turbo-preview    # Default model
LLM_TEMPERATURE=0.7              # Creativity (0-1)
LLM_MAX_TOKENS=2000              # Max response length

# Embeddings Configuration
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_PROVIDER=openai
```

---

## API Usage Examples

### Example 1: Generate CO from Syllabus
```python
from app.ai_engine.llm.llm_client import llm_client

syllabus = """
This course covers:
- Database design and normalization
- SQL query optimization
- Transaction management
- Data warehousing
"""

prompt = f"""Generate 5 Course Outcomes from this syllabus:
{syllabus}

Return JSON: {{"outcomes": [{{"code": "CO1", "statement": "...", "bloom_level": "..."}}]}}"""

response = await llm_client.generate_structured(prompt)
# Returns: {"outcomes": [{"code": "CO1", ...}, ...]}
```

### Example 2: Detect Bloom Level
```python
question = "Design a database schema for an e-commerce system"

prompt = f"""Determine Bloom level:
Question: {question}

Return JSON: {{"bloom_level": "...", "confidence": 0.0-1.0}}"""

response = await llm_client.generate_structured(prompt)
# Returns: {"bloom_level": "Create", "confidence": 0.95}
```

### Example 3: Semantic Similarity
```python
from app.ai_engine.embeddings.embedding_service import embedding_service

co_statement = "Students will be able to design database schemas"
po_statement = "Graduates will demonstrate mastery in database design"

co_embedding = await embedding_service.embed_text(co_statement)
po_embedding = await embedding_service.embed_text(po_statement)

similarity = embedding_service.cosine_similarity(co_embedding, po_embedding)
# Returns: 0.87 (high similarity)
```

---

## Cost Comparison

| Model | Input Cost | Output Cost | Use Case |
|-------|-----------|-----------|----------|
| GPT-4 Turbo | $10/1M | $30/1M | Complex reasoning |
| GPT-3.5 Turbo | $0.50/1M | $1.50/1M | Fast processing |
| Claude 3 Opus | $15/1M | $75/1M | Best quality |
| Claude 3 Sonnet | $3/1M | $15/1M | Balanced |
| Claude 3 Haiku | $0.25/1M | $1.25/1M | Budget |
| Gemini 1.5 Pro | $1.25/1M | $2.50/1M | Large context |
| Gemini 1.5 Flash | $0.075/1M | $0.30/1M | Fast |

---

## Performance Metrics

### Response Times (Approximate)
- GPT-4 Turbo: 2-5 seconds
- GPT-3.5 Turbo: 1-3 seconds
- Claude 3 Opus: 2-4 seconds
- Claude 3 Haiku: 1-2 seconds
- Gemini 1.5 Pro: 1-3 seconds
- Gemini 1.5 Flash: 1-2 seconds

### Quality Scores (1-10)
- GPT-4 Turbo: 9.5/10
- Claude 3 Opus: 9.3/10
- Gemini 1.5 Pro: 9.0/10
- Claude 3 Sonnet: 8.7/10
- GPT-3.5 Turbo: 8.3/10
- Claude 3 Haiku: 7.8/10
- Gemini 1.5 Flash: 8.0/10

---

## Troubleshooting

### API Key Not Found
```python
# Check environment
import os
print(os.environ.get("OPENAI_API_KEY"))  # Should not be None
```

### Model Not Available
```python
# Verify model name and API key are correct
# Try fallback provider
response = await multi_llm_client.generate(
    prompt="...",
    provider="claude"  # Fallback
)
```

### Rate Limiting
```python
# Implement exponential backoff
import asyncio

for attempt in range(3):
    try:
        response = await client.generate_completion(prompt)
        break
    except RateLimitError:
        await asyncio.sleep(2 ** attempt)
```

### High Costs
```python
# Use faster/cheaper models
client = LLMClient(provider="claude")  # Try Claude Haiku
# Or: GPT-3.5 Turbo, Gemini 1.5 Flash
```

---

## Recommendations

### For Production
- **Primary**: Claude 3 Opus (quality)
- **Fallback 1**: GPT-4 Turbo
- **Fallback 2**: Gemini 1.5 Pro

### For Development
- **Primary**: GPT-3.5 Turbo (cost-effective)
- **Fallback 1**: Gemini 1.5 Flash
- **Fallback 2**: Claude 3 Haiku

### For Scale
- **Primary**: Gemini 1.5 Pro (large context, cost-effective)
- **Fallback 1**: Claude 3 Sonnet
- **Fallback 2**: GPT-3.5 Turbo

---

## Updates & New Models

This document is maintained with latest available models. Check provider websites for new releases:
- OpenAI: https://platform.openai.com/docs/models
- Google: https://ai.google.dev/models
- Anthropic: https://docs.anthropic.com/en/docs/about-claude/models/latest
