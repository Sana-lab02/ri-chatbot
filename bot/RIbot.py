import pandas as pd
from bot.Keywords import column_aliases, credential_terms, column_to_names
from bot.bot_matchers import find_best_row, find_best_column
from bot.bot_utils import clean_text, is_credential_question, clean_text_tfidf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
import inspect

#Confidence Threasholds
RETAILER_HIGH = 70
RETAILER_MEDIUM = 40
COLUMN_HIGH = 0.75
COLUMN_MEDIUM = 0.60
TROUBLE_THREASHOLD = 0.25

MAX_INFO_TURNS = 3
class RetailBot:
    def __init__(self, db_path="retailers.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        self.df_customer_info = pd.read_sql_query("SELECT * FROM retailers", self.conn)
        self.df_trouble = pd.read_sql_query("SELECT * FROM troubleshooting", self.conn)
        
        self.awaiting_info = None
        self.awaiting_info_turns = 0

        self.df_trouble['clean_question'] = self.df_trouble['question'].astype(str).apply(clean_text_tfidf)
        self.vectorizer_trouble = TfidfVectorizer(ngram_range=(1, 2))
        self.tfidf_trouble = self.vectorizer_trouble.fit_transform(self.df_trouble['clean_question'])
        self.column_names = list(column_aliases.keys())
        column_docs = [" ".join([col] + column_aliases.get(col, [])) for col in self.column_names]
        self.intent_vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        if column_docs:
            self.tfidf_columns = self.intent_vectorizer.fit_transform([clean_text(doc) for doc in column_docs])
        else:
            self.tfidf_columns = None


        self.awaiting_confirmation = None
        self.awaiting_confirmation_turns = 0
        self.last_user_input = None
        self.awaiting_retailer = False
        self.exit_commands = ["quit", "exit", "bye"]

    def process_input(self, user_input):
        """Handles yes/no confirmation in Flask"""
        user_input = str(user_input).strip()

        if user_input.lower() in self.exit_commands:
            return "Goodbye!"
        
        if self.awaiting_confirmation:
            self.awaiting_confirmation_turns += 1
            return self.handle_confirmation(user_input)
        
        
        if self.awaiting_retailer:
            return self.handle_retailer_input(user_input)
        

        if self.awaiting_info:
            self.awaiting_info_turns += 1
            return self.handle_info_request(user_input)
        
        return self.answer(user_input)


    def answer(self, user_input):
        self.last_user_input = user_input

        if not is_credential_question(user_input):
            return self.get_troubleshooting_answer(user_input)
        

        ranked = find_best_row(user_input, self.df_customer_info, threshold=40)
        row_index, retailer_name, r_score = ranked

        print("Debug... ", row_index, retailer_name, r_score)
        if retailer_name is None:
            if is_credential_question(user_input):
                return f"Sorry I couldn't find that retailer. Can you double-check the name?"
            return self.get_troubleshooting_answer(user_input)
        
        # Medium confidence -> ask user to confirm
        if r_score < RETAILER_MEDIUM:
            self.awaiting_confirmation = {
                "row_index": row_index,
                "retailer_name": retailer_name
            }
            return f"I think you mean {retailer_name}. Is that correct? (yes/no)"
        
        if retailer_name is None:
            return self.get_troubleshooting_answer(user_input)
        

        # High confidence -> auto-select retailer and look for column
        result = find_best_column(user_input, column_aliases)

        if not result:
            self.awaiting_info = {
                "row_index" : row_index,
                "retailer_name": retailer_name
            }
            self.awaiting_info_turns = 0
            return f"I foud {retailer_name}. What information do you need?"

        col_name, col_score = result

        if col_score < COLUMN_MEDIUM:
            return f"For {retailer_name}, did you want {col_name.lower()}?"
    
        return self.get_column_value(row_index, col_name, retailer_name)
    
    def get_column_value(self, row_index, col_name, retailer_name):
        # Auto-fetch value if high enough confidence
        actual_cols = {c.lower().strip(): c for c in self.df_customer_info.columns}
        real_col = actual_cols.get(col_name.lower().strip(), col_name)

        if not real_col:
            return f"Sorry, I could't find that information for {retailer_name}."
        

        value = self.df_customer_info.at[row_index, real_col]

        if pd.isna(value) or str(value).strip() == "":
            return f"No information stored for {retailer_name}."

        self.reset_state
        friend_col = column_to_names.get(
            real_col,
            real_col.replace("_", " ").title()
        )
        return f"{friend_col} for {retailer_name} is: {value}"


    def get_troubleshooting_answer(self, user_input):
        """Use TF-IDF to find the closest troubleshooting answer from df_trouble"""
        try:
            clean_input = clean_text(user_input)
            user_vec = self.vectorizer_trouble.transform([clean_input])
            similarities = cosine_similarity(user_vec, self.tfidf_trouble).flatten()
            best_index = similarities.argmax()
            score = similarities[best_index]

            if score < TROUBLE_THREASHOLD:
                return "Sorry, I couldn't find an answer. Can you rephrase your question?"

            return self.df_trouble['question'].iloc[best_index] + ": " + self.df_trouble['answer'].iloc[best_index]
        except Exception as e:
            print("Debug...", e)
            return "Sorry, something went wrong while searching for a troubleshooting answer."
    


    def handle_confirmation(self, user_input):
        user_input = clean_text(user_input)
        data = self.awaiting_confirmation

        if user_input in ["yes", "y"]:
            self.awaiting_confirmation = None
            
            self.awaiting_info = {
                "row_index": data["row_index"],
                "retailer_name": data["retailer_name"]
            }
            self.awaiting_info_turns = 0

            return f"Great. What information do you need for {data['retailer_name']}"
        
        elif user_input in ["no", "n"]:
            self.awaiting_confirmation = None
            self.awaiting_retailer = True
            return "Okay, please tell me the correct retailer name"
        else:
            return "Please answer yes or no."
        
    def answer_with_locked_retailer(self, user_input, row_index, retailer_name):
        result = find_best_column(user_input, column_aliases)

        if not result:
            return f"I found {retailer_name}, but what information do you need?"
        
        col_name, col_score = result

        if col_score < COLUMN_MEDIUM:
            return f"For {retailer_name}, did you want {col_name.lower()}?"
        
        return self.get_column_value(row_index, col_name, retailer_name)

    def handle_info_request(self, user_input):
        data = self.awaiting_info
        row_index = data["row_index"]
        retailer_name = data["retailer_name"]

        result = find_best_column(user_input, column_aliases)

        if not result :
            return "I still couldn't tell what info you need. Try saying password, username, or account number"
        
        col_name, col_score = result

        if col_score < COLUMN_MEDIUM:
            return f"For {retailer_name}, did you want {col_name}?"
        
        self.awaiting_info = None
        return self.get_column_value(row_index, col_name, retailer_name)

    def reset_state(self):
        self.awaiting_info = None
        self.awaiting_info_turns = 0
        self.awaiting_confirmation = None
        self.awaiting_confirmation_turns = 0

    def handle_retailer_input(self, user_input):
        self.awaiting_retailer = False

        ranked = find_best_row(user_input, self.df_customer_info, threshold=50)
        row_index, retailer_name, score = ranked

        if retailer_name is None:
            self.awaiting_confirmation = True
            return "Sorry, I still couldn't find that retailer. Please try again"
        
        self.awaiting_info = {
            "row_index": row_index,
            "retailer_name": retailer_name
        }
        self.awaiting_info_turns = 0

        return f"Got it {retailer_name}. What information do you need?"