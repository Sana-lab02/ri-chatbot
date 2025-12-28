from Keywords import exit_commands, column_aliases
from bot_utils import clean_text, safe_print, load_excel_files
from bot_matchers import find_best_troubleshooting_answer, find_best_column, find_best_row, chat_bot_stop_commands, mask_value_for_debug
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd
import traceback



#--------------config----------------------
debug = False

# confidence thresholds
RETAILER_HIGH = 85    # percent (rapidfuzz) to accept retialer immediatly
RETAILER_MEDIUM = 70  # medium confidence -> ask user to confirm retaier
COLUMN_HIGH = 0.75     # combined score to accept column immediately 
COLUMN_MEDIUM = 0.60   # medim -> ask user 
TROUBLE_THRESHOLD = 0.10  #cosine similarity threshold for troubleshoting anwers

# ======Load Excel Sheets==========#
df_trouble, df_customer_info = load_excel_files(
    '/Users/phood/Documents/Troubleshootingchat.xlsx', 
    '/Users/phood/Documents/Sheet.xlsx'
)


# --- Build TF-IDF models ---
df_trouble['clean_question'] = df_trouble['Question'].astype(str).apply(clean_text)
vectorizer_trouble = TfidfVectorizer(ngram_range=(1, 2))
tfidf_trouble = vectorizer_trouble.fit_transform(df_trouble['clean_question'])


def answer_user_question(user_input):
    # Logic:
    #1) try to identify retailer (fuzzy)
    # - if no retailer -> go to troubleshooting fallback
    # 2) If retailer found -> try to identify column
    #  - if column high confidenc -> return value
    # - if column medium confidence -> ask confirm retailer
    # _ if no column -> troubleshooting fallback

    # 1) retialer detection
    row_index, retailer_name, retailer_score = find_best_row(user_input, df_customer_info)

    if row_index is None:
        if debug:
            print(f"Debug.. Retailer match too weak ({retailer_score:.1f}) - fallback to troubleshooting")
        ts_answer = find_best_troubleshooting_answer(user_input, df_trouble, vectorizer_trouble, tfidf_trouble)
        if ts_answer:
            return ts_answer
        return "Bot: I couldnt confidently determine the customerf. Can you please rephrase with the store name?"
        
    if retailer_score < RETAILER_MEDIUM:
        if debug:
            print(f"Debug.. Retailer match to weak ({retailer_score:.1f})")
        ts_answer = find_best_troubleshooting_answer(user_input, df_trouble, vectorizer_trouble, tfidf_trouble)
        if ts_answer:
            return ts_answer
        return("Bot: I couldn't confidently determine the customer. Can you repharse with the stor name?")
    
    col_name, col_score = find_best_column(user_input, column_aliases)

    if not col_name:
        if debug:
            print("Debug.. No column math found -> troubleshoting fallback")
        ts_answer = find_best_troubleshooting_answer(user_input, df_trouble, vectorizer_trouble, tfidf_trouble)
        if ts_answer:
            return ts_answer
        return f"Bot: I found the retailer '{retailer_name}', but couldn't figure out what info you want. Try 'username' or 'password'."


    if col_score >= COLUMN_HIGH and retailer_score >= RETAILER_HIGH:
        actual_cols = {c.lower().strip(): c for c in df_customer_info.columns}
        real_col = actual_cols.get(col_name.lower().strip(), col_name)
        value = df_customer_info.at[row_index, real_col] if real_col in df_customer_info.columns else None

        if pd.isna(value) or str(value).strip() == "":
            return f"Bot: Sorr, there is no infomation entered for '{retailer_name}'."
        
        if "password" in real_col.lower():
            return f"Bot: '{real_col}' for '{retailer_name}' is '{value}'"
        return f"Bot: '{real_col}' for '{retailer_name}' is '{value}"
    

    if col_score >= COLUMN_MEDIUM or retailer_score >= RETAILER_MEDIUM:
        suggestion = f"Did you mean the '{col_name}' for '{retailer_name}'? (yes/no)"
        return suggestion
    
    ts_answer = find_best_troubleshooting_answer(user_input, df_trouble, vectorizer_trouble, tfidf_trouble)
    if ts_answer:
        return ts_answer
    return "Bot: I coudn't find an asnwer. Try rephrasing "


