import telebot
import os
from dotenv import load_dotenv
from telebot import types

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}


@bot.message_handler(commands=['start'])
def start(message):
    with open('words.txt', 'r') as file:
        words = [word for line in file for word in line.strip().split()]
    user_data[message.chat.id] = {'words': words}
    msg = bot.send_message(message.chat.id, 'Введи слово которое ты написал в worlde (5 букв)')
    bot.register_next_step_handler(msg, process_word)


def process_word(message):
    user_id = message.chat.id

    try:
        user_input = message.text.strip().lower()
    except AttributeError:
        msg = bot.send_message(user_id, "Неподходящее слово Пожалуйста, введите слово")
        bot.register_next_step_handler(msg, process_word)
        return

    if user_input.startswith('/'):
        return

    if not user_input.isalpha():
        msg = bot.send_message(user_id, "Неподходящее слово Пожалуйста, введите слово из 5 букв:")
        bot.register_next_step_handler(msg, process_word)
        return

    if len(user_input) != 5:
        msg = bot.send_message(user_id, f'Введено {len(user_input)} букв. Нужно 5. Попробуйте снова:')
        bot.register_next_step_handler(msg, process_word)
        return

    if not message.text:
        msg = bot.send_message(user_id, f'Введено не слово')
        bot.register_next_step_handler(msg, process_word)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    yes_btn = types.InlineKeyboardButton("Да, верно", callback_data="word_correct")
    no_btn = types.InlineKeyboardButton("Нет, перевыбрать", callback_data="word_incorrect")
    markup.add(yes_btn, no_btn)

    user_data[user_id]['word'] = user_input
    user_data[user_id]['current_index'] = 0
    user_data[user_id]['colors'] = []

    bot.send_message(user_id,
                     f'Введено слово {user_input}, верно?',
                     reply_markup=markup)


def send_letter_with_buttons(user_id):
    data = user_data.get(user_id)
    if not data:
        bot.send_message(user_id, "Ошибка состояния. Начните заново командой /start")
        return

    index = data['current_index']
    letter = data['word'][index]
    markup = types.InlineKeyboardMarkup(row_width=3)

    grey_btn = types.InlineKeyboardButton("Серый", callback_data=f"grey_{index}")
    yellow_btn = types.InlineKeyboardButton("Желтый", callback_data=f"yellow_{index}")
    green_btn = types.InlineKeyboardButton("Зеленый", callback_data=f"green_{index}")

    markup.add(grey_btn, yellow_btn, green_btn)

    bot.send_message(
        user_id,
        f"Буква {index + 1}: {letter}\nВыберите цвет:",
        reply_markup=markup
    )


def show_results(user_id, state):
    colors = state['colors']

    visualization = "Визуализация:\n"
    for color in colors:
        if color == 'grey':
            visualization += '⬜'
        elif color == 'yellow':
            visualization += '🟨'
        elif color == 'green':
            visualization += '🟩'
    bot.send_message(user_id, visualization)

    markup = types.InlineKeyboardMarkup(row_width=2)
    yes_btn = types.InlineKeyboardButton("Да, верно", callback_data="colors_correct")
    no_btn = types.InlineKeyboardButton("Нет, перевыбрать", callback_data="colors_incorrect")
    markup.add(yes_btn, no_btn)

    bot.send_message(
        user_id,
        "Верно ли выбраны цвета для букв?",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data in ['word_correct', 'word_incorrect'])
def handle_word_confirmation(call):
    user_id = call.message.chat.id

    bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=None
    )

    if call.data == 'word_correct':
        bot.answer_callback_query(call.id, "Отлично! Результаты подтверждены")
        send_letter_with_buttons(user_id)

    elif call.data == "word_incorrect":
        bot.answer_callback_query(call.id, "Начинаем заново!")
        msg = bot.send_message(user_id, "Введите слово заново... (5 букв)")
        bot.register_next_step_handler(msg, process_word)

    else:
        bot.answer_callback_query(call.id, "❌ Ошибка состояния. Начните заново командой /start")


@bot.callback_query_handler(func=lambda call: call.data.startswith(('grey_', 'yellow_', 'green_')))
def handle_button_click(call):
    user_id = call.message.chat.id
    data = user_data.get(user_id)

    if not data:
        bot.answer_callback_query(call.id, "Сессия устарела. Начните заново командой /start")
        return

    color, index_str = call.data.split('_')
    index = int(index_str)

    if index != data['current_index']:
        bot.answer_callback_query(call.id, "Вы уже обработали эту букву!")
        return

    data['colors'].append(color)
    data['current_index'] += 1

    color_emojis = {
        'grey': '⚪',
        'yellow': '🟡',
        'green': '🟢'
    }
    bot.answer_callback_query(call.id, f"Выбрано: {color_emojis.get(color, '❓')}")

    bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=None
    )

    if data['current_index'] < 5:
        send_letter_with_buttons(user_id)
    else:
        data['current_index'] = 0
        show_results(user_id, data)


@bot.callback_query_handler(func=lambda call: call.data in ['colors_correct', 'colors_incorrect'])
def handle_color_confirmation(call):
    user_id = call.message.chat.id
    data = user_data.get(user_id)
    bot.edit_message_reply_markup(
        chat_id=user_id,
        message_id=call.message.message_id,
        reply_markup=None
    )
    if call.data == "colors_correct":
        bot.answer_callback_query(call.id, "Отлично! Результаты подтверждены")

        words = data['words']
        if data['colors'].count('green') != 5 and data['word'] in words:
            words.remove(data['word'])

        for i, (color, letter) in enumerate(zip(data['colors'], data['word'])):
            if color == 'grey':
                words = [word_iter for word_iter in words if letter not in word_iter]
            elif color == 'green':
                words = [word_iter for word_iter in words if word_iter[i] == letter]
            elif color == 'yellow':
                words = [word_iter for word_iter in words if letter in word_iter]
        data['words'] = words
        if len(data['words']) == 0:
            bot.send_message(user_id, "Такого слова не найдено, попробуйте ещё раз /start")
            return
        elif len(data['words']) < 50:
            bot.send_message(user_id, f"Возможные слова {str(words)[1:-1]}")
        msg = bot.send_message(user_id, f"Введи следующее слово")
        bot.register_next_step_handler(msg, process_word)

    elif call.data == "colors_incorrect":
        data['colors'] = []
        bot.answer_callback_query(call.id, "Начинаем заново!")
        bot.send_message(user_id, "Давайте выберем цвета заново...")
        send_letter_with_buttons(user_id)

    else:
        bot.answer_callback_query(call.id, "Ошибка состояния. Начните заново командой /start")


bot.polling(non_stop=True)
