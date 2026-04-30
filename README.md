# 🔬 AI Research Agent — Multi-Agent Research System

> **Give it a topic. It researches the web, analyzes data, fact-checks claims, and writes a professional report — all autonomously.**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-Powered-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 🎯 What It Does

This is a **production-grade multi-agent AI system** that automates deep research on any topic. Instead of a single LLM call, it uses **specialized AI agents** that collaborate:

| Agent | Role |
|-------|------|
| 🎯 **Orchestrator** | Breaks down the research topic into subtasks and coordinates all agents |
| 🔍 **Researcher** | Searches the web, scrapes pages, and gathers raw information |
| 📊 **Analyst** | Analyzes gathered data, finds patterns, extracts key statistics |
| ✅ **Fact Checker** | Validates claims and cross-references sources |
| ✍️ **Writer** | Produces a structured, cited, professional report |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Real-time UI)                │
│              WebSocket ← Live Agent Updates               │
├─────────────────────────────────────────────────────────┤
│                    FastAPI Backend                        │
│              REST API + WebSocket Server                  │
├─────────────────────────────────────────────────────────┤
│                 Agent Orchestration Layer                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │Researcher│  │ Analyst  │  │FactCheck │  │ Writer  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
├───────┼──────────────┼──────────────┼─────────────┼──────┤
│       │         Tool Layer          │             │      │
│  ┌────┴────┐  ┌─────┴─────┐  ┌─────┴────┐  ┌────┴───┐  │
│  │Web Search│  │Data Tools │  │Vector DB │  │Report  │  │
│  │Scraper  │  │Analyzer   │  │ChromaDB  │  │Gen     │  │
│  └─────────┘  └───────────┘  └──────────┘  └────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/mehessamit-dotcom/ai-research-agent.git
cd ai-research-agent
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env with your API keys (Groq is free!)
```

### 3. Run
```bash
python -m src.main
```
Open `http://localhost:8000` in your browser.

### 4. Research!
Enter a topic, watch the agents work in real-time, and download your report.

## 🔑 API Keys

| Provider | Free Tier | Get Key |
|----------|-----------|---------|
| **Groq** (recommended) | ✅ Yes | [console.groq.com](https://console.groq.com) |
| **OpenAI** | ❌ Paid | [platform.openai.com](https://platform.openai.com) |

## 📁 Project Structure
```
ai-research-agent/
├── src/
│   ├── main.py              # FastAPI application entry point
│   ├── agents/              # AI agent implementations
│   │   ├── orchestrator.py  # Task decomposition & coordination
│   │   ├── researcher.py    # Web research agent
│   │   ├── analyst.py       # Data analysis agent
│   │   ├── fact_checker.py  # Fact verification agent
│   │   └── writer.py        # Report writing agent
│   ├── core/                # Core infrastructure
│   │   ├── llm.py           # LLM provider abstraction
│   │   ├── prompts.py       # All prompt templates
│   │   └── memory.py        # Research memory management
│   ├── tools/               # Agent tools
│   │   ├── web_search.py    # DuckDuckGo search
│   │   ├── scraper.py       # Web page scraping
│   │   └── document_loader.py # PDF/document processing
│   ├── vectorstore/         # Vector database
│   │   └── store.py         # ChromaDB integration
│   ├── reports/             # Report generation
│   │   ├── generator.py     # HTML/PDF report builder
│   │   └── templates/       # Report HTML templates
│   └── models/              # Data models
│       └── schemas.py       # Pydantic schemas
├── frontend/                # Web UI
│   ├── index.html
│   ├── css/styles.css
│   └── js/app.js
├── output/                  # Generated reports
├── tests/                   # Test suite
├── .env.example
├── requirements.txt
└── Dockerfile
```

## 🛠️ Tech Stack

- **LLM**: Groq (Llama 3) / OpenAI (GPT-4)
- **Framework**: LangChain
- **Backend**: FastAPI + WebSockets
- **Frontend**: Vanilla HTML/CSS/JS (real-time agent visualization)
- **Vector DB**: ChromaDB
- **Search**: DuckDuckGo (free, no API key)
- **Scraping**: BeautifulSoup4 + httpx

## 📄 License

MIT License — use it, modify it, ship it.
