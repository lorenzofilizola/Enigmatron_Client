import json
import datetime
import random
from enum import Enum

import pytz
import strings
from google_images_search import GoogleImagesSearch
from telegram.ext import Updater, CallbackContext, PollHandler, PollAnswerHandler
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram import ParseMode
import constants
import requests

OPENING_DAYS = ["Venerdì", "Sabato"]


class WeekDay(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


############################### Bot ############################################
def start(bot, update):
    bot.message.reply_text(main_menu_message(),
                           reply_markup=main_menu_keyboard())


def main_menu(bot, update):
    bot.callback_query.message.edit_text(main_menu_message(),
                                         reply_markup=first_menu_keyboard)


def first_menu(bot, update):
    bot.callback_query.message.edit_text(first_menu_message(),
                                         reply_markup=first_menu_keyboard())


def second_menu(bot, update):
    bot.callback_query.message.edit_text(second_menu_message(),
                                         reply_markup=second_menu_keyboard())


def first_submenu(bot, update):
    pass


def show_cleaning_calendar(bot, update):
    r = requests.get('http://localhost:8080/cleaningCalendar')
    turns = json.loads(r.text)
    message = "*Calendario pulizie:*\n"
    for t in turns:
        timestamp = t['date'] / 1000
        date = datetime.datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y')
        message += f"*{date}:* "
        for v in t['cleaningGroup']['volunteers']:
            message += f"[{v['firstName']}](tg://user?id={v['id']}) "
        message += '\n'
    bot.callback_query.message.edit_text(message,
                                         parse_mode=ParseMode.MARKDOWN)


def show_group_menu(bot, update):
    r = requests.get('http://localhost:8080/groups')
    groups = json.loads(r.text)
    print(groups)
    keyboard = []
    message = ""
    for g in groups:
        print(g)
        message += f"*Group #{str(g['id'])}:* "
        print(message)
        for v in g['volunteers']:
            message += f"[{v['firstName']}](tg://user?id={v['id']}) "
        message += '\n'
    print(message)
    bot.callback_query.message.edit_text(message,
                                         reply_markup=InlineKeyboardMarkup(keyboard),
                                         parse_mode=ParseMode.MARKDOWN)


def register_to_cleaning_group(update: Update, context: CallbackContext):
    user = update.message.from_user
    print(context.args)
    print(user)


def error(update, context):
    print(f'Update {update} caused error {context.error}')


############################ Keyboards #########################################


def main_menu_keyboard():
    keyboard = [[InlineKeyboardButton('Turni di apertura', callback_data='opening_calendar')],
                [InlineKeyboardButton('Calendario pulizie', callback_data='cleaning_calendar')],
                [InlineKeyboardButton('Volontari', callback_data='m3')]]
    return InlineKeyboardMarkup(keyboard)


def first_menu_keyboard():
    keyboard = [[InlineKeyboardButton('Submenu 1-1', callback_data='m1_1')],
                [InlineKeyboardButton('Submenu 1-2', callback_data='m1_2')],
                [InlineKeyboardButton('Main menu', callback_data='main')]]
    return InlineKeyboardMarkup(keyboard)


def second_menu_keyboard():
    keyboard = [[InlineKeyboardButton('Calendario', callback_data='cleaning_calendar')],
                # [InlineKeyboardButton('Registra un nuovo gruppo', callback_data='group_menu')],
                [InlineKeyboardButton('Main menu', callback_data='main')]]
    return InlineKeyboardMarkup(keyboard)


############################# Messages #########################################
def main_menu_message():
    return 'Choose the option in main menu:'


def first_menu_message():
    return 'Choose the submenu in first menu:'


def second_menu_message():
    return 'Choose the submenu in second menu:'


def check_for_turns(context):
    r = requests.post('http://localhost:8080/updateCleaningTurns')
    cleaning_turn = json.loads(requests.get('http://localhost:8080/cleaningTurnsToday').text)
    print(cleaning_turn)
    if cleaning_turn:
        search_params = {
            'q': 'mr clean',
            'num': 30,
            'fileType': 'jpg|gif|png',
            'rights': 'cc_publicdomain|cc_attribute|cc_sharealike|cc_noncommercial|cc_nonderived'
        }
        gis.search(search_params)
        results = gis.results()
        image = random.choice(results)
        print(image.url)
        message = ""
        for v in cleaning_turn['cleaningGroup']['volunteers']:
            message += f"[{v['firstName']}](tg://user?id={v['id']}) "
        message += "tocca a voi pulire!"
        context.bot.send_message(chat_id=constants.CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)
        context.bot.send_photo(chat_id=constants.CHAT_ID, photo=image.url)


def today(bot, context):
    check_for_turns(context)


def send_poll(context):
    today = datetime.date.today()
    friday = today + datetime.timedelta((4 - today.weekday()) % 7)
    saturday = friday + datetime.timedelta(1)
    poll = context.bot.sendPoll(constants.CHAT_ID, is_anonymous=False,
                         allows_multiple_answers=True, close_date=friday.timetuple(),
                         question="Quando sei disponibile per i turni di apertura?",
                         options=[f"Venerdì {friday.strftime('%d/%m')}", f"Sabato {saturday.strftime('%d/%m')}",
                                  "Non posso partecipare"])
    context.bot.pinChatMessage(constants.CHAT_ID, poll.message_id)
    f = open("poll.txt", "w+")
    f.write(poll.message_id)
    f.close()


def send_poll_test(bot, context):
    send_poll(context);


def turns_poll_handler(update, context):
    user_id = update.poll_answer.user.id

    r = requests.post(f'http://localhost:8080/resetAvailability?userId={user_id}')

    answers = update.poll_answer.option_ids

    if answers:
        if 2 in answers:
            for i in range(2):
                requests.post(f'http://localhost:8080/availability?userId={user_id}&day={i}&available={False}')
            return

        for i in range(2):
            requests.post(f'http://localhost:8080/availability?userId={user_id}&day={i}&available={i in answers}')


def compute_opening_turns(context):
    r = requests.post(f'http://localhost:8080/opening_turns')


def check_opening_turns(context):
    turn = json.loads(requests.get('http://localhost:8080/openingTurnsToday').text)
    message = ""
    for v in turn['volunteers']:
        message += f"[{v['firstName']}](tg://user?id={v['id']}) "
    message += "stasera avete il turno!"
    context.bot.send_message(chat_id=constants.CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)


def send_trash_memo(context):
    today_date = datetime.date.today()
    message = ""
    weekday = today_date.weekday()

    if weekday == WeekDay.FRIDAY:
        message += strings.FRIDAY_TRASH_MEMO

    elif weekday == WeekDay.TUESDAY:
        if today_date.isocalendar().week % 2 == 0:
            message += strings.EVEN_TUESDAY_TRASH_MEMO
        else:
            message += strings.ODD_TUESDAY_TRASH_MEMO
    context.bot.send_message(chat_id=constants.CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)


def urge_voting(context):
    r = requests.get("http://localhost:8080/availability")
    openings = json.loads(r.text)
    message = "Non abbiamo ancora abbastanza volontari per le aperture di questa settimana.\n"
    enough_volunteers = True
    for index, opening in enumerate(openings):
        message += f"{OPENING_DAYS[index]}: "
        count = 0
        for a in opening['availabilities']:
            if a['available']:
                count += 1
        message += f"{count} volontari{'o' if count == 1 else ''}\n"
        if count < 3:
            enough_volunteers = False

    if enough_volunteers:
        return
    else:
        r = requests.get("http://localhost:8080/abstained")
        abstained = json.loads(r.text)
        for v in abstained:
            message += f"[{v['firstName']}](tg://user?id={v['id']}) "
        message += "per favore votate il prima possibile!"
        f = open("poll.txt", "r")
        poll_id = f.read()
        f.close()
        context.bot.send_message(chat_id=constants.CHAT_ID, text=message,
                                 reply_to_message_id=poll_id, parse_mode=ParseMode.MARKDOWN)


def show_opening_calendar(bot, update):
    r = requests.get('http://localhost:8080/openingCalendar')
    turns = json.loads(r.text)
    if turns:
        message = "*Calendario aperture:*\n"
        for t in turns:
            timestamp = t['opening']['date'] / 1000
            date = datetime.datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y')
            message += f"*{date}:* "
            for v in t['volunteers']:
                message += f"[{v['firstName']}](tg://user?id={v['id']}) "
            message += '\n'

    else:
        message = "I turni di questa settimana non sono ancora stati stabiliti. Vi avviserò giovedì alle 15 sui turni " \
                  "definitivi."
    bot.callback_query.message.edit_text(message,
                                         parse_mode=ParseMode.MARKDOWN)


############################# Handlers #########################################

updater = Updater(constants.TOKEN, use_context=True)
updater.dispatcher.add_handler(CommandHandler('menu', start))
updater.dispatcher.add_handler(CommandHandler('check_for_turns', check_for_turns))
updater.dispatcher.add_handler(CommandHandler('check_opening_turns', check_opening_turns))
updater.dispatcher.add_handler(CommandHandler('today', today))
updater.dispatcher.add_handler(CommandHandler('send_poll', send_poll_test))
updater.dispatcher.add_handler(CallbackQueryHandler(main_menu, pattern='main'))
updater.dispatcher.add_handler(CallbackQueryHandler(first_menu, pattern='m1'))
updater.dispatcher.add_handler(CallbackQueryHandler(second_menu, pattern='m2'))
updater.dispatcher.add_handler(CallbackQueryHandler(first_submenu, pattern='m1_1'))
updater.dispatcher.add_handler(CallbackQueryHandler(show_cleaning_calendar, pattern='cleaning_calendar'))
updater.dispatcher.add_handler(CallbackQueryHandler(show_opening_calendar, pattern='opening_calendar'))
updater.dispatcher.add_handler(CallbackQueryHandler(show_group_menu, pattern='group_menu'))
updater.dispatcher.add_error_handler(error)
updater.dispatcher.add_handler(PollAnswerHandler(turns_poll_handler, pass_chat_data=True, pass_user_data=True))

# Scheduled Tasks


j = updater.job_queue

# Message to volunteers in cleaning turn
target_time = datetime.time(hour=10, minute=00, second=00, tzinfo=pytz.timezone('Europe/Rome'))
j.run_daily(check_for_turns, context=updater,
            time=target_time)

# Message to volunteers in turn
target_time = datetime.time(hour=17, minute=00, second=00, tzinfo=pytz.timezone('Europe/Rome'))
j.run_daily(check_opening_turns, context=updater,
            time=target_time)

# Computation of turns
target_time = datetime.time(hour=15, minute=00, second=00, tzinfo=pytz.timezone('Europe/Rome'))
j.run_daily(compute_opening_turns, context=updater, days=[3],
            time=target_time)

# Turns poll
target_time = datetime.time(hour=12, minute=00, second=00, tzinfo=pytz.timezone('Europe/Rome'))
j.run_daily(send_poll, context=updater, days=[0],
            time=target_time)

# Trash memos
target_time = datetime.time(hour=20, minute=00, second=00, tzinfo=pytz.timezone('Europe/Rome'))
j.run_daily(send_trash_memo, context=updater,
            time=target_time)

# Remind people to vote for turns
target_time = datetime.time(hour=12, minute=00, second=00, tzinfo=pytz.timezone('Europe/Rome'))
j.run_daily(urge_voting, context=updater, days=(1, 2, 3, 4, 5, 6),
            time=target_time)


gis = GoogleImagesSearch(constants.GOOGLE_API_KEY, constants.CX)
updater.start_polling()
updater.idle()
