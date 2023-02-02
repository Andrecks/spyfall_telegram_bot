import os
import json
import asyncio
import time
import threading
#####################################

from telegram.ext import Updater, CallbackQueryHandler, InlineQueryHandler, ChosenInlineResultHandler
from telegram import CallbackQuery, ReplyKeyboardRemove, Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, Bot, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineQueryResult  # noqa
from telegram.ext import CallbackContext, Filters
from telegram.ext import CommandHandler, MessageHandler

#####################################
# можно удалить при сборке докерфайла
# from dotenv import load_dotenv
# load_dotenv()
#####################################
from bd_utils import workWithBD  # noqa
from threads import MyThread, AnotherThread

bd_class = workWithBD()

#####################################

from keyboards import KeyboardController  # noqa

keyboard_class = KeyboardController()

#####################################


updater = Updater(token=os.getenv('TOKEN'))
bot = Bot(token=os.getenv('TOKEN'))


# обработка входа бота в конфу
def new_member(update: Update, context: CallbackContext):
    chat_id = context._chat_id_and_data[0]
    lang_code = update.effective_user.language_code
    if not language_available(update.effective_user.language_code):
        # DEFAULT LANGUAGE SET
        lang_code = 'ru'
    create_lobby(chat_id, lang_code, update._effective_chat.title)
    messages = load_messages(lang_code)
    for member in update.message.new_chat_members:
        if member.username == 'spyfall_dungeon_master_bot':
            update.message.reply_text(messages['start'])


###
# Utils:

def create_lobby(chat_id, lang_code, chat_name):
    if not bd_class.check_lobby_exists(chat_id):
        if language_available(lang_code):
            bd_class.create_new_lobby(chat_id, lang_code)
        else:
            bd_class.create_new_lobby(chat_id)

        bd_class.set_chat_name(chat_id, chat_name)
    return


def send_message(chat_id, message, **kwargs):
    return bot.send_message(chat_id=chat_id, text=message, **kwargs)


def language_available(lang_code):
    'check avialable localizations'
    languages = ['ru']
    if lang_code in languages:
        return True
    return False


def load_messages(lang_code):
    text = open(f'text_{lang_code}.json')
    return json.load(text)

def load_rules(lang_code):
    text = open(f'rules/rules_{lang_code}.json')
    return json.load(text)


def migchat(update: Update, context: CallbackContext):
    oldchatid = update.message.migrate_from_chat_id
    newchatid = update.message.chat.id
    bd_class.update_chat_id(oldchatid, newchatid)
    return

def send_rules(update: Update, context: CallbackContext):
    # user_id = update.effective_user.id
    # print(update)
    lang_code = update.effective_user.language_code
    if not language_available(lang_code):
        # DEFAULT LANGUAGE SET
        lang_code = 'ru'
    rules = load_rules(lang_code)
    messages = load_messages(lang_code)

    query = update.callback_query.data.split('#')

    page = int(query[1])
    if page != 1 and page != 9:
        keyboard = [[InlineKeyboardButton('<', callback_data=f'rules#{page-1}'), InlineKeyboardButton('>', callback_data=f'rules#{page+1}')]]
    elif page == 1:
        keyboard = [[InlineKeyboardButton('>', callback_data=f'rules#{page+1}')]]
    elif page == 9:
        keyboard = [[InlineKeyboardButton('<', callback_data=f'rules#{page-1}')]]

    keyboard.append([InlineKeyboardButton(messages['send_locs'], callback_data=f'send_locs#{lang_code}')])

    print(f'page is {page}')
    update.callback_query.message.edit_text(rules[f'rules#{page}'], reply_markup=InlineKeyboardMarkup(keyboard, resize_keyboard=True))


