import os
import json
import asyncio
import time
#####################################

from telegram.ext import Updater, CallbackQueryHandler, InlineQueryHandler, ChosenInlineResultHandler
from telegram import CallbackQuery, ReplyKeyboardRemove, Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, Bot, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton  # noqa
from telegram.ext import CallbackContext, Filters
from telegram.ext import CommandHandler, MessageHandler

#####################################
# можно удалить при сборке докерфайла
from dotenv import load_dotenv
load_dotenv()
#####################################
from bd_utils import workWithBD  # noqa

bd_class = workWithBD()

#####################################

from keyboards import KeyboardController  # noqa

keyboard_class = KeyboardController()

#####################################


updater = Updater(token=os.getenv('TOKEN'))
bot = Bot(token=os.getenv('TOKEN'))

# list of active lobbies for inline_query
chats = bd_class.get_active_lobbies_chat_ids()

# обработка входа бота в конфу
def new_member(update: Update, context: CallbackContext):
    chat_id = context._chat_id_and_data[0]
    lang_code = update.effective_user.language_code
    if not language_available(update.effective_user.language_code):
        # DEFAULT LANGUAGE SET
        lang_code = 'ru'
    create_lobby(chat_id, lang_code)
    messages = load_messages(lang_code)
    for member in update.message.new_chat_members:
        if member.username == 'spyfall_dungeon_master_bot':
            update.message.reply_text(messages['start'])


###
# Utils:

def create_lobby(chat_id, lang_code):
    if not bd_class.check_lobby_exists(chat_id):
        if language_available(lang_code):
            bd_class.create_new_lobby(chat_id, lang_code)
        else:
            bd_class.create_new_lobby(chat_id)
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


def migchat(update: Update, context: CallbackContext):
    oldchatid = update.message.migrate_from_chat_id
    newchatid = update.message.chat.id
    bd_class.update_chat_id(oldchatid, newchatid)
    return

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

    lang_code = bd_class.get_lobby_language(chat_id)
    messages = load_messages(lang_code)
    lobby_id = bd_class.get_lobby_id(chat_id)
    await asyncio.sleep(1)
    user_id = update.effective_user.id
    players = bd_class.get_player_list(lobby_id)

    # if bd_class.check_lobby_started(lobby_id):
    #     query.answer(messages['lobby_already_started'])
    #     return
    if user_id not in players:
        query.answer(messages['player_not_joined'])
        return
    if len(players) < 3:
        query.answer(messages['not_enough_players'])

    else:
        # запуск игры
        start_game(chat_id, lang_code, chat_name)
        player = bd_class.get_active_turn_player_name_id_username(lobby_id)
        players = bd_class.get_player_list_id_name_username(lobby_id)

        #TODO: продумать реализацию таргета
        keyboard = keyboard_class.generate_turn_keyboard(players, lobby_id,
                                                         messages['turn_kb_target'])

        reply_markup = InlineKeyboardMarkup(keyboard, reisize_keyboard=True)
        # keyboard = keyboard_class.generate_turn_keyboard()
        update.callback_query.message.edit_text(
            messages["game_started_text"].format(player[0], player[1]),
            reply_markup=reply_markup, parse_mode='MarkdownV2'
        )


def join_game_lobby_btn(update: Update, context: CallbackContext):
    asyncio.run(join_game_lobby_btn_async(update, context))
    return


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
        bd_class.insert_player(user_id, update.effective_user.name, update.effective_user.username)

    players = bd_class.get_player_list(lobby_id)

    if user_id in players:
        query.answer(messages['already_joined'])
        return

    bd_class.add_player_to_lobby(user_id, chat_id)  # noqa
    #TODO: сделать ограничение по лобби, для каждого игрока сделать только одно лобби
    query.answer(messages['player_join_lobby'])
    count = bd_class.count_players(chat_id)
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
        count = bd_class.count_players(chat_id)
        query.answer(messages['player_left_lobby'])
        update.callback_query.message.edit_text(
            messages["new_lobby"] % count,
            reply_markup=update.callback_query.message.reply_markup
        )
        return
    query.answer(messages['player_not_joined'])
    return

