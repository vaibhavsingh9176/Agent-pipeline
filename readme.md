# 🤖 Agent Pipeline

A small multi-agent AI app. You describe a task, a **planning agent** splits it into steps, a **specialist agent** handles each step, and a **synthesis agent** merges everything into one final answer.

```
PLAN  →  SPAWN  →  EXECUTE  →  MERGE
```

## How it works

1. **Plan**: the planner agent turns your request into an ordered list of steps (1 to 10), each with a title, a specialist role, and instructions.
2. **Spawn**: one specialist agent is created per step.
3. **Execute**: each agent runs once, and the outputs of earlier steps are passed to the next one as context.
4. **Merge**: a synthesis agent combines all outputs into a single, clean Markdown answer.

## Features

- Streamlit UI with a colorful, modern theme
- Provider-agnostic LLM wrapper: **Groq** (default) or **Mistral**, switched from `.env`
- Built-in request throttling and retry with exponential backoff on `429` rate limits
- Planner output is parsed defensively (handles stray markdown fences or extra text)
- Simple, readable orchestration code

## Project structure

```
agent-pipeline/
├── app.py              # Streamlit UI
├── orchestator.py      # make_plan(), run_step(), synthesize()
├── mistral_client.py   # LLM wrapper (Groq / Mistral), throttling, retries
├── requirements.txt
├── .env                # your keys (never commit this)
└── README.md
```

## Getting started

### 1. Clone and set up a virtual environment

```bash
git clone https://github.com/<your-username>/agent-pipeline.git
cd agent-pipeline

python -m venv venv
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

`requirements.txt`:

```
streamlit
python-dotenv
groq
mistralai
```

### 3. Configure `.env`

Get a free API key from [console.groq.com](https://console.groq.com), then create a `.env` file:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=openai/gpt-oss-20b

# Optional: use Mistral instead
# LLM_PROVIDER=mistral
# MISTRAL_API_KEY=your_mistral_key_here
# MISTRAL_MODEL=mistral-small-latest

# Optional tuning
# LLM_MIN_INTERVAL=2.0
# LLM_MAX_RETRIES=5
```

### 4. Run

```bash
streamlit run app.py
```

Open the URL shown in the terminal (usually http://localhost:8501).

## Configuration

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq` or `mistral` |
| `GROQ_API_KEY` | none | Required when using Groq |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Any model your Groq key can use |
| `MISTRAL_API_KEY` | none | Required when using Mistral |
| `MISTRAL_MODEL` | `mistral-small-latest` | Any Mistral model name |
| `LLM_MIN_INTERVAL` | `2.0` | Minimum seconds between requests |
| `LLM_MAX_RETRIES` | `5` | Retries after a `429` rate limit |

## Troubleshooting

- **`429 Rate limit exceeded`**: free tiers have strict limits. Increase `LLM_MIN_INTERVAL`, or switch to a smaller model.
- **`model_not_found` (404)**: providers retire models often. Check the provider's current model list and update `GROQ_MODEL` / `MISTRAL_MODEL`.
- **`pip` or `uvicorn` "Fatal error in launcher"**: you moved the project folder after creating the venv. Delete and recreate the venv, or run tools as `python -m pip ...`.

## Security

Never commit your `.env` file. Add it to `.gitignore`:

```
.env
venv/
__pycache__/
```

If a key is ever exposed, revoke it in the provider's console and create a new one.

## Roadmap

- [ ] Run independent steps in parallel
- [ ] Tool use (web search, code execution) for agents
- [ ] Save and reload past runs
- [ ] Export the final answer as PDF / Markdown

## License

MIT. See `LICENSE` for details.