def send_locs(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    #  send_locs#<lang_code>#pack@pack2@pack3
    data = update.callback_query.data.split('#')
    print(f'data is {data}')
    lang_code = data[1]
    messages = load_messages(lang_code)
    location_packs = []
    locations_file = open(f'location_packs/locations_{lang_code}.json')
    all_locations = json.load(locations_file)
    locations = []

    

    if len(data) > 2:
        packs = data[2]
        lobby_id = data[3]
        chat_name = bd_class.get_chat_name_from_lobby_id(lobby_id)
        message = messages['dlc_chat'].format(chat_name)
        location_packs = packs.split('@')
        while("" in location_packs):
            location_packs.remove("")
    else:
        send_message(user_id, messages["locs_send"])
        message = messages["dlc"]
        for pack in all_locations.keys():
            location_packs.append(pack)

    for pack in location_packs:
        for location in all_locations[pack]['locations']:
            locations.append(location['name'])
        send_message(user_id,  f'{message}: {pack}\n' + '\n'.join(locations))


# Buttons:

# /newgame message keyboard
def start_game_btn(update: Update, context: CallbackContext):
    asyncio.run(start_game_btn_async(update, context))
    return

async def start_game_btn_async(update: Update, context: CallbackContext):
    # pattern = start#{id}

    query = update.callback_query
    chat_id = int(query.data.split('#')[1])
    chat_name = str(query.data.split('#')[2])

    bd_class.check_and_update_chat_name(chat_id, chat_name)

    lang_code = bd_class.get_lobby_language(chat_id)
    messages = load_messages(lang_code)
    lobby_id = bd_class.get_lobby_id(chat_id)
    await asyncio.sleep(1)
    user_id = update.effective_user.id
    players = bd_class.get_player_list(lobby_id)

    if bd_class.check_lobby_started(lobby_id):
        query.answer(messages['lobby_already_started'])
        return
    if user_id not in players:
        query.answer(messages['player_not_joined'])
        return
    if len(players) < 3:
        query.answer(messages['not_enough_players'])

    else:
        # запуск игры

        true_false = start_game(chat_id, lang_code, chat_name)
        if true_false:
            player = bd_class.get_active_turn_player_name_id_username(lobby_id)

            #TODO: продумать реализацию таргета
            keyboard = keyboard_class.generate_turn_keyboard(player, lobby_id,
                                                            messages['turn_kb_target'],
                                                            messages['question_btn'],
                                                            messages['send_locs_btn'])

            reply_markup = InlineKeyboardMarkup(keyboard, reisize_keyboard=True)

            update.callback_query.message.edit_text(
                messages["game_started_text"].format(player[0], player[1]),
                reply_markup=reply_markup, parse_mode='Markdown'
            )
        else:
            bd_class.set_lobby_started(lobby_id, False)
            update.callback_query.message.edit_text(
                messages["game_canceled"],
                reply_markup = ReplyKeyboardRemove
            )
        return


def join_game_lobby_btn(update: Update, context: CallbackContext):
    asyncio.run(join_game_lobby_btn_async(update, context))
    return

def username_correcto(username):
    if username[0] != '@':
        correcto = '@' + username
        return correcto
    return username

async def join_game_lobby_btn_async(update: Update, context: CallbackContext):
    #TODO: лимитировать количество лобби для оного игрока (один игрок - одно лобби)
    # pattern = join#{id}
    query = update.callback_query
    chat_id = int(query.data.split('#')[1])
    lobby_id = bd_class.get_lobby_id(chat_id)
    await asyncio.sleep(1)
    lang_code = bd_class.get_lobby_language(chat_id)
    messages = load_messages(lang_code)

    user_id = update.effective_user.id

    if bd_class.check_lobby_started(lobby_id):
        query.answer(messages['lobby_already_started'])
        return

    if not bd_class.check_player_exists(user_id):

        print(f'user is {update.effective_user}')
        username = username_correcto(update.effective_user.name)
        bd_class.insert_player(user_id, update.effective_user.full_name, username)

    players = bd_class.get_player_list(lobby_id)

    false_or_lobby_id = bd_class.check_user_not_in_another_lobby(user_id, lobby_id)
    if false_or_lobby_id:
        chat_name = bd_class.get_chat_name_from_lobby_id(lobby_id)
        query.answer(messages['player_in_another_lobby'].format(chat_name))
        return

    if user_id in players:
        query.answer(messages['already_joined'])
        return

    bd_class.add_player_to_lobby(user_id, chat_id)  # noqa
    query.answer(messages['player_join_lobby'])
    count = bd_class.count_players(lobby_id)
    update.callback_query.message.edit_text(
        messages["new_lobby"] % count,
        reply_markup=update.callback_query.message.reply_markup
    )
    return


def open_settings_btn(update: Update, context: CallbackContext):
    query =  update.callback_query
    chat_id = int(query.data.split('#')[1])
    lang_code = bd_class.get_lobby_language(chat_id)
    messages = load_messages(lang_code)

    pass


def leave_lobby_btn(update: Update, context: CallbackContext):
    asyncio.run(leave_lobby_btn_async(update, context))


async def leave_lobby_btn_async(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split('#')[1])
    user_id = update.effective_user.id
    lobby_id = bd_class.get_lobby_id(chat_id)
    await asyncio.sleep(1)
    lang_code = bd_class.get_lobby_language(chat_id)
    messages = load_messages(lang_code)

    if bd_class.check_lobby_started(lobby_id):
        query.answer(messages['lobby_already_started'])
        return

    players = bd_class.get_player_list(lobby_id)
    if user_id in players:
        bd_class.remove_player_from_lobby(user_id, chat_id)
        query.answer(messages['player_left_lobby'])
        count = bd_class.count_players(lobby_id)
        query.answer(messages['player_left_lobby'])
        update.callback_query.message.edit_text(
            messages["new_lobby"] % count,
            reply_markup=update.callback_query.message.reply_markup
        )
        return
    query.answer(messages['player_not_joined'])
    return


def location_guess(update: Update, context: CallbackContext):
    asyncio.run(location_guess_async(update, context))

async def location_guess_async(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    lobby_id = bd_class.get_lobby_id_from_user(user_id)
    lang_code = bd_class.get_lobby_language_from_lobby_id(lobby_id)
    messages = load_messages(lang_code)
    spy_role = str(query.data.split('#')[2])
    await asyncio.sleep(1)
    if bd_class.check_user_id_spy(user_id, spy_role):
        spy_name = bd_class.get_player_name(user_id)
        true_location = bd_class.get_lobby_location_from_lobby_id(lobby_id)
        location = str(query.data.split('#')[1])
        if location == true_location:
            bd_class.add_score_user(user_id, 4)
            bot.edit_message_text(inline_message_id=update.callback_query.inline_message_id, reply_markup = None ,text=messages["spy_guess_correct"].format(spy_name, true_location))
        else:
            players = bd_class.get_player_list(lobby_id)
            for player in players:
                if player != user_id:
                    bd_class.add_score_user(player, 1)
            bot.edit_message_text(inline_message_id=update.callback_query.inline_message_id, reply_markup = None , text=messages["spy_guess_incorrect"].format(spy_name, true_location))
        send_message(chat_id, messages["end_game_reminder"])
        bd_class.remove_players_from_lobby(lobby_id)

    
    #TODO: снять лобби с паузы, поменять started на False
    #TODO: убрать всех плееров из таблицы lobby_players с lobby_id
    #TODO: допилить сообщения: добавить упоминание о начале новой игры через /newgame
    return

def page_flip(update: Update, context: CallbackContext):
    asyncio.run(page_flip_async(update, context))


async def page_flip_async(update: Update, context: CallbackContext):
    query = update.callback_query.data.split('#')
    # print(query)
    user_id = update.effective_user.id
    lobby_id = bd_class.get_lobby_id_from_user(user_id)
    spy_role = str(query[3])
    page_num = int(query[2])
    prev_next = str(query[1])
    if bd_class.check_user_id_spy(user_id, spy_role):
        if prev_next == 'prev':
            markup = InlineKeyboardMarkup(keyboard_class.generate_locations_keyboard(lobby_id, page_num-1, spy_role), reisize_keyboard=True)
            bot.editMessageReplyMarkup(inline_message_id = update.callback_query.inline_message_id, reply_markup = markup)
        elif prev_next == 'next':
            markup = InlineKeyboardMarkup(keyboard_class.generate_locations_keyboard(lobby_id, page_num+1, spy_role), reisize_keyboard=True)
            bot.editMessageReplyMarkup(inline_message_id = update.callback_query.inline_message_id, reply_markup = markup)

    await asyncio.sleep(1)
    return

def check_vote_started(lobby_id, chat_id, lang_code):
    messages = load_messages(lang_code)

    if bd_class.check_vote_started(lobby_id) is not None:
        print('vote started')
        return
    else:
        print('vote didnt start')
        bd_class.set_lobby_paused(lobby_id, False)
        send_message(chat_id, messages["game_resumed"])

        player = bd_class.get_active_turn_player_name_id_username(lobby_id)
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton( text=f'🔎 задать вопрос', switch_inline_query_current_chat = '')],
                                               [InlineKeyboardButton( text=messages["turn_kb_target"], callback_data= f'target#{player[1]}')]], reisize_keyboard=True)
        send_message(chat_id,
            messages["default_turn_msg"].format(player[0], player[1]),
            reply_markup=reply_markup, parse_mode='Markdown'
        )
    return


