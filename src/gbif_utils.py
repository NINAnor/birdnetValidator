"""GBIF Species API utilities for dynamic species search."""

import urllib.parse
import urllib.request
import json

import streamlit as st

# GBIF Backbone Taxonomy dataset key — ensures clean, deduplicated results
_BACKBONE_DATASET_KEY = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"
_GBIF_SEARCH_URL = "https://api.gbif.org/v1/species/search"
_REQUEST_TIMEOUT = 5  # seconds


@st.cache_data(ttl=3600, show_spinner=False)
def search_species_gbif(query, limit=20):
    """Search the GBIF Backbone Taxonomy for species matching a query.

    Searches both scientific and vernacular (common) names.
    Returns a list of dicts with keys: scientific_name, vernacular_name, display.
    """
    if not query or len(query.strip()) < 2:
        return []

    params = {
        "q": query.strip(),
        "rank": "SPECIES",
        "limit": str(limit),
        "datasetKey": _BACKBONE_DATASET_KEY,
        "status": "ACCEPTED",
    }
    url = f"{_GBIF_SEARCH_URL}?{urllib.parse.urlencode(params)}"

    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []

    results = []
    seen = set()
    for item in data.get("results", []):
        scientific = item.get("canonicalName") or item.get("scientificName", "")
        if not scientific or scientific in seen:
            continue
        seen.add(scientific)

        # Extract first English vernacular name if available
        vernacular = ""
        for vn in item.get("vernacularNames", []):
            if vn.get("language", "").startswith("eng"):
                vernacular = vn.get("vernacularName", "")
                break
        # Fall back to any vernacular name
        if not vernacular and item.get("vernacularNames"):
            vernacular = item["vernacularNames"][0].get("vernacularName", "")

        if vernacular:
            display = f"{vernacular} ({scientific})"
        else:
            display = scientific

        results.append({
            "scientific_name": scientific,
            "vernacular_name": vernacular,
            "display": display,
        })

    return results


def search_species_for_searchbox(query, **kwargs):
    """Wrapper for st_searchbox: returns list of (display, scientific_name) tuples."""
    results = search_species_gbif(query)
    return [(r["display"], r["scientific_name"]) for r in results]
