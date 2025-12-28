import re
from rapidfuzz import fuzz
import nltk
import numpy as np
import pandas as pd
from nltk.stem import WordNetLemmatizer
import sys
from bot.Keywords import credential_terms

nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

# ======= Lematizer function ========#
lemmatizer = WordNetLemmatizer()



def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    
    text = re.sub(r"[^\w\s'&\-\.]", "", text)

    return text

def clean_text_tfidf(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    
    text = re.sub(r"[^\w\s'&\-\.]", "", text)
    
    return text

# Helper for safe prints
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        pass

def load_excel_files(trouble_path, customer_path):
    # Loading excelsheet
    try:
        df_trouble = pd.read_excel(trouble_path)
        df_customer_info = pd.read_excel(customer_path)
        return df_trouble, df_customer_info
    except FileNotFoundError as e:
        safe_print("Error: One or more Excel files could not be found.")
        safe_print(e)
        sys.exit(1)

def is_credential_question(user_input):
    text = user_input.lower()
    for term in credential_terms:
        if fuzz.partial_ratio(term, text) > 80:
            return True
    return False