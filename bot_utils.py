import re
import nltk
import numpy as np
import pandas as pd
from nltk.stem import WordNetLemmatizer
import sys

nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

# ======= Lematizer function ========#
lemmatizer = WordNetLemmatizer()



def clean_text(text, lemmatize=True):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s\.]', "", text)
    text = re.sub(r'\s+', " ", text).strip()
    if lemmatize:
        tokens = [lemmatizer.lemmatize(t) for t in text.split()]
        return " ".join(tokens)
    return text

def mask_value_for_debug(user_input):
    s = st(value)
    if len(s) <= 4:
        return "*" * len(s)
    return s[:2] + "*" (len(s) - 4) + s[-2:]

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