# turn keyboard

def ask_btn(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    query = update.callback_query
    if bd_class.check_lobby_exists(chat_id):
        lobby_id = bd_class.get_lobby_id(chat_id)
        if bd_class.check_lobby_started(lobby_id) and not bd_class.check_lobby_paused(lobby_id):
            print('HELLO')
            print(f'the update is {update}')
            print(f'the query is {query}')


    else:
        if not language_available(update.effective_user.language_code):
        # DEFAULT LANGUAGE SET
            lang_code = 'ru'
        else:
            lang_code = bd_class.get_lobby_language(update.effective_chat.id)
        messages = load_messages(lang_code)
        query.answer(messages['lobby_not_found'])

###

###
# Commands:f
# /start
def start(update: Update, context: CallbackContext):
    if update.effective_chat.type == 'private':
        lang_code = update.effective_user.language_code
        if not language_available(update.effective_user.language_code):
            # DEFAULT LANGUAGE SET
            lang_code = 'ru'
    else:
        lang_code = bd_class.get_lobby_language(update.effective_chat.id)
    messages = load_messages(lang_code)
    update.message.reply_text(messages['/start'])
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

    if not bd_class.check_lobby_exists(chat_id):
        lang_code = update.effective_user.language_code
        if not language_available(lang_code):
            # DEFAULT LANGUAGE SET
            lang_code = 'ru'
        create_lobby(chat_id, lang_code)
    else:
        lang_code = bd_class.get_lobby_language(chat_id)
    messages = load_messages(lang_code)

    if not bd_class.check_player_exists(user_id):
        bd_class.insert_player(user_id, update.effective_user.full_name, update.effective_user.username)
    lobby_id = bd_class.get_lobby_id(chat_id)
    players = bd_class.get_player_list(lobby_id)
    if user_id not in players:
        bd_class.add_player_to_lobby(user_id, chat_id)
    count = bd_class.count_players(chat_id)

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
    lang_code = update.effective_user.language_code
    user_id = update.effective_user.id
    username = update.effective_user.username
    name = update.effective_user.name
    # проверка нейма и юзернейма в базе
    if not bd_class.check_name_username_correct(user_id, username, name):
        ...

    if not language_available(lang_code):
        # DEFAULT LANGUAGE SET
        lang_code = 'ru'
    messages = load_messages(lang_code)
    query = update.inline_query.query
    payload = query.split(',')
    target = payload[0]

    lobby_id = bd_class.get_lobby_id_from_user(user_id)

    # если лобби находится на паузе, значит не принимаем вопросы и ответы
    if bd_class.check_lobby_paused(lobby_id):
        return

    if not bd_class.check_player_active(user_id):
        if not bd_class.check_user_active_answer(user_id):
            return
        else:
            print('YAYAYAY')
            asker = bd_class.get_active_turn_player_name_id_username(lobby_id)[2]
            results = [(
            InlineQueryResultArticle(
                    id = f'answer#',
                    title = f'{messages["answer_text"]}',
                    description = f"{messages['answer_text']} {query}",
                    thumb_url='https://sun9-19.userapi.com/impg/NpJWwSd1fr-Ql-ZIMUfO5eYkiicrRbh5WO132Q/0jaNNyXg-dw.jpg?size=128x128&quality=96&sign=58a242e77a56e5d06cfa67e3ca12e749&type=album',
                    input_message_content = InputTextMessageContent(message_text=f'{asker}, {query}'),
                    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(messages["turn_kb_target"].format(name),
                                                                              callback_data=f'target#{user_id}#{lobby_id}')]],
                                                        reisize_keyboard=True)
            )
            )]
            pass
    else:
        question = ', '.join(payload[1::])

        if question and question[-1] != '?':
            question += '?'
        results = [(
            InlineQueryResultArticle(
                id = f'ask#{target}',
                title = f'{messages["enter_question"]}',
                description = messages['inline_ask_description'].format(target, question),
                thumb_url='https://www.pngfind.com/pngs/m/2-24050_question-mark-png-image-transparent-white-question-mark.png',
                input_message_content = InputTextMessageContent(message_text=f'{target}, {question}'),
                reply_markup = InlineKeyboardMarkup(keyboard_class.generate_answer_keyboard(messages["answer_text"], messages["turn_kb_target"], user_id),
                                                    reisize_keyboard=True)
)
)]


    # ссылка на png со списком локций
    # thumb_url='https://sun9-25.userapi.com/impg/a2NMifqpi-aHbs6ZY57u4FWHisgjSAZ87WWM8g/oXfEU2tp_jc.jpg?size=1024x1024&quality=96&sign=923c693e180dc82b32ffc5c36b9f95da&type=album',
    update.inline_query.answer(results)
    return