def start_vote(update: Update, context: CallbackContext):
    asyncio.run(start_vote_async(update, context))


def check_vote_started(lobby_id, chat_id, lang_code, user_id):
    # user_id = update.effective_user.id
    lobby_id = bd_class.get_lobby_id_from_user(user_id)
    if not lobby_id:
        return
    lang_code = bd_class.get_lobby_language_from_lobby_id(lobby_id)
    messages = load_messages(lang_code)
    chat_id = bd_class.get_chat_id_from_lobby_id(lobby_id)
    if bd_class.check_vote_started(lobby_id) is not None:
        print('vote started')
        return
    else:
        print('vote didnt start')
        bd_class.set_lobby_paused(lobby_id, False)
        active_player = bd_class.get_active_answer_player_name_id_username(lobby_id)
        if active_player is not None:
            active_player_id = active_player[1]
            asker_name = bd_class.get_asker_name(active_player_id)
            question = bd_class.get_question_asked(active_player_id)
            message = messages["resumed_answer_txt"].format(active_player[0], active_player_id, asker_name, question)
            keyboard = keyboard_class.generate_answer_keyboard(messages["answer_text"], messages["turn_kb_target"], active_player[0])
        else:
            active_player = bd_class.get_active_turn_player_name_id_username(lobby_id)
            message = messages["default_turn_msg"].format(active_player[0], active_player[1])
            keyboard = keyboard_class.generate_turn_keyboard(active_player, lobby_id,
                                                             messages["turn_kb_target"],
                                                             messages['question_btn'],
                                                             messages['send_locs_btn'])

        send_message(chat_id, messages["game_resumed"])

        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True)
        send_message(chat_id,
            message,
            reply_markup=reply_markup, parse_mode='Markdown'
        )
    return