def chat_bot_loop():
     # Chatbot start
    print("Hi, how may I assist you?")
    awaiting_confirmation = None

    while True:

        try:
            user_input = input("You: ").strip()
            if user_input == "":
                continue

        # Step 0: Check stop commands
            if str(user_input).strip().lower() in exit_commands:
                print(("Bot: Goodbye!"))
                break

            if awaiting_confirmation:
                t, meta = awaiting_confirmation
                lc = user_input.strip().lower()
                if lc in ("yes", "y"):
                    if t == 'confirm_col':

                        row_index = meta['row_index']
                        col_name = meta['col_name']
                        actual_cols = {c.lower().strip(): c for c in df_customer_info.columns}
                        real_cols = actual_cols.get(col_name.lower().strip(), col_name)
                        value = df_customer_info.at[row_index, real_cols] if real_cols in df_customer_info.columns else None
                        if pd.isna(value) or str(value).strip() == "":
                            print(f"Bot: Sorry, there is no information entered for '{meta['retailer_name']}'.")
                        else:
                            print(f"Bot: '{real_cols}' for '{meta['retailer_name']}' is '{value}'")
                        awaiting_confirmation = None
                        continue
                    elif t == 'confirm_retailer':
                        print(f"Bot: Ok - what info would you like for '{meta['retailer_name']}'? (e.g. username, password)")
                    awaiting_confirmation = ('awaiting_column_for_retailer', meta)
                    continue
                elif lc in ("no", "n"):
                    print(f"Bot: Okay - please repharase your question or include the retalier name clearly.")
                    awaiting_confirmation = None
                    continue
                else:
                    print(f"Bot: Please answer 'yes' or 'no'.")
                    continue


            if awaiting_confirmation and awaiting_confirmation[0] == 'awaiting_column_for_retailer':
                meta = awaiting_confirmation[1]

                col_guess, col_score = find_best_column(user_input, column_aliases)
                if col_guess and col_score >= COLUMN_MEDIUM:
                    actual_cols = {c.lower().strip(): c for c in df_customer_info.columns}
                    real_cols = actual_cols.get(col_guess.lower().strip(), col_guess)
                    row_index = meta['row_index']
                    value = df_customer_info.at[row_index, real_cols] if real_cols in df_customer_info.columns else None
                    if pd.isna(value) or str(value).strip() == "":
                        print(f"Bot: Sorry, there is no information entered for '{meta['retailer_name']};.")
                    else:
                        print(f"Bot: '{real_cols}' for '{meta['retailer_name']}' is '{value}'")
                    awaiting_confirmation = None
                    continue
                else:
                    print("Bot: I could't identify which filed you want. try 'username' or 'passowrd'.")
                    continue

            result = answer_user_question(user_input)

            if isinstance(result, str) and result.strip().lower().startswith("did you mean"):
                try:
                    part = result.split("Did you mean the ", 1)[1]
                    col_part, rest = part.split("' for '", 1)
                    retailer_part = rest.rsplit("'?'", 1)[0]

                    row_index = df_customer_info.index[df_customer_info["Retailer"].str.strip().str.lower() == retailer_part.lower()][0]
                    awaiting_confirmation = ('confirm_col', {
                        'row_index': int(row_index),
                        'col_name': col_part,
                        'retailer_name': retailer_part
                        })
                    print("Bot:", result)
                    continue
                except Exception:
                    print("Bot:", result)
                    awaiting_confirmation = None
                    continue

            print(result)

        except KeyboardInterrupt:
            print("\nBot: Goodbye!")
            break
        except Exception as e:
            print("Unexpected error:", e)
            traceback.print_exc()
            continue



if __name__ == "__main__":
    chat_bot_loop()



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