def inline_query_magic(update: Update, context: CallbackContext):
    asyncio.run(inline_query_magic_async(update, context))


async def inline_query_magic_async(update: Update, context: CallbackContext):
    '''Here we catch all possible inline queries and do something with it yay'''
    # TODO: Доделать обработку инлоайнов
    # ask#<user_id>
    # answer#
    user_id = update.effective_user.id
    lobby_id = bd_class.get_lobby_id_from_user(user_id)
    chat_data = bot.get_chat(bd_class.get_chat_id_from_lobby_id(lobby_id))
    chat_name = chat_data.title

    lang_code = bd_class.get_lobby_language_from_lobby_id(lobby_id)
    option_id = update.chosen_inline_result.result_id.split('#')

    if option_id[1]:
        target_id = bd_class.get_target_id_from_username(option_id[1])
    messages = load_messages(lang_code)

    if option_id[0] == 'ask':
        # bd_class.set_player_active_turn(user_id, False)
        bd_class.set_player_active_answer(target_id, True)
        send_message(target_id, messages["new_question"].format(chat_name))
    elif option_id[0] == 'answer':
        bd_class.set_player_active_answer(user_id, False)
        current_active_player_id = bd_class.get_active_turn_player_name_id_username(lobby_id)[1]
        bd_class.set_player_active_turn(current_active_player_id, False)
        bd_class.set_player_active_turn(user_id, True)
        #TODO отправить сообщение в конфу с новым водящим и клавиатурой выбора
        #TODO после этого доделать механику обвинения (с таймингом)
    await asyncio.sleep(1)

    return


###########################################################
def main():
    # bot.setMyCommands()
    updater.start_polling()


###########################################################
# game starts here...



def start_game(chat_id, lang_code, chat_name):
    lobby_id = bd_class.get_lobby_id(chat_id)
    messages = load_messages(lang_code)
    spy_role = messages['spy_role']
    #TODO: Раскомментить точбы игра началась)
    bd_class.start_game(chat_id, lang_code, spy_role)
    location = bd_class.get_lobby_location(chat_id)
    names_failures = []
    for player in bd_class.get_player_list(lobby_id):
        role = bd_class.get_player_role(lobby_id, player)
        flag = True
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
        return


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
# turn keyboard
# updater.dispatcher.add_handler(CallbackQueryHandler(target_btn, pattern=r'target#'))
updater.dispatcher.add_handler(CallbackQueryHandler(ask_btn, pattern=r'ask#'))


updater.dispatcher.add_handler(InlineQueryHandler(inline_query))
updater.dispatcher.add_handler(ChosenInlineResultHandler(inline_query_magic))
updater.dispatcher.add_handler(MessageHandler(Filters.status_update.migrate, migchat))
###

###########################################################
if __name__ == '__main__':
    # text_ru = open(f'text_ru.json')
    # messages = json.load(text_ru)
    main()


