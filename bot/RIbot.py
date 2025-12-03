import pandas as pd
from Keywords import column_aliases
from bot_matchers import find_best_row, find_best_column
from bot_utils import clean_text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

#Confidence Threasholds
RETAILER_HIGH = 70
RETAILER_MEDIUM = 60
COLUMN_HIGH = 0.75
COLUMN_MEDIUM = 0.60
TROUBLE_THREASHOLD = 10

class RetailBot:
    def __init__(self, customer_excel='/Users/phood/Documents/Sheet.xlsx', trouble='/Users/phood/Documents/Troubleshootingchat.xlsx'):
        self.df_customer_info = pd.read_excel(customer_excel)
        self.exit_commands = ["quit", "exit", "bye"]

        self.df_trouble = pd.read_excel(trouble)
        self.df_trouble['clean_question'] = self.df_trouble['Question'].astype(str).apply(lambda x: x.lower().strip())
        
        self.vectorizer_trouble = TfidfVectorizer(ngram_range=(1, 2))
        self.tfidf_trouble = self.vectorizer_trouble.fit_transform(self.df_trouble['clean_question'])

        self.awaiting_confirmation = None
        self.last_user_input = None


    def answer(self, user_input):
        self.last_user_input = user_input
        row_index, retailer_name, r_score = find_best_row(user_input, self.df_customer_info)

        # No retailer or very low confidence -> troubleshooting fallback
        if retailer_name is None or r_score < RETAILER_MEDIUM:
            return self.fallback_troubleshooting(user_input)

        # Medium confidence -> ask user to confirm
        if RETAILER_MEDIUM <= r_score < RETAILER_HIGH:
            self.awaiting_confirmation = {
                "row_index": row_index,
                "retailer_name": retailer_name
            }
            return f"I think you mean '{retailer_name}'. Is that correct? (yes/no)"

        # High confidence -> auto-select retailer and look for column
        col_name, col_score = find_best_column(user_input, column_aliases)

        if not col_name or col_score < COLUMN_MEDIUM:
            return f"I found '{retailer_name}', but what info do you need? (e.g., username, password)"

        # Auto-fetch value if high enough confidence
        actual_cols = {c.lower().strip(): c for c in self.df_customer_info.columns}
        real_col = actual_cols.get(col_name.lower().strip(), col_name)
        value = self.df_customer_info.at[row_index, real_col] if real_col in self.df_customer_info.columns else None

        if pd.isna(value) or str(value).strip() == "":
            return f"No information stored for '{retailer_name}'."

        return f"{real_col} for '{retailer_name}' is: {value}"


    def fallback_troubleshooting(self, user_input):
        """Use TF-IDF to find the closest troubleshooting answer from df_trouble"""
        try:
            clean_input = clean_text(user_input)
            user_vec = self.vectorizer_trouble.transform([clean_input])
            similarities = cosine_similarity(user_vec, self.tfidf_trouble).flatten()
            best_index = similarities.argmax()
            score = similarities[best_index]

            if score < TROUBLE_THREASHOLD:
                return "Sorry, I couldn't find an answer. Can you rephrase your question?"

            return self.df_trouble['Question'].iloc[best_index] + ": " + self.df_trouble['Answer'].iloc[best_index]
        except Exception:
            return "Sorry, something went wrong while searching for a troubleshooting answer."


    def lookup_retailer_info(self, row_index, retailer_name):
        col_name, col_score = find_best_column(self.last_user_input, column_aliases)
        
        if not col_name or col_score < COLUMN_MEDIUM:
            return f"I found '{retailer_name}', but what info do you need?"
        
        actual_cols = {c.lower().strip(): c for c in self.df_customer_info.columns}
        real_col = actual_cols.get(col_name.lower().strip(), col_name)

        if real_col not in self.df_customer_info.columns:
            return f"Sorry, I couldn't find that information for '{retailer_name}'."

        value = self.df_customer_info.at[row_index, real_col]
           
        if pd.isna(value) or str(value).strip() == "":
            return f"Sorry, there was no information entered for '{retailer_name}'."
            
        return f"{real_col} for '{retailer_name}' is: {value}"

    def process_input(self, user_input):
        """Handles yes/no confirmation in Flask"""
        if self.awaiting_confirmation:
            return self.handle_confirmation(user_input)
        else:
            self.last_user_input = user_input
            return self.answer(user_input)