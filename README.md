# 🧠 AI Research Copilot

An autonomous research assistant that finds, reads, and summarizes scientific papers from arXiv — so you can focus on insights, not information overload.

---

## Features

* 🔍 Search arXiv based on your research goal
* 🧠 Analyze abstracts or full papers
* 📚 Build a local knowledge base using embeddings
* ✍️ Summarize findings into clear overviews
* 🤖 Multi-agent workflow powered by LangGraph
* ⚡ Runs on Groq’s fast, free Llama 3 8B API

---

## Setup

```bash
git clone https://github.com/vinod-polinati/ai-research-agent.git
cd ai-research-agent
pip install -r requirements.txt
pip install sentence-transformers "numpy<2.0.0"
```

Create a `.env` file:

```
GROQ_API_KEY=your_groq_api_key
```

---

## Usage

```python
from research_copilot import ResearchCopilot

copilot = ResearchCopilot()  # or specify model="llama3-8b-8192"

results = copilot.research(
    research_goal="Your research question here",
    max_papers=5,
    include_full_text=False
)

if 'findings' in results.get('findings', {}):
    for paper in results['findings']['findings']:
        print(paper['title'])

if 'summary' in results.get('summary', {}):
    print("\nSummary:")
    print(results['summary']['summary'])
```

---

## Tech Stack

* **Groq (Llama 3 8B)** for inference
* **ChromaDB + Sentence Transformers** for local embeddings
* **LangGraph** for orchestrating agent workflows

---