async def start_vote_async(update, context):
    # query = update.callback_query.data.split('#')
    await asyncio.sleep(1)
    user_id = update.effective_user.id
    lobby_id = bd_class.get_lobby_id_from_user(user_id)
    lang_code = bd_class.get_lobby_language_from_lobby_id(lobby_id)
    messages = load_messages(lang_code)
    chat_id = bd_class.get_chat_id_from_lobby_id(lobby_id)
    if bd_class.check_lobby_paused(lobby_id):
        update.callback_query.answer(messages["another_vote_active"])
        return

    player_name = bd_class.get_player_name(user_id)
    lang_code = bd_class.get_lobby_language_from_lobby_id(lobby_id)
    messages = load_messages(lang_code)
    bd_class.set_lobby_paused(lobby_id, True)

    keyboard = keyboard_class.generate_vote_keyboard(user_id, lobby_id)
    send_message(chat_id, messages["vote_started"].format(player_name, user_id), reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True),
                parse_mode='Markdown')
    thread = MyThread(1, 'thread1', 15, check_vote_started, lobby_id, chat_id, lang_code, user_id)
    thread.start()
    # time.sleep(15)




def check_vote_ended(vote_id):
    # whatever = [lobby_id, chat_id, lang_code, [active_player(name_id_username)], 'turn/answer',]
    whatever = bd_class.check_vote_not_ended(vote_id)
    if whatever:
        messages = load_messages(whatever[2])
        chat_id = whatever[1]
        lobby_id = whatever[0]
        bot.send_message(chat_id, messages["game_resumed"])
        active_player = whatever[3]
        bd_class.set_lobby_paused(whatever[0], False)
        if whatever[4] == 'turn':
            message = messages["default_turn_msg"]
            keyboard = keyboard_class.generate_turn_keyboard(active_player, lobby_id,
                                                            messages["turn_kb_target"],
                                                            messages['question_btn'],
                                                            messages['send_locs_btn'])
            send_message(chat_id, message.format(active_player[0], active_player[1]), reply_markup=InlineKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')
        elif whatever[4] == 'answer':
            active_player_id = active_player[1]
            asker_name = bd_class.get_asker_name(active_player_id)
            question = bd_class.get_question_asked(active_player_id)
            message = messages["resumed_answer_txt"].format(active_player[0], active_player_id, asker_name, question)
            keyboard = keyboard_class.generate_answer_keyboard(messages["answer_text"], messages["turn_kb_target"], active_player[1])
            send_message(chat_id, message, reply_markup=InlineKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')
    else:
        return



def stop_game_start_vote(update: Update, context: CallbackContext):
    print('hello')
    asyncio.run(stop_game_start_vote_async(update, context))

async def stop_game_start_vote_async(update: Update, context: CallbackContext):
    # choose#{player[0]}#{lobby_id}#{user_id}
    # print('hello')
    query = update.callback_query.data.split('#')
    lobby_id = int(query[2])
    # chat_id = bd_class.get_chat_name_from_lobby_id(lobby_id)

    lang_code = bd_class.get_lobby_language_from_lobby_id(lobby_id)
    messages = load_messages(lang_code)

    user_id = int(update.effective_user.id)
    user_name = bd_class.get_player_name(user_id)
    await asyncio.sleep(1)
    if int(user_id) != int(query[3]):
        print(f'{user_id} == {query[3]}')
        update.callback_query.answer(messages["wrong_user_vote"])
        return
    # elif bd_class.check_lobby_paused(lobby_id):
    #     update.callback_query.answer(messages["another_vote_active"])
    #     return

    chosen_player_id = query[1]
    chosen_player_name = bd_class.get_player_name(chosen_player_id)

    bd_class.start_new_vote(lobby_id, user_id, chosen_player_id)

    vote_id_to_end = bd_class.get_vote_id(user_id, lobby_id)
    not_voted = bd_class.players_still_not_voted(lobby_id, chosen_player_id)
    vote_time_sec = bd_class.get_vote_time_from_lobby_id(lobby_id)
    keyboard = keyboard_class.generate_vote_kb(lobby_id, chosen_player_id)
    update.callback_query.message.edit_text(messages["target_chosen"].format(user_name, user_id, chosen_player_name, chosen_player_id, ', '.join([x[0] for x in not_voted]), vote_time_sec),
                reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode='Markdown')
    #TODO: вместо 20 поставить vote_time_sec
    another_thread = AnotherThread(1000, check_vote_ended, vote_id_to_end)
    another_thread.start()
    return

def vote(update: Update, context: CallbackContext):
    asyncio.run(vote_async(update, context))

async def vote_async(update, context):
    
    user_id = int(update.effective_user.id)
    # agree#{lobby_id}#{target_id}#yes/no
    query = update.callback_query.data.split('#')
    lobby_id = int(query[1])
    target_id = int(query[2])
    yes_no = str(query[3])
    chat_id = bd_class.get_chat_id_from_lobby_id(lobby_id)
    lang_code = bd_class.get_lobby_language_from_lobby_id(lobby_id)
    messages = load_messages(lang_code)

    if bd_class.player_already_voted(user_id, lobby_id):
        update.callback_query.answer(messages["user_already_voted"])
        return

    elif not bd_class.check_player_in_current_lobby(user_id, lobby_id):
        update.callback_query.answer(messages["not_in_lobby"])
        return

    bd_class.add_vote(lobby_id, user_id, target_id, yes_no)
    await asyncio.sleep(1)
    player_count = len(bd_class.get_player_list(lobby_id)) - 1
    if bd_class.get_votes_count(lobby_id) ==  player_count:
        bd_class.set_lobby_paused(lobby_id, False)
        if bd_class.check_all_voted_yes(lobby_id, player_count):
            bd_class.set_lobby_started(lobby_id, False)
            spy = bd_class.get_spy_name_id(messages["spy_role"])
            target = bd_class.get_target_name_id(target_id)
            started_vote = bd_class.get_started_vote_name_id(lobby_id)
            bd_class.remove_vote_lobby_id(lobby_id)
            if bd_class.check_target_is_spy(lobby_id, target_id, messages["spy_role"]):


                send_message(chat_id, messages["voted_correct"].format(spy[0], spy[1], started_vote[0], started_vote[1], parse_mode='Markdown'))
                players = bd_class.get_player_list(lobby_id)
                for player in players:
                    if player != spy[1]:
                        bd_class.add_score_user(player, 1)
                    elif player == started_vote[1]:
                        bd_class.add_score_user(player, 1)
                #TODO: вычислили пральна, добавить по очку всем и плюс один тому, кто стартовал голосование
            else:
                send_message(chat_id, messages["voted_incorrect"].format(target[0], target[1], spy[0], spy[1]), parse_mode='Markdown')
                bd_class.add_score_user(spy[1], 2)
                #TODO: вычислили не того, шпиону +2 очка
            send_message(chat_id, messages["end_game_reminder"])
            bd_class.remove_players_from_lobby(lobby_id)
        else:
            vote_id = bd_class.get_vote_id_from_user_id(user_id)
            check_vote_ended(vote_id)
    else:
        id_name = bd_class.get_started_vote_player_id_name(lobby_id)
        chosen_player_name = bd_class.get_player_name(target_id)
        not_voted = bd_class.players_still_not_voted(lobby_id, target_id)
        vote_time_sec = bd_class.get_vote_time_from_lobby_id(lobby_id)
        keyboard = keyboard_class.generate_vote_kb(lobby_id, target_id)
        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True)
        update.callback_query.message.edit_text(messages["target_chosen"].format(id_name[1], id_name[0], chosen_player_name, str(target_id), ', '.join([x[0] for x in not_voted]), vote_time_sec),
                                                reply_markup=reply_markup, parse_mode='Markdown')
        return
    print('problemo del voto lol')
    return

# turn keyboard

# def ask_btn(update: Update, context: CallbackContext):
#     user_id = update.effective_user.id
#     chat_id = update.effective_chat.id
#     query = update.callback_query
#     if bd_class.check_lobby_exists(chat_id):
#         lobby_id = bd_class.get_lobby_id(chat_id)
#         if bd_class.check_lobby_started(lobby_id) and not bd_class.check_lobby_paused(lobby_id):
#             print('HELLO')
#             print(f'the update is {update}')
#             print(f'the query is {query}')


#     else:
#         if not language_available(update.effective_user.language_code):
#         # DEFAULT LANGUAGE SET
#             lang_code = 'ru'
#         else:
#             lang_code = bd_class.get_lobby_language(update.effective_chat.id)
#         messages = load_messages(lang_code)
#         query.answer(messages['lobby_not_found'])

###

###
# Commands:f
# /start
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if update.effective_chat.type == 'private':
        lang_code = update.effective_user.language_code
        if not language_available(update.effective_user.language_code):
            # DEFAULT LANGUAGE SET
            lang_code = 'ru'
        messages = load_messages(lang_code)
        keyboard = [[InlineKeyboardButton(messages['start_kb_continue'], callback_data='rules#1')],
                    [InlineKeyboardButton(messages['send_locs'], callback_data=f'send_locs#{lang_code}')]]
        markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True)
        send_message(user_id, messages["welcome"], reply_markup=markup)

    else:
        lang_code = bd_class.get_lobby_language(update.effective_chat.id)
        messages = load_messages(lang_code)
        chat_id = update.effective_chat.id
        send_message(chat_id, messages['start_group'])


    return

