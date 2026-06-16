# HELIOS — Hypothesis Exploration with LLM-driven Intelligent Orchestration System

HELIOS is a web-based prototype for automated hypothesis-driven exploratory data analysis over tabular datasets. It combines heuristic search, statistical validation, visual analytics, and LLM-based agents to support the generation, interpretation, and refinement of statistically grounded hypotheses.

The current version runs as a local web application with:

- a static HTML/JavaScript frontend;
- a Python FastAPI backend;
- statistical validation with one-sample t-test, Welch's t-test, ANOVA, and Levene's test;
- visualizations such as table view, tree view, sunburst chart, hypothesis cloud, heatmap, and metric analysis;
- LLM support through OpenAI and Groq, with optional Gemini configuration.

## Repository structure

```text
.
├── index.html                 # Landing page
├── sheva.html                 # Main HELIOS analysis interface
├── main.py                    # FastAPI backend
├── utils.py                   # Statistical and algorithmic helper functions
├── sheva_core.js              # CSV parsing, state, preprocessing, data operations
├── sheva_ui.js                # UI rendering and interaction logic
├── generatehypotheses.js      # Hypothesis-generation orchestration in the frontend
├── ai_utilities.js            # Frontend calls to the backend LLM endpoints
├── visualizationtools.js      # Tables, tree, sunburst, heatmap, t-SNE and metric plots
├── tsne.js                    # t-SNE implementation used by the frontend
├── image2.png                 # Image used in the landing page
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment variables
└── .gitignore
```

## Requirements

- Python 3.10 or newer recommended.
- A modern browser such as Chrome, Edge, or Firefox.
- At least one LLM API key if you want to use the AI-agent and AI-analysis features:
  - `OPENAI_API_KEY` for OpenAI models;
  - `GROQ_API_KEY` for Groq models;
  - `GEMINI_API_KEY` only if you use Gemini-related functionality.

The heuristic/statistical parts can be explored without an LLM key, but AI-generated hypotheses, advisor text, and narrative analysis require a configured provider.

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR-USER/helios.git
cd helios
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Linux/macOS:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## API keys

Do not hard-code API keys in the source code. Use environment variables instead.

On Linux/macOS:

```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export GROQ_API_KEY="your_groq_api_key_here"
export GEMINI_API_KEY="your_gemini_api_key_here"
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your_openai_api_key_here"
$env:GROQ_API_KEY="your_groq_api_key_here"
$env:GEMINI_API_KEY="your_gemini_api_key_here"
```

You only need to define the keys for the providers you intend to use.

## Running HELIOS locally

Start the backend:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open the frontend.

Option 1: open the landing page directly in your browser:

```text
index.html
```

Option 2: serve the frontend with a simple local HTTP server:

```bash
python -m http.server 5500
```

Then open:

```text
http://localhost:5500/index.html
```

Click **Start Analysis** to open the HELIOS interface. You can also open the interface directly at:

```text
http://localhost:5500/sheva.html
```

The frontend expects the backend to be available at:

```text
http://localhost:8000
```

## Basic workflow

1. Open `index.html` or `sheva.html`.
2. Upload a CSV file.
3. Select the target variable.
4. Optionally map binary columns and discretize numeric columns.
5. Add a dataset description or user intent if relevant.
6. Choose hypothesis-generation methods.
7. Generate hypotheses.
8. Explore significant hypotheses in the visualizations.
9. Use the AI analysis panel to generate a narrative summary and suggested next steps.
10. Download the hypotheses JSON if needed.

## Notes for development

- The current frontend uses absolute backend calls to `http://localhost:8000`. If you deploy the backend elsewhere, update the fetch URLs in `ai_utilities.js` and `sheva_ui.js`.
- External frontend libraries are loaded through CDNs: Tailwind, Font Awesome, Chart.js, Plotly, and D3. An internet connection is needed for the current frontend unless these libraries are vendored locally.
- Keep API keys out of GitHub. Use environment variables or a local `.env` file that is ignored by Git.
- The application is a research prototype and should be validated carefully before use in high-stakes analytical settings.

## Publishing to GitHub

Create a new empty repository on GitHub, then run:

```bash
git init
git add .
git commit -m "Initial HELIOS release"
git branch -M main
git remote add origin https://github.com/YOUR-USER/helios.git
git push -u origin main
```

For future updates:

```bash
git status
git add .
git commit -m "Describe the update"
git push
```
