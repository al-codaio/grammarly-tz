# Grammarly Support Chatbot with TensorZero

A production-ready customer support chatbot built with LangGraph and optimized using TensorZero. This application demonstrates how to build an AI-powered support system that improves over time through automated optimization techniques.

## 🚀 Features

- **Intent Classification**: Automatically categorizes customer queries into support categories
- **Intelligent Response Generation**: Provides helpful, context-aware responses
- **Self-Optimization**: Uses TensorZero for continuous improvement through:
  - Dynamic In-Context Learning (DICL)
  - Automated prompt engineering (MIPRO)
  - Supervised fine-tuning
- **Human Escalation**: Intelligently identifies when human support is needed
- **Performance Tracking**: Comprehensive metrics and visualization
- **LangGraph Studio Compatible**: Visual debugging and testing

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+
- OpenAI API key
- At least 4GB of available RAM

## 🛠️ Setup

### 1. Clone and Navigate

```bash
cd /home/alchen/claude/grammarly-tz
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Launch Services

```bash
docker-compose up -d
```

This starts:
- **ClickHouse**: Data storage for TensorZero (port 8123)
- **TensorZero Gateway**: LLM gateway and optimization engine (port 3000)
- **TensorZero UI**: Monitoring and optimization interface (port 4000)
- **LangGraph App**: The chatbot application (port 8000)

### 4. Verify Services

```bash
# Check health
curl http://localhost:8000/health

# Access UIs
# TensorZero UI: http://localhost:4000
# API Docs: http://localhost:8000/docs
```

## 📊 Data Collection & Training

### 1. Scrape Help Articles (Optional)

```bash
cd scripts
python scrape_grammarly_help.py
```

### 2. Generate Training Dataset

```bash
python generate_dataset.py
```

This creates synthetic customer queries with:
- Diverse intents (technical support, billing, features, etc.)
- Structured JSON outputs for training
- Train/validation/test splits

## 🧪 Using the Chatbot

### Via API

```python
import httpx

response = httpx.post("http://localhost:8000/chat", json={
    "query": "I can't get Grammarly to work in Google Docs",
    "user_context": {
        "platform": "chrome",
        "product": "grammarly_premium"
    }
})

print(response.json())
```

### Via LangGraph Studio

1. Install LangGraph Studio
2. Open the project directory
3. The entry point is configured in `langgraph/app.py`

## 🔧 Optimization Workflow

### 1. Collect Initial Data

Run the chatbot with baseline variants to collect inference data:

```bash
# The app randomly samples between gpt-4o and gpt-4o-mini
# All inferences are automatically logged to ClickHouse
```

### 2. Apply DICL (Dynamic In-Context Learning)

DICL automatically selects relevant examples from successful interactions:

```bash
# Data is automatically used by the gpt_4o_mini_dicl variant
# No manual intervention needed
```

### 3. Run MIPRO Optimization

For automated prompt engineering:

```bash
cd /home/alchen/claude/tensorzero/recipes/mipro
python mipro.ipynb  # Adapt for this use case
```

### 4. Supervised Fine-Tuning

Use the TensorZero UI (http://localhost:4000) to:
1. Navigate to "Supervised Fine-Tuning"
2. Select function and metrics
3. Start fine-tuning job
4. Add the fine-tuned model to `config/tensorzero.toml`

## 📈 Evaluation & Monitoring

### Run Evaluation

```bash
cd scripts
python evaluate_variants.py
```

This generates:
- Performance comparison charts
- Detailed metrics (accuracy, latency, quality)
- Recommendations for production deployment

### View Results

Results are saved to `data/results/`:
- `variant_comparison.png`: Visual performance comparison
- `evaluation_metrics.csv`: Detailed metrics
- `evaluation_report.json`: Summary and recommendations

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   LangGraph     │────▶│   TensorZero     │────▶│    OpenAI       │
│   Application   │     │    Gateway       │     │    Models       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         │                       ▼
         │              ┌─────────────────┐
         │              │   ClickHouse    │
         │              │   (Metrics)     │
         │              └─────────────────┘
         ▼
┌─────────────────┐
│  LangGraph      │
│  Checkpointer   │
└─────────────────┘
```

## 📁 Project Structure

```
grammarly-tz/
├── config/               # TensorZero configuration
│   ├── tensorzero.toml  # Main config with functions/variants
│   └── functions/       # Prompt templates and schemas
├── langgraph/           # LangGraph application
│   ├── app.py          # Main graph definition
│   ├── nodes.py        # Processing nodes
│   ├── state.py        # State management
│   └── server.py       # FastAPI wrapper
├── scripts/             # Data and evaluation scripts
│   ├── scrape_grammarly_help.py
│   ├── generate_dataset.py
│   └── evaluate_variants.py
├── utils/               # Shared utilities
│   └── tensorzero_client.py
├── data/                # Data storage
│   ├── scraped/        # Help articles
│   ├── processed/      # Training datasets
│   └── results/        # Evaluation outputs
├── docker-compose.yml   # Service orchestration
├── Dockerfile          # App container
└── requirements.txt    # Python dependencies
```

## 🎯 Key Concepts

### Variants

The system tests multiple model variants:
- **gpt_4o**: High-quality baseline
- **gpt_4o_mini**: Cost-effective option
- **gpt_4o_mini_dicl**: With dynamic examples
- **gpt_4o_mini_fine_tuned**: After training

### Metrics

- **intent_accuracy**: Classification accuracy
- **response_relevance**: Response quality (0-1)
- **resolution_potential**: Can resolve without human
- **customer_satisfaction**: Predicted satisfaction

### Optimization Strategies

1. **Baseline**: Collect data with standard prompts
2. **DICL**: Use successful examples dynamically
3. **MIPRO**: Optimize prompts algorithmically
4. **Fine-tuning**: Train custom models

## 🔍 Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs tensorzero
docker-compose logs clickhouse

# Restart services
docker-compose down
docker-compose up -d
```

### API Errors

- Verify OpenAI API key is set correctly
- Check TensorZero Gateway health: `curl http://localhost:3000/health`
- Ensure ClickHouse is running: `docker-compose ps`

### Performance Issues

- Increase Docker memory allocation
- Use `gpt_4o_mini` variants for faster responses
- Enable response streaming in production

## 🚀 Production Deployment

1. **Security**: Use environment-specific secrets
2. **Scaling**: Deploy TensorZero Gateway behind a load balancer
3. **Monitoring**: Set up alerts for error rates and latency
4. **Backup**: Regular ClickHouse backups for inference data
5. **A/B Testing**: Use TensorZero's variant weights for gradual rollout

## 📚 Next Steps

1. **Expand Dataset**: Add more query patterns and edge cases
2. **Multi-turn Conversations**: Enhance context handling
3. **RAG Integration**: Connect to Grammarly's knowledge base
4. **Custom Metrics**: Add business-specific success metrics
5. **Multi-language Support**: Extend to non-English queries
