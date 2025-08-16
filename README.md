# Grammarly Support Chatbot with TensorZero

AI-powered customer support chatbot with self-optimization through TensorZero.

## Features

- Intent classification and intelligent response generation
- Self-optimization via DICL, MIPRO, and fine-tuning
- Human escalation detection
- Performance tracking and metrics
- LangGraph Studio compatible

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- OpenAI API key

## Setup

```bash
# Configure environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Start services
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

Services:
- TensorZero UI: http://localhost:4000
- API Docs: http://localhost:8000/docs

## Data & Training

```bash
cd scripts

# Optional: Scrape help articles
python scrape_grammarly_help.py

# Generate training dataset
python generate_dataset.py
```

## Usage

```python
import httpx

response = httpx.post("http://localhost:8000/chat", json={
    "query": "I can't get Grammarly to work in Google Docs",
    "user_context": {
        "platform": "chrome",
        "product": "grammarly_premium"
    }
})
```

## Optimization Workflow

1. **Collect Data**: App randomly samples between gpt-4o and gpt-4o-mini
2. **DICL**: Automatically uses successful examples (gpt_4o_mini_dicl variant)
3. **MIPRO**: Run prompt optimization in `tensorzero/recipes/mipro`
4. **Fine-tuning**: Use TensorZero UI → Supervised Fine-Tuning

## Evaluation

```bash
cd scripts
python evaluate_variants.py
```

Results in `data/results/`:
- `variant_comparison.png`: Performance comparison
- `evaluation_metrics.csv`: Detailed metrics
- `evaluation_report.json`: Summary

## Architecture

```
LangGraph App → TensorZero Gateway → OpenAI Models
                      ↓
                 ClickHouse (Metrics)
```

## Project Structure

```
config/           # TensorZero configuration
langgraph/        # LangGraph application  
scripts/          # Data and evaluation
utils/            # Shared utilities
data/             # Data storage
docker-compose.yml
```

## Key Concepts

**Variants**: gpt_4o, gpt_4o_mini, gpt_4o_mini_dicl, gpt_4o_mini_fine_tuned

**Metrics**: intent_accuracy, response_relevance, resolution_potential, customer_satisfaction

**Optimization**: Baseline → DICL → MIPRO → Fine-tuning

## Troubleshooting

```bash
# Check logs
docker-compose logs [service]

# Restart
docker-compose down && docker-compose up -d
```

**Known Issues**:
- DICL variants may error in UI due to input format differences
- TensorZero requires UUID v7 format
- Using TensorZero 2025.7.2 (migration issues with latest)

## Production Deployment

- Use environment-specific secrets
- Deploy TensorZero Gateway behind load balancer
- Set up monitoring and alerts
- Regular ClickHouse backups
- Use variant weights for A/B testing
