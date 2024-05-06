import telebot
import schedule
import time
import threading
import sqlite3

# Create a connection to the SQLite database
conn = sqlite3.connect('goals.db', check_same_thread=False)
cursor = conn.cursor()

# Create a table to store users if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT
    )
''')

# Create a table to store goals if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        goal_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        goal TEXT,
        completed INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
''')
conn.commit()

# Initialize the bot
bot = telebot.TeleBot('6824276007:AAFXqFkU8Re5n7fWxPzh4bWH9v5sjOH-xZw')

# Function to send notification
def send_notification(chat_id, goal):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ Completed", callback_data=f"completed_{goal}"),
        telebot.types.InlineKeyboardButton("❌ Not completed", callback_data=f"not_completed_{goal}")
    )
    bot.send_message(chat_id, f"Don't forget your daily goal: {goal}", reply_markup=markup)


# Function to schedule notification
def schedule_notification(chat_id, goal, time):
    schedule.every().day.at(time).do(send_notification, chat_id, goal)


# Function to run the scheduler
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


# Command handler for /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, f'Hello {message.from_user.first_name}, how can I help you?')
    # Check if the user is in the database. If not, add them
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (message.chat.id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (user_id, first_name) VALUES (?, ?)',
                       (message.chat.id, message.from_user.first_name))
        conn.commit()


# Command handler for /help
@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = """
    List of available commands:
    /start - start conversation with the bot
    /help - get a list of available commands
    """
    bot.send_message(message.chat.id, help_text)


# Command handler for /setdailygoals
@bot.message_handler(commands=['setdailygoals'])
def set_daily_goals(message):
    try:
        args = message.text.split()[1:]
        if len(args) < 2:
            raise ValueError("Usage: /setdailygoals <goal> <time>")

        goal = ' '.join(args[:-1])
        time_str = args[-1]

        # Get the user ID
        user_id = message.chat.id

        # Save the goal in the database with completion status 0 (not completed)
        cursor.execute('INSERT INTO goals (user_id, goal, completed) VALUES (?, ?, 0)', (user_id, goal))
        conn.commit()

        schedule_notification(message.chat.id, goal, time_str)

        bot.reply_to(message, f"Daily goal set: {goal} at {time_str}")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")


# Callback handler for keyboard buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data.startswith("completed_"):
        goal = call.data.split("_", 1)[1]
        # Mark the goal as completed in the database
        cursor.execute('UPDATE goals SET completed = 1 WHERE user_id = ? AND goal = ?', (call.message.chat.id, goal))
        conn.commit()
        bot.answer_callback_query(call.id, f"You marked goal '{goal}' as completed")
    elif call.data.startswith("not_completed_"):
        goal = call.data.split("_", 1)[1]
        # Mark the goal as not completed in the database
        cursor.execute('UPDATE goals SET completed = 0 WHERE user_id = ? AND goal = ?', (call.message.chat.id, goal))
        conn.commit()
        bot.answer_callback_query(call.id, f"You marked goal '{goal}' as not completed")


# Start the scheduler in a separate thread
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.start()

# Start polling the bot
while True:
    try:
        bot.polling(none_stop=True)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)  # Wait for 15 seconds before retrying polling
def main():
    print("Main function called")


if __name__ == '__main__':
    main()