# /update_username_nameа
def update_username_name(update: Update, context: CallbackContext):
    bd_class.update_name_username(
        update.effective_user.id,
        update.effective_user.username,
        update.effective_user.name
    )

# /newgame
def open_lobby(update: Update, context: CallbackContext):
    chat_id = update.message.chat.id
    user_id = update.effective_user.id
    chat_data = bot.get_chat(chat_id)
    lobby_id = bd_class.get_lobby_id(chat_id)
    chat_name = chat_data.title
    if not bd_class.check_lobby_exists(chat_id):
        lang_code = update.effective_user.language_code
        if not language_available(lang_code):
            # DEFAULT LANGUAGE SET
            lang_code = 'ru'
        create_lobby(chat_id, lang_code, chat_name)
    else:
        lang_code = bd_class.get_lobby_language(chat_id)
    messages = load_messages(lang_code)

    if not bd_class.check_player_exists(user_id):
        username = update.effective_user.username

        username = username_correcto(username)
        bd_class.insert_player(user_id, update.effective_user.full_name, username)

    lobby_id = bd_class.get_lobby_id(chat_id)
    players = bd_class.get_player_list(lobby_id)
    if user_id not in players:
        bd_class.add_player_to_lobby(user_id, chat_id)
    count = bd_class.count_players(lobby_id)
    print(f'lobby {lobby_id} has {count} players')
    keyboard = keyboard_class.generate_new_lobby_keyboard(
        chat_id,
        update._effective_chat.title,
        messages["start_kb_start"],
        messages["start_kb_join"],
        messages["start_kb_settings"],
        messages["start_kb_leave"])
    reply_markup = InlineKeyboardMarkup(keyboard, reisize_keyboard=True,)
    send_message(update.message.chat.id, messages["new_lobby"] % count, reply_markup = reply_markup)  # noqa
    return

