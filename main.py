import telebot
import schedule
import time
import threading
import sqlite3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

# Create a connection to the SQLite database
conn = sqlite3.connect('goals.db', check_same_thread=False)
cursor = conn.cursor()

# Create a table to store users if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
bot = telebot.TeleBot('6824276007:AAFyHqxGV2lGLLJGNLMRyExoiUxMSTlvaw0')
started_users = set()
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
    if message.chat.id not in started_users:
        bot.send_message(message.chat.id, f'Hello {message.from_user.first_name}, how can I help you?')

        # Check if the user is in the database. If not, add them
        query_user_name = message.from_user.first_name
        cursor.execute('SELECT * FROM users WHERE first_name = ?', (query_user_name,))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO users (first_name) VALUES (?)', (query_user_name,))
            conn.commit()




# Command handler for /help
@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = """
    List of available commands:
    /start - start conversation with the bot
    /help - get a list of available commands
    /setdailygoals - to set <goal> and <time>
    /totalgoals - to see how many goals are completed and not completed
    /completegoal - to complete not completed <goal>
    /resetgoals - to delete all goals
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

# Command handler for /totalgoals
@bot.message_handler(commands=['totalgoals'])
def total_goals(message):
    try:
        # Get the user ID
        user_id = message.chat.id

        # Retrieve completed and not completed goals for the user
        cursor.execute('SELECT goal, completed FROM goals WHERE user_id = ?', (user_id,))
        goals = cursor.fetchall()

        total_goals_count = len(goals)

        if goals:
            goals_message = f"You have set {total_goals_count} goal(s):\n"
            for goal, completed in goals:
                status = "✅" if completed == 1 else "❌"
                goals_message += f"- {goal} {status}\n"
            bot.send_message(message.chat.id, goals_message)
        else:
            bot.send_message(message.chat.id, "You haven't set any goals yet.")

    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

#Command handler for /resetgoals
@bot.message_handler(commands=['resetgoals'])
def reset_goals(message):
    try:
        # Get the user ID
        user_id = message.chat.id

        # Delete all goals for the user
        cursor.execute('DELETE FROM goals WHERE user_id = ?', (user_id,))
        conn.commit()

        bot.send_message(message.chat.id, "All goals have been reset.")

    except Exception as e:
        bot.reply_to(message, f"Error: {e}")


# Command handler for /completegoal
@bot.message_handler(commands=['completegoal'])
def complete_goal(message):
    try:
        args = message.text.split()[1:]
        if len(args) < 1:
            raise ValueError("Usage: /completegoal <goal>")

        goal_title = ' '.join(args)

        # Get the user ID
        user_id = message.chat.id

        # Update the completion status of the goal
        cursor.execute('UPDATE goals SET completed = 1 WHERE user_id = ? AND goal = ?', (user_id, goal_title))
        conn.commit()

        bot.reply_to(message, f"You marked goal '{goal_title}' as completed ✅.")

    except Exception as e:
        bot.reply_to(message, f"Error: {e}")


# Command handler for /visual
@bot.message_handler(commands=['visual'])
def visualize_goals(message):
    try:
        # Get the user ID
        user_id = message.chat.id

        # Retrieve completed and not completed goals for the user
        cursor.execute('SELECT completed FROM goals WHERE user_id = ?', (user_id,))
        goals = cursor.fetchall()

        if not goals:
            bot.send_message(message.chat.id, "You haven't set any goals yet.")
            return

        completed_count = sum(1 for goal in goals if goal[0] == 1)
        not_completed_count = sum(1 for goal in goals if goal[0] == 0)

        # Plot the graph
        labels = ['Completed', 'Not Completed']
        counts = [completed_count, not_completed_count]
        colors = ['green', 'red']

        plt.bar(labels, counts, color=colors)
        plt.xlabel('Goal Status')
        plt.ylabel('Count')
        plt.title('Completed vs. Not Completed Goals')

        # Save the plot as an image
        plot_filename = f'{user_id}_goals_plot.png'
        plt.savefig(plot_filename)

        # Send the plot image
        with open(plot_filename, 'rb') as plot_image:
            bot.send_photo(message.chat.id, plot_image)

        # Remove the plot image file
        os.remove(plot_filename)

    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

# Command handler for /resetusers
@bot.message_handler(commands=['resetusers'])
def reset_users(message):
    try:
        # Delete all users from the database
        cursor.execute('DELETE FROM users')
        conn.commit()

        bot.send_message(message.chat.id, "All users have been deleted.")

    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(commands=['debug'])
def handle_debug(message):
    connection = sqlite3.connect("goals.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users")
    print("Users:")
    print(cursor.fetchall())
    cursor.execute("SELECT * FROM goals")
    print("Goals")
    print(cursor.fetchall())

# Start the scheduler in a separate thread

def main():
    print("Main function called")
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    # Start polling the bot
    while True:
        try:
            bot.polling(none_stop=True)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)  # Wait for 15 seconds before retrying polling

if __name__ == '__main__':
    main()
