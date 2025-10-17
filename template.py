import streamlit as st
import pandas as pd
import numpy as np
import time

from QueryarXiv import search_arxiv, print_papers
from typing import List, Dict, Any
from Extraction import extractPDF


# --- 1. CONFIGURATION ---
# Set up the page configuration just once
st.set_page_config(
    page_title="Custom Data App Template",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DATA CACHING (The "Hello" App uses this extensively) ---

# Use st.cache_data to load data only once, speeding up the app significantly
# This is crucial because Streamlit reruns the script on every interaction!
@st.cache_data
def load_mock_data():
    """Loads a mock dataset for demonstration."""
    # Simulate a slow data load process
    # time.sleep(2) 
    
    data = {
        'timestamp': pd.date_range(start='1/1/2024', periods=100, freq='D'),
        'value_a': np.random.randn(100).cumsum() + 10,
        'value_b': np.random.randn(100).cumsum() + 5,
        'category': np.random.choice(['A', 'B', 'C'], 100),
    }
    df = pd.DataFrame(data)
    return df

DATA_DF = load_mock_data()


# --- 3. PAGE FUNCTIONS (Modularizing the App) ---

def show_papers(papers_table: pd.DataFrame):
    st.subheader("Heuristic Papers Collected from arXiv:")
    st.dataframe(papers_table, use_container_width=True)    


# collect paper references from arXiv based on keywords
def collect_papers():
   
    search_keywords = ["large language model", "agent"]  # Example keywords
    
    # Define the number of results you want
    limit = 10

    collected_papers = search_arxiv(search_keywords, max_results=limit)
    paper_table = pd.DataFrame(collected_papers)

    print_papers( collected_papers )
    show_papers( paper_table )
    download_pdfs( collected_papers )

def download_pdfs(papers: List[Dict[str, Any]]):
    """Downloads PDFs of the given papers."""
    import requests
    from pathlib import Path

    pdf_dir = Path("downloaded_pdfs")
    pdf_dir.mkdir(exist_ok=True)

    for paper in papers:
        arxiv_id = paper.get("arxiv_id", "").split('/')[-1]
        pdf_url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"
        response = requests.get(pdf_url)
        if response.status_code == 200:
            with open(pdf_dir / f"{arxiv_id}.pdf", 'wb') as f:
                f.write(response.content)
            st.success(f"Downloaded: {arxiv_id}.pdf")
        else:
            st.error(f"Failed to download: {arxiv_id}.pdf")  


def page_dashboard():
    """Main Analytical Dashboard Page."""
    st.title("📊 建立启发式规则库")
    
    st.header("收集启发式规则")
    
    collect_papers()
    
    PDF_FILE = "./downloaded_pdfs/Gesture.pdf" 
    # Example: PDF_FILE = "C:/Users/User/Documents/NielsenHeuristics.pdf"
    extractPDF(PDF_FILE)

    st.markdown("""---""")
    
    # 3.1. Layout with Columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Analysis")
        # Use st.line_chart for quick visualization of two columns
        st.line_chart(DATA_DF[['value_a', 'value_b']])
        
    with col2:
        st.subheader("Data Summary")
        st.dataframe(DATA_DF.describe().T.style.format('{:.2f}'), use_container_width=True)

def page_data_exploration():
    """Interactive Data Exploration Page."""
    st.title("🔍 Data Exploration & Filtering")
    
    st.header("Select Parameters")
    
    # 3.2. Sidebar Interaction Replicated
    selected_category = st.selectbox(
        "Filter by Category",
        options=['All'] + list(DATA_DF['category'].unique())
    )
    
    # Apply filter
    if selected_category != 'All':
        filtered_df = DATA_DF[DATA_DF['category'] == selected_category]
    else:
        filtered_df = DATA_DF
        
    st.markdown(f"**Showing {len(filtered_df)} Records**")
    
    # 3.3. Interactive Table
    st.dataframe(filtered_df, use_container_width=True)


# --- 4. NAVIGATION AND MAIN EXECUTION ---

# Create the sidebar for navigation
st.sidebar.title("App Navigation")

# Use a radio button for page selection
page = st.sidebar.radio(
    "Go to",
    ("Dashboard", "Data Exploration")
)

# Main routing logic
if page == "Dashboard":
    page_dashboard()
elif page == "Data Exploration":
    page_data_exploration()



# --- 5. UXEE Task Input ---

# Add a text area for user input in the sidebar 
st.sidebar.markdown("""---""")
st.sidebar.header("User Input Section")
user_input = st.sidebar.text_area("Enter your notes or tasks here:", height=100)
if user_input:
    st.sidebar.success("Input received!")   
else:
    st.sidebar.info("Please enter some text above.")        




