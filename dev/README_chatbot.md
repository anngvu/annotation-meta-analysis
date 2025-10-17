# RDF Chatbot

A simple chatbot interface for querying DCA data models using natural language.

## Features

- 🤖 **Natural language queries** - Ask questions in plain English
- 📊 **SPARQL generation** - Automatically converts questions to SPARQL
- 🔍 **Real-time results** - Query the RDF graph instantly
- 💬 **Chat history** - Keep track of your conversation
- 🔧 **Query inspection** - See the generated SPARQL queries
- 📥 **Export results** - Download query results as CSV or JSON

## Setup

### 1. Install dependencies

```bash
pip install -r requirements_chatbot.txt
```

### 2. Set up your Anthropic API key

Create a `.env` file in the project directory:

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```
ANTHROPIC_API_KEY=your-api-key-here
```

The app will automatically load this when it starts.

### 3. Convert data models to RDF (if not already done)

```bash
# Convert data models to RDF
python3 convert_to_rdf.py

# Generate template enrichment metadata
python3 enrich_templates_to_rdf.py
```

This creates:
- Turtle files in `data_models_rdf/` directory (base data models)
- Enrichment files in `template_enrichment_rdf/` directory (template types, species, file types)

## Usage

### Run the chatbot

```bash
streamlit run rdf_chatbot.py
```

The app will open in your browser at `http://localhost:8501`

### Using the interface

1. **Load the graph**: Click "Load Graph" in the sidebar
2. **Ask questions**: Type your question in the chat input
3. **View results**: See the SPARQL query and results
4. **Explore**: Click "Generated SPARQL Query" to see the query
5. **Export data**: Download results as CSV or JSON using the download buttons

## Example Questions

### Templates
- "What templates are available?"
- "Show me all templates for CB project"
- "What is the description of FiletoIndividualMap?"
- "Show me all Record templates"
- "What Annotation templates are for Human samples?"
- "How many templates of each type are there?"

### Dependencies
- "What are the dependencies for FiletoIndividualMap?"
- "Which properties are required for this template?"
- "Show me all templates that require FileName"

### Properties
- "What properties are required?"
- "Show me all properties with validation rules"
- "What is the display name for FileName?"

### Validation Rules
- "What validation rules are used?"
- "Show me properties that require regex validation"
- "What are the validation rules for FileName?"

### Cross-project
- "Which projects have templates?"
- "How many templates does each project have?"
- "Show me all Human-related templates across projects"

## How It Works

1. **User asks a question** in natural language
2. **Claude generates SPARQL** using the provided schema and examples
3. **Query is executed** against the loaded RDF graph
4. **Results are displayed** in a readable format
5. **Export options** allow downloading results as CSV or JSON

## Exporting Results

After each query, download buttons appear below the results:

- **📥 Download CSV**: Export results as comma-separated values
  - Includes column headers
  - Full URIs preserved (not shortened)
  - Compatible with Excel, Google Sheets, etc.

- **📥 Download JSON**: Export results as JSON array
  - Each result row is an object
  - Keys are column names from the SPARQL query
  - Useful for programmatic processing

**Example CSV output:**
```csv
template,label,species
https://dca.app.sagebionetworks.org/EL/GenotypingHumanTemplate,GenotypingHumanTemplate,Human
https://dca.app.sagebionetworks.org/EL/IndividualHumanTemplate,IndividualHumanTemplate,Human
```

**Example JSON output:**
```json
[
  {
    "template": "https://dca.app.sagebionetworks.org/EL/GenotypingHumanTemplate",
    "label": "GenotypingHumanTemplate",
    "species": "Human"
  },
  {
    "template": "https://dca.app.sagebionetworks.org/EL/IndividualHumanTemplate",
    "label": "IndividualHumanTemplate",
    "species": "Human"
  }
]
```

## Architecture

```
User Question
     ↓
Claude API (NL → SPARQL)
     ↓
SPARQL Query
     ↓
rdflib Graph
     ↓
Results
```

## Customization

### Add more example queries

Edit the `EXAMPLE_QUERIES` in `rdf_chatbot.py` to help Claude generate better queries:

```python
EXAMPLE_QUERIES = """
6. Your custom query:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
SELECT ...
"""
```

### Modify the system prompt

Update `SYSTEM_PROMPT` to give Claude more context about your specific use case.

### Change the LLM model

The app currently uses `claude-sonnet-4-5-20250929` (latest Sonnet model). You can change to other models:

```python
message = client.messages.create(
    model="claude-sonnet-4-5-20250929",  # Current (default)
    # or
    model="claude-opus-4-20250514",  # More powerful (if available)
    # or
    model="claude-3-5-haiku-20241022",  # Faster/cheaper
    ...
)
```

## Troubleshooting

### Graph not loading
- Check that `data_models_rdf/` directory exists
- Ensure Turtle files are valid (run `convert_to_rdf.py` again)

### API errors
- Verify your Anthropic API key is correct
- Check your API usage limits

### Query errors
- Click "Generated SPARQL Query" to see what was generated
- Copy the query and test it manually
- Add more examples to `EXAMPLE_QUERIES` to improve generation

## Alternative Frameworks

If you want to try different frameworks:

### Gradio (simpler)
```python
import gradio as gr

def query_graph(question):
    # Your logic here
    return results

gr.ChatInterface(query_graph).launch()
```

### Flask (more control)
```python
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/query', methods=['POST'])
def query():
    question = request.json['question']
    # Your logic here
    return results
```

### FastAPI + React (production)
```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/query")
async def query(question: str):
    # Your logic here
    return {"results": results}
```

## Dependencies

- **streamlit**: Web UI framework
- **rdflib**: RDF graph and SPARQL queries
- **anthropic**: Claude API for NL→SPARQL conversion

## License

Same as the parent project.