###########################################################
# Inline Queries:

def inline_query(update: Update, context: CallbackContext) -> None:
    """Handle the inline query. This is run when you type: @botusername <query>"""
    print('welcum')
    user_id = update.effective_user.id
    lobby_id = bd_class.get_lobby_id_from_user(user_id)
    chat_id = bd_class.get_chat_id_from_lobby_id(lobby_id)
    lang_code = bd_class.get_lobby_language(chat_id)

    username = update.effective_user.name
    name = update.effective_user.full_name
    # проверка нейма и юзернейма в базе
    bd_class.check_name_username_correct(user_id, username, name)

    messages = load_messages(lang_code)
    query = update.inline_query.query
    spy_role = messages["spy_role"]
    results = []

    if bd_class.check_lobby_paused(lobby_id) or not bd_class.check_lobby_started(lobby_id):
        return

    elif (query == ''):
        if bd_class.check_user_id_spy(user_id, spy_role):
            results.append(InlineQueryResultArticle(
                id = f'info#{user_id}',
                title = messages["info_message"],
                description = messages["info_location_spy"].format(bd_class.get_player_role(lobby_id, user_id)),
                input_message_content = InputTextMessageContent(message_text='хто я')
            ))
            results.append(InlineQueryResultArticle(
                    id = 'guess_location#',
                    title = messages["guess_location"],
                    description = messages['guess_msg'],
                    thumb_url='https://cdn-icons-png.flaticon.com/512/2058/2058160.png',
                    input_message_content = InputTextMessageContent(message_text=messages["guess_msg"]),
                    reply_markup = InlineKeyboardMarkup(keyboard_class.generate_locations_keyboard(lobby_id, 1, messages["spy_role"]),
                                                        reisize_keyboard=True)))
        else:
            results.append(InlineQueryResultArticle(
                id = f'info#{user_id}',
                title = messages["info_message"],
                description = messages["info_location"].format(bd_class.get_lobby_location(chat_id),
                                                               bd_class.get_player_role(lobby_id, user_id)),
                input_message_content= InputTextMessageContent(message_text='хто я')
            ))
        update.inline_query.answer(results, cache_time=0)
        return

    # если лобби находится на паузе, значит не принимаем вопросы и ответы

    if bd_class.check_user_active_answer(user_id):
        asker = bd_class.get_player_username(bd_class.get_who_asked(user_id))
        results.append(
        InlineQueryResultArticle(
                id = f'answer#',
                title = f'{messages["answer_text"]}',
                description = f"{messages['answer_text']} {query}",
                thumb_url='https://sun9-19.userapi.com/impg/NpJWwSd1fr-Ql-ZIMUfO5eYkiicrRbh5WO132Q/0jaNNyXg-dw.jpg?size=128x128&quality=96&sign=58a242e77a56e5d06cfa67e3ca12e749&type=album',
                input_message_content = InputTextMessageContent(message_text=f'{asker}, {query}'),
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(messages["turn_kb_target"],
                                                                            callback_data=f'target#{user_id}#')]],
                                                    reisize_keyboard=True)
        )
        )

    elif bd_class.check_player_active(user_id):
        question = query
        if question and question[-1] != '?':
            question += '?'

        players = bd_class.get_player_list_id_name_username(lobby_id)
        asked = bd_class.get_who_asked(user_id)
        for player in players:
            if player[0] != user_id and player[0] != asked:
                results.append(
                    InlineQueryResultArticle(
                        id = f'ask#{player[0]}',
                        title = f'{messages["enter_question"].format(player[1])}',
                        description = messages['inline_ask_description'].format(player[2], question),
                        thumb_url='https://www.pngfind.com/pngs/m/2-24050_question-mark-png-image-transparent-white-question-mark.png',
                        input_message_content = InputTextMessageContent(message_text=f'{player[2]}, {question}'),
                        reply_markup = InlineKeyboardMarkup(keyboard_class.generate_answer_keyboard(messages["answer_text"], messages["turn_kb_target"], user_id),
                                                            reisize_keyboard=True)))

    if bd_class.check_user_id_spy(user_id, spy_role):
        results.append(InlineQueryResultArticle(
                            id = 'guess_location#',
                            title = messages["guess_location"],
                            description = messages['guess_msg'],
                            thumb_url='https://cdn-icons-png.flaticon.com/512/2058/2058160.png',
                            input_message_content = InputTextMessageContent(message_text=messages["guess_msg"]),
                            reply_markup = InlineKeyboardMarkup(keyboard_class.generate_locations_keyboard(lobby_id, 1, messages["spy_role"]),
                                                                reisize_keyboard=True)))
    # else:
    #     print('hello?')
    #     return
    # ссылка на png со списком локций
    # thumb_url='https://sun9-25.userapi.com/impg/a2NMifqpi-aHbs6ZY57u4FWHisgjSAZ87WWM8g/oXfEU2tp_jc.jpg?size=1024x1024&quality=96&sign=923c693e180dc82b32ffc5c36b9f95da&type=album',
    update.inline_query.answer(results, cache_time=0)
    return


