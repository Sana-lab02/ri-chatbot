from RIbot import RetailBot
import pandas as pd

awaiting_confirmation = None

bot = RetailBot()

print("Hi, how may I assist you?")

while True:
    user_input = input("You: ")
    
    if user_input.lower() in bot.exit_commands:
        print("Bot: Goodbye!")
        break

    #Check for confirmation
    if bot.awaiting_confirmation:
        if user_input.lower() == ("yes"):
            data = bot.awaiting_confirmation
            bot.awaiting_confirmation = None

            response = bot.lookup_retailer_info(
                data["row_index"],
                data["retailer_name"]
            )
            print("Bot:", response)
            continue

        elif user_input.lower() == ("no"):
            print("Bot: Okay, please rephrase your question.")
            bot.awaiting_confirmation = None
            continue
        else:
            print("Bot: Please answer 'yes' or 'no'.")
            continue
    response = bot.answer(user_input)
    
    if response.startswith("I think you mean"):
        suggested_retailer = response.split("'")[1]
        awaiting_confirmation = (None, suggested_retailer)
        print("Bot:", response)
        continue

    print("Bot:", response)
