import requests
import xml.etree.ElementTree as ET
import urllib.parse
from typing import List, Dict, Any

# ArXiv API documentation: https://arxiv.org/help/api/user-manual
ARXIV_API_URL = "http://export.arxiv.org/api/query"

def search_arxiv(keywords: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches the arXiv API for papers matching the given keywords.

    Args:
        keywords: A list of string keywords (e.g., ['deep learning', 'quantum']).
        max_results: The maximum number of results to fetch.

    Returns:
        A list of dictionaries, where each dictionary represents a paper 
        and contains its title, authors, summary, ID, and primary category.
    """
    if not keywords:
        print("Error: Keywords list cannot be empty.")
        return []

    # 1. Construct the search query string. 
    # The arXiv API format is 'field:term+operator+field:term...'.
    # We search for all keywords across all fields ('all').
    query_parts = [f"all:{urllib.parse.quote(k)}" for k in keywords]
    search_query = "+AND+".join(query_parts)

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
    }

    print(f"Searching arXiv for: '{' AND '.join(keywords)}' (Max: {max_results} results)...")
    
    try:
        # 2. Make the request to the arXiv API
        response = requests.get(ARXIV_API_URL, params=params, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        return []

    # 3. Parse the XML response
    try:
        # ArXiv returns XML in the Atom format, which requires namespaces
        root = ET.fromstring(response.content)
        
        # Define namespaces for easy element searching
        namespaces = {'atom': 'http://www.w3.org/2005/Atom', 
                      'arxiv': 'http://arxiv.org/schemas/atom'}
        
        papers = []
        
        # Find all 'entry' tags which represent individual papers
        for entry in root.findall('atom:entry', namespaces):
            title = entry.find('atom:title', namespaces).text.strip() if entry.find('atom:title', namespaces) is not None else "N/A"
            summary = entry.find('atom:summary', namespaces).text.strip() if entry.find('atom:summary', namespaces) is not None else "N/A"
            
            # Extract authors
            authors = []
            for author_elem in entry.findall('atom:author', namespaces):
                name = author_elem.find('atom:name', namespaces).text
                if name:
                    authors.append(name)
            
            # Extract the main link (ID) and category
            arxiv_id = entry.find('atom:id', namespaces).text if entry.find('atom:id', namespaces) is not None else "N/A"
            primary_cat = entry.find('arxiv:primary_category', namespaces).attrib.get('term') if entry.find('arxiv:primary_category', namespaces) is not None else "N/A"
            
            paper_data = {
                "title": title,
                "authors": authors,
                "summary": summary,
                "arxiv_id": arxiv_id,
                "primary_category": primary_cat,
            }
            papers.append(paper_data)
            
        return papers
        
    except ET.ParseError as e:
        print(f"Error parsing XML response: {e}")
        return []


def print_papers(papers: List[Dict[str, Any]]):
    """Prints the retrieved paper information in a readable format."""
    if not papers:
        print("\nNo papers found matching the search criteria.")
        return

    print(f"\n--- Found {len(papers)} Papers ---")
    for i, paper in enumerate(papers, 1):
        print("-" * 60)
        print(f"[{i}] Title: {paper['title']}")
        print(f"    Authors: {', '.join(paper['authors'])}")
        print(f"    Category: {paper['primary_category']}")
        print(f"    Link: {paper['arxiv_id']}")
        
        # Print a snippet of the summary
        snippet = paper['summary'].replace('\n', ' ').split('.')[0] + '...'
        print(f"    Summary Snippet: {snippet}")
        
    print("-" * 60)
    print("Search complete.")


# --- Example Usage ---
if __name__ == "__main__":
    # Define your keywords here
    search_keywords = ["user interface", "LLM"]
    
    # Define the number of results you want
    limit = 5 

    results = search_arxiv(search_keywords, max_results=limit)
    
    print_papers(results)