# def inline_query_magic(update: Update, context: CallbackContext):
#     asyncio.run(inline_query_magic_async(update, context))


def inline_query_magic(update: Update, context: CallbackContext):
    '''Here we catch all possible inline queries and do something with it yay'''
    # TODO: Доделать обработку инлоайнов
    # ask#<user_id>
    # answer#
    print('inline option was chosen!')
    print(f'update is {update}')
    option_id = update.chosen_inline_result.result_id.split('#')
    user_id = update.effective_user.id
    lobby_id = bd_class.get_lobby_id_from_user(user_id)
    chat_data = bot.get_chat(bd_class.get_chat_id_from_lobby_id(lobby_id))
    chat_name = chat_data.title
    chat_id = chat_data.id
    print(f'user_id is {user_id}')
    lang_code = bd_class.get_lobby_language_from_lobby_id(lobby_id)



    messages = load_messages(lang_code)
    if option_id[0] == 'ask':
        if option_id[1]:
            target_id = option_id[1]

        question = update.chosen_inline_result.query
        if question[-1] != '?':
            question += '?'
        bd_class.save_question_for_user(question, target_id)
        bd_class.set_player_active_turn(user_id, False)
        bd_class.set_player_active_answer(target_id, True)
        bd_class.set_who_asked(target_id, user_id)
        send_message(target_id, messages["new_question"].format(chat_name))
        return

    elif option_id[0] == 'answer':
        print('answered question')
        # bd_class.set_player_active_answer(user_id, False)
        # current_active_player_id = bd_class.get_active_turn_player_name_id_username(lobby_id)[1]
        # bd_class.set_player_active_turn(current_active_player_id, False)
        bd_class.set_player_active_answer(user_id, False)
        bd_class.set_player_active_turn(user_id, True)
        #TODO отправить сообщение в конфу с новым водящим и клавиатурой выбора

        player = bd_class.get_active_turn_player_name_id_username(lobby_id)

        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton( text=f'🔎 задать вопрос', switch_inline_query_current_chat = '')],
                                             [InlineKeyboardButton( text=messages["turn_kb_target"], callback_data= f'target#{player[1]}')]], reisize_keyboard=True)
        send_message(chat_id,
            messages["default_turn_msg"].format(player[0], player[1]),
            reply_markup=reply_markup, parse_mode='Markdown'
        )
        return

    elif option_id[0] == 'guess_location':
        bd_class.set_lobby_paused(lobby_id, True)

        # send_message(text=messages["default_turn_msg"].format(player[0], player[1]))
        #TODO после этого доделать механику обвинения (с таймингом)
    # await asyncio.sleep(1)

    return


