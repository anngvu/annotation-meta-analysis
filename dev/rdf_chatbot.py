#!/usr/bin/env python3
"""
RDF Chatbot - Query data model graphs using natural language.

A simple chatbot interface for querying DCA data models converted to RDF/Turtle.
Uses LLM to convert natural language questions to SPARQL queries.
"""

import streamlit as st
from rdflib import Graph, Namespace
from pathlib import Path
import anthropic
import os
import json
import csv
from io import StringIO
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define namespaces
DCA = Namespace("https://dca.app.sagebionetworks.org/vocab/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

# SPARQL query examples for the LLM
EXAMPLE_QUERIES = """
Example SPARQL queries:

1. Get all templates (templates have requiresDependency):
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?template ?label ?description
WHERE {
  ?template dca:requiresDependency ?dep ;
            rdfs:label ?label .
  OPTIONAL { ?template rdfs:comment ?description }
}

2. Get dependencies for a specific template:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?dependency
WHERE {
  ?template rdfs:label "FiletoIndividualMap" ;
            dca:requiresDependency ?dependency .
}

3. Get all validation rules:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?property ?rule
WHERE {
  ?property dca:validationRules/rdf:rest*/rdf:first ?rule .
}

4. Find required properties:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
SELECT ?property ?displayName
WHERE {
  ?property dca:displayName ?displayName ;
            dca:required true .
}

5. Cross-project template search:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?project ?label
WHERE {
  ?template dca:requiresDependency ?dep ;
            rdfs:label ?label .
  FILTER(STRSTARTS(STR(?template), "https://dca.app.sagebionetworks.org/"))
  BIND(REPLACE(STR(?template), "https://dca.app.sagebionetworks.org/([^/]+)/.*", "$1") AS ?project)
}

6. Count templates by project:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
SELECT ?project (COUNT(DISTINCT ?template) as ?count)
WHERE {
  ?template dca:requiresDependency ?dep .
  FILTER(STRSTARTS(STR(?template), "https://dca.app.sagebionetworks.org/"))
  BIND(REPLACE(STR(?template), "https://dca.app.sagebionetworks.org/([^/]+)/.*", "$1") AS ?project)
}
GROUP BY ?project
ORDER BY DESC(?count)

7. Find Record templates:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?template ?label
WHERE {
  ?template a dca:RecordTemplate ;
            rdfs:label ?label .
}

8. Find Annotation templates with species:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?template ?label ?species
WHERE {
  ?template a dca:AnnotationTemplate ;
            rdfs:label ?label ;
            dca:species ?species .
}

9. Count templates by type:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
SELECT ?type (COUNT(?template) as ?count)
WHERE {
  ?template a ?type .
  FILTER(?type IN (dca:RecordTemplate, dca:AnnotationTemplate, dca:UnconfiguredTemplate))
}
GROUP BY ?type

10. Find unconfigured templates:
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?template ?label
WHERE {
  ?template a dca:UnconfiguredTemplate ;
            rdfs:label ?label .
}
"""

SYSTEM_PROMPT = f"""You are a SPARQL query assistant for DCA (Data Curator App) data models.

The RDF graph contains data models with:
- Templates - classes that have dca:requiresDependency (forms for data submission)
  - Can be typed as dca:RecordTemplate, dca:AnnotationTemplate, or dca:UnconfiguredTemplate
  - dca:RecordTemplate - templates for recording entities (e.g., Biospecimen, Individual)
  - dca:AnnotationTemplate - templates for annotating files/data (e.g., assays, file metadata)
  - dca:UnconfiguredTemplate - templates that haven't been categorized yet
  - May have dca:species (e.g., "Human", "Animal model", "Multi-species")
  - May have dca:fileType (e.g., "FASTQ", "BAM", "Various")
- Properties - fields that may have dca:validationRules
- Dependencies - dca:requiresDependency points to required fields
- Validation rules - dca:validationRules contains constraints

IMPORTANT: Templates are identified by having dca:requiresDependency, but can also be queried by type (dca:RecordTemplate, dca:AnnotationTemplate, or dca:UnconfiguredTemplate)

Available prefixes:
- dca: <https://dca.app.sagebionetworks.org/vocab/>
- rdfs: <http://www.w3.org/2000/01/rdf-schema#>
- rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
- Project-specific: cb:, adkp:, el:, etc. <https://dca.app.sagebionetworks.org/PROJECT/>

{EXAMPLE_QUERIES}

Convert the user's natural language question to a SPARQL query.
Respond ONLY with the SPARQL query, no explanation or markdown formatting.
"""


def load_rdf_graph(ttl_dir: Path, enrichment_dir: Path = None) -> Graph:
    """Load all Turtle files into a single RDF graph."""
    g = Graph()

    # Bind namespaces
    g.bind("dca", DCA)
    g.bind("rdfs", RDFS)

    # Load data model TTL files
    ttl_files = list(ttl_dir.glob("*.ttl"))

    for ttl_file in ttl_files:
        try:
            g.parse(ttl_file, format="turtle")
        except Exception as e:
            st.error(f"Error loading {ttl_file.name}: {e}")

    # Load enrichment TTL files if directory provided
    if enrichment_dir and enrichment_dir.exists():
        enrichment_files = list(enrichment_dir.glob("*.ttl"))
        for ttl_file in enrichment_files:
            try:
                g.parse(ttl_file, format="turtle")
            except Exception as e:
                st.error(f"Error loading enrichment {ttl_file.name}: {e}")

    return g


def nl_to_sparql(question: str, api_key: str) -> str:
    """Convert natural language question to SPARQL using Claude."""
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": question}
        ]
    )

    sparql_query = message.content[0].text.strip()

    # Clean up any markdown formatting
    if sparql_query.startswith("```"):
        lines = sparql_query.split("\n")
        sparql_query = "\n".join(lines[1:-1])

    return sparql_query


