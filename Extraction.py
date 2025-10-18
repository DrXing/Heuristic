import fitz # PyMuPDF for PDF handling
import json
import time
import requests # For making the API call

# --- CONFIGURATION ---
# NOTE: Replace the empty string below with your actual Gemini API Key
API_KEY = "AIzaSyBZ_5JnWp9mmlA9-UaQhcjpkj6-ibd8Xik"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"
# Note on Model: We use a fast model with preview access for structured output.

# Define the JSON schema for the desired output structure.
# This guides the LLM to provide clean, structured data.
HEURISTIC_SCHEMA1 = {
    "type": "ARRAY",
    "description": "A list of all distinct heuristic rules found in the document.",
    "items": {
        "type": "OBJECT",
        "properties": {
            "rule_id": {
                "type": "STRING",
                "description": "A short, unique identifier for the rule (e.g., 'H1', 'VisibilityOfSystemStatus')."
            },
            "rule_name": {
                "type": "STRING",
                "description": "A concise, descriptive name for the heuristic (e.g., 'Visibility of system status')."
            },
            "description": {
                "type": "STRING",
                "description": "The full, extracted text describing the heuristic rule."
            },
            "source_page": {
                "type": "NUMBER",
                "description": "The page number (1-indexed) where the rule was primarily found."
            }
        },
        "required": ["rule_id", "rule_name", "description", "source_page"]
    }
}

# --- PDF PROCESSING FUNCTIONS ---

def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extracts text from a PDF file page by page.

    Args:
        pdf_path: The file path to the PDF document.

    Returns:
        A list of dictionaries, where each dict contains 'page_num' and 'text'.
    """
    try:
        document = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF file at {pdf_path}: {e}")
        return []

    print(f"Successfully opened PDF: {pdf_path}. Total pages: {document.page_count}")
    page_texts = []
    for page_num in range(document.page_count):
        page = document.load_page(page_num)
        text = page.get_text()
        
        # Only process pages that have a decent amount of text
        if len(text.strip()) > 100:
            page_texts.append({
                "page_num": page_num + 1, # 1-indexed for human readability
                "text": text
            })
    
    document.close()
    print(f"Extracted content from {len(page_texts)} pages with substantial text.")
    return page_texts

# --- GEMINI API CALL FUNCTION ---

def call_gemini_for_extraction(page_data: dict, max_retries: int = 5) -> str | None:
    """
    Calls the Gemini API to extract heuristics using a structured JSON schema.
    Includes exponential backoff for reliable API access.
    """
    page_num = page_data['page_num']
    text = page_data['text']

    system_prompt = (
        "You are an expert document analysis system specializing in extracting design and user experience "
        "heuristic rules. Your task is to analyze the provided text content from a single PDF page. "
        "Identify and extract all distinct, clearly defined heuristic rules mentioned on this page. "
        "The extracted rules MUST strictly conform to the provided JSON schema. "
        "Ensure the 'source_page' field is always set to the provided page number."
    )
    
    # The user query provides the content and specifies the task context
    user_query = (
        f"Analyze the following text from page {page_num} and extract all heuristic rules. "
        "Each rule must have a rule_id, rule_name, a full description, and the source_page number. "
        f"Page Content:\n\n---\n{text}\n---"
    )

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": HEURISTIC_SCHEMA1
        }
    }

    headers = {'Content-Type': 'application/json'}

    for attempt in range(max_retries):
        try:
            # We use f-string for API URL to inject the key cleanly
            response = requests.post(f"{API_URL}?key={API_KEY}", headers=headers, data=json.dumps(payload))
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            result = response.json()
            
            # Extracting the JSON string from the response
            json_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            
            if json_text:
                return json_text
            else:
                print(f"Attempt {attempt + 1}: No text content in API response for page {page_num}.")
                
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed for page {page_num}. Error: {e}")

        # Exponential Backoff
        if attempt < max_retries - 1:
            delay = 2 ** attempt
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
        
    print(f"Failed to extract rules from page {page_num} after {max_retries} attempts.")
    return None

# --- MAIN EXECUTION ---

def extractPDF(pdf_file_path):
    """
    Main function to run the heuristic extraction process.
    """
    if not API_KEY:
        print("ERROR: Please set your Gemini API Key in the API_KEY variable.")
        return

    # 1. Extract text from the PDF
    all_page_data = extract_text_from_pdf(pdf_file_path)
    if not all_page_data:
        print("Could not extract any meaningful text from the PDF. Exiting.")
        return

    all_extracted_heuristics = []
    
    # 2. Process each page using the Gemini API
    print("\n--- Starting LLM Analysis for Heuristic Extraction ---")

    for page_data in all_page_data:
        page_num = page_data['page_num']
        print(f"-> Processing Page {page_num}...")
        
        json_result_str = call_gemini_for_extraction(page_data)
        
        if json_result_str:
            try:
                # The response is a JSON string of an array of heuristic objects
                heuristics_list = json.loads(json_result_str)
                if heuristics_list:
                    print(f"-> Found {len(heuristics_list)} heuristics on Page {page_num}.")
                    all_extracted_heuristics.extend(heuristics_list)
                else:
                    print(f"-> No heuristics identified on Page {page_num}.")
            except json.JSONDecodeError:
                print(f"-> ERROR: Failed to decode JSON response for Page {page_num}.")
        
        # Add a short delay to be respectful to the API rate limit
        time.sleep(0.5) 
    
    # 3. Final Output
    print("\n=======================================================")
    print(f"Extraction Complete. Total unique heuristics found: {len(all_extracted_heuristics)}")
    print("=======================================================\n")

    # Save the final results to a JSON file
    output_filename = "extracted_heuristics.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_extracted_heuristics, f, indent=4)

    print(f"All extracted data has been saved to: {output_filename}")
    print("Preview of first 3 extracted rules:")
    for rule in all_extracted_heuristics[:3]:
        print(f"  - [{rule.get('rule_id', 'N/A')}] {rule.get('rule_name', 'N/A')}")
        print(f"    (Source Page: {rule.get('source_page', 'N/A')})")
        
# --- RUN PROGRAM ---

# IMPORTANT: Replace 'path/to/your/document.pdf' with the actual path to your file.
if __name__ == "__main__":
    PDF_FILE = "./downloaded_pdfs/Gesture.pdf" 
    # Example: PDF_FILE = "C:/Users/User/Documents/NielsenHeuristics.pdf"
    
    extractPDF(PDF_FILE)