###########################################################
def main():
    # bot.setMyCommands()
    updater.start_polling()


###########################################################
# game starts here...



def start_game(chat_id, lang_code, chat_name):
    flag = True
    lobby_id = bd_class.get_lobby_id(chat_id)
    messages = load_messages(lang_code)
    spy_role = messages['spy_role']
    #TODO: Раскомментить точбы игра началась)
    bd_class.start_game(chat_id, lang_code, spy_role)
    location = bd_class.get_lobby_location(chat_id)
    names_failures = []
    for player in bd_class.get_player_list(lobby_id):
        role = bd_class.get_player_role(lobby_id, player)
        try:
            # TODO: добавить inlinequery handler для всех и для того, кто ходит
            # TODO:  у всех должна быть возможность прислать им список локаций и открыть обвинение на игрока
            # TODO: если обвинение от игрока x игроку y уже есть в этом лобби, то отправить его
            if role != spy_role:
                send_message(player, messages['game_start_msg'].format(chat_name, role, location))  # noqa
            else:
                send_message(player, messages['game_start_msg_spy'].format(chat_name, role))

        except:
            flag = False
            names_failures.append(bd_class.get_player_username(player))
            continue

    if not flag:
        message = messages['ERROR_0'].format(', '.join(names_failures))
        send_message(chat_id, message)

    return flag


###
# Handlers:
updater.dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_member))  # noqa
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('newgame', open_lobby))
updater.dispatcher.add_handler(CommandHandler('update_name_username', update_username_name))
# Button handlers
#/newgame keyboard
updater.dispatcher.add_handler(CallbackQueryHandler(start_game_btn, pattern=r'start#'))
updater.dispatcher.add_handler(CallbackQueryHandler(join_game_lobby_btn, pattern=r'join#'))
updater.dispatcher.add_handler(CallbackQueryHandler(open_settings_btn, pattern=r'settings#'))
updater.dispatcher.add_handler(CallbackQueryHandler(leave_lobby_btn, pattern=r'leave#'))

updater.dispatcher.add_handler(CallbackQueryHandler(location_guess, pattern=r'guess#'))
updater.dispatcher.add_handler(CallbackQueryHandler(page_flip, pattern=r'page#'))

updater.dispatcher.add_handler(CallbackQueryHandler(stop_game_start_vote, pattern=r'choose#'))
updater.dispatcher.add_handler(CallbackQueryHandler(start_vote, pattern=r'target#'))
#TODO поменять чтчобы обе функции вели в голосование
updater.dispatcher.add_handler(CallbackQueryHandler(vote, pattern=r'vote#'))


updater.dispatcher.add_handler(CallbackQueryHandler(send_rules, pattern=r'rules#'))
updater.dispatcher.add_handler(CallbackQueryHandler(send_locs, pattern=r'send_locs#'))

updater.dispatcher.add_handler(InlineQueryHandler(inline_query))
updater.dispatcher.add_handler(ChosenInlineResultHandler(inline_query_magic))
updater.dispatcher.add_handler(MessageHandler(Filters.status_update.migrate, migchat))
###

###########################################################
if __name__ == '__main__':
    # text_ru = open(f'text_ru.json')
    # messages = json.load(text_ru)
    main()