def execute_sparql(graph: Graph, query: str):
    """Execute SPARQL query and return results."""
    try:
        results = graph.query(query)
        return results, None
    except Exception as e:
        return None, str(e)


def format_results(results) -> str:
    """Format SPARQL results as a readable string."""
    if not results:
        return "No results found."

    output = []

    # Get column names
    cols = [str(var) for var in results.vars]

    # Format as table
    output.append(" | ".join(cols))
    output.append("-" * (len(cols) * 20))

    for row in results:
        values = []
        for col in cols:
            val = getattr(row, col)
            if val:
                # Shorten URIs for readability
                val_str = str(val)
                if val_str.startswith("https://dca.app.sagebionetworks.org/"):
                    val_str = val_str.replace("https://dca.app.sagebionetworks.org/", "")
                values.append(val_str[:50])
            else:
                values.append("")
        output.append(" | ".join(values))

    return "\n".join(output)


def results_to_csv(results) -> str:
    """Convert SPARQL results to CSV format."""
    if not results:
        return ""

    output = StringIO()
    cols = [str(var) for var in results.vars]
    writer = csv.writer(output)

    # Write header
    writer.writerow(cols)

    # Write rows
    for row in results:
        values = []
        for col in cols:
            val = getattr(row, col)
            values.append(str(val) if val else "")
        writer.writerow(values)

    return output.getvalue()


def results_to_json(results) -> str:
    """Convert SPARQL results to JSON format."""
    if not results:
        return "[]"

    cols = [str(var) for var in results.vars]
    data = []

    for row in results:
        row_dict = {}
        for col in cols:
            val = getattr(row, col)
            row_dict[col] = str(val) if val else None
        data.append(row_dict)

    return json.dumps(data, indent=2)


def main():
    st.set_page_config(page_title="RDF Chatbot", page_icon="🤖", layout="wide")

    st.title("🤖 DCA Data Model Chatbot")
    st.markdown("Ask questions about DCA data models in natural language")

    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API key input
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=os.environ.get("ANTHROPIC_API_KEY", ""),
            help="Enter your Anthropic API key"
        )

        # RDF directories
        ttl_dir = st.text_input(
            "Data Models Directory",
            value="data_models_rdf",
            help="Directory containing data model .ttl files"
        )

        enrichment_dir = st.text_input(
            "Template Enrichment Directory",
            value="template_enrichment_rdf",
            help="Directory containing template enrichment .ttl files"
        )

        if st.button("Load Graph"):
            with st.spinner("Loading RDF graph..."):
                g = load_rdf_graph(Path(ttl_dir), Path(enrichment_dir))
                st.session_state.graph = g

                # Count triples from each source
                base_graph = Graph()
                for f in Path(ttl_dir).glob("*.ttl"):
                    base_graph.parse(f, format="turtle")

                enrichment_graph = Graph()
                if Path(enrichment_dir).exists():
                    for f in Path(enrichment_dir).glob("*.ttl"):
                        enrichment_graph.parse(f, format="turtle")

                st.success(f"✅ Loaded {len(g):,} total triples")
                st.info(f"📊 Data models: {len(base_graph):,} triples | Template enrichment: {len(enrichment_graph):,} triples")

        st.markdown("---")
        st.markdown("### Example Questions")
        st.markdown("""
        - What templates are available?
        - Show me all Record templates
        - What Annotation templates are for Human samples?
        - What are the dependencies for FiletoIndividualMap?
        - Show me all required properties
        - What validation rules are used?
        - Which projects have templates?
        - How many templates by type?
        """)

    # Initialize session state
    if 'graph' not in st.session_state:
        st.session_state.graph = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Check if graph is loaded
    if st.session_state.graph is None:
        st.warning("⚠️ Please load the RDF graph from the sidebar first")
        return

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if question := st.chat_input("Ask a question about the data models..."):
        if not api_key:
            st.error("Please provide an Anthropic API key in the sidebar")
            return

        # Add user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Generate SPARQL query
        with st.chat_message("assistant"):
            with st.spinner("Generating SPARQL query..."):
                try:
                    sparql_query = nl_to_sparql(question, api_key)

                    # Show the generated query
                    with st.expander("Generated SPARQL Query"):
                        st.code(sparql_query, language="sparql")

                    # Execute query
                    results, error = execute_sparql(st.session_state.graph, sparql_query)

                    if error:
                        st.error(f"Query execution error: {error}")
                        response = f"Sorry, I couldn't execute that query. Error: {error}"
                    else:
                        # Format and display results
                        formatted = format_results(results)
                        st.code(formatted, language="text")

                        # Add export buttons if there are results
                        if len(results) > 0:
                            col1, col2, col3 = st.columns([1, 1, 4])

                            with col1:
                                csv_data = results_to_csv(results)
                                st.download_button(
                                    label="📥 Download CSV",
                                    data=csv_data,
                                    file_name="query_results.csv",
                                    mime="text/csv",
                                    key=f"csv_{len(st.session_state.messages)}"
                                )

                            with col2:
                                json_data = results_to_json(results)
                                st.download_button(
                                    label="📥 Download JSON",
                                    data=json_data,
                                    file_name="query_results.json",
                                    mime="application/json",
                                    key=f"json_{len(st.session_state.messages)}"
                                )

                        response = f"Found {len(results)} results:\n\n```\n{formatted}\n```"

                    st.session_state.messages.append({"role": "assistant", "content": response})

                except Exception as e:
                    st.error(f"Error: {e}")
                    response = f"Sorry, I encountered an error: {e}"
                    st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
