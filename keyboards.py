from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bd_utils import workWithBD
import json

bd_unit = workWithBD()

class KeyboardController():

    def generate_new_lobby_keyboard(self, chat_id, chat_name,
                                    start_text, join_text, settings_text,
                                    leave_text):
        keyboard = [[InlineKeyboardButton(f'{start_text} 🚀', callback_data=f'start#{chat_id}#{chat_name}')],
                    [InlineKeyboardButton(f'{join_text} 🔗', callback_data=f'join#{chat_id}#{chat_name}')],
                    [InlineKeyboardButton(f'{settings_text} ⚙️', callback_data=f'settings#{chat_id}#{chat_name}')],
                    [InlineKeyboardButton(f'{leave_text} 🚪', callback_data=f'leave#{chat_id}#{chat_name}')]
        ]
        return keyboard

    def generate_turn_keyboard(self, active_player, lobby_id, turn_kb_target, question_btn, send_loc_text):
        lang_code = bd_unit.get_lobby_language_from_lobby_id(lobby_id)
        locations = '@'.join(bd_unit.get_lobby_location_packs(lobby_id))
        keyboard = [[InlineKeyboardButton(turn_kb_target, callback_data=f'target#{active_player[1]}#{lobby_id}')],
                    [InlineKeyboardButton(text=question_btn, switch_inline_query_current_chat = '')],
                    [InlineKeyboardButton(send_loc_text, callback_data=f'send_locs#{lang_code}#{locations}#{lobby_id}')]]

        return keyboard

    def generate_answer_keyboard(self, answer_text, turn_kb_target, active_user_id):
        return [[InlineKeyboardButton(answer_text, switch_inline_query_current_chat='')],
                [InlineKeyboardButton(turn_kb_target, callback_data=f'target#{active_user_id}')]]

    def generate_locations_keyboard(self, lobby_id, page, spy_role):
        flag = True
        flag_2 = True
        keyboard = [[]]
        chat_id = bd_unit.get_chat_id_from_lobby_id(lobby_id)
        lang_code = bd_unit.get_lobby_language(chat_id)
        location_pack_list = bd_unit.get_lobby_location_packs(lobby_id)
        locations_file = open(f'location_packs/locations_{lang_code}.json')
        all_locations = json.load(locations_file)
        location_list = []
        for loc_pack in location_pack_list:
             for location in all_locations[loc_pack]['locations']:
                location_list.append(location['name'])


        i = 0
        if (len(location_list) <= page*6):
            flag = False
        location_list = location_list[(page*6-6):page*6]
        for location in location_list:
            if i == 2:
                i = 0
                keyboard.append([])
            keyboard[-1].append(
                InlineKeyboardButton(location, callback_data=f'guess#{location}#{spy_role}')
            )
            i += 1

        if page != 1:
            keyboard.append([InlineKeyboardButton("<", callback_data=f'page#prev#{page}#{spy_role}')])
        else:
            flag_2 = False
        if flag:
            if flag_2:
                keyboard[-1].append(InlineKeyboardButton(">", callback_data=f'page#next#{page}#{spy_role}'))
            else:
                keyboard.append([InlineKeyboardButton(">", callback_data=f'page#next#{page}#{spy_role}')])
        return keyboard


    def generate_vote_keyboard(self, user_id, lobby_id):
        keyboard = []
        players = bd_unit.get_player_list_id_name_username(lobby_id)
        for player in players:
            if player[0] != user_id:
                keyboard.append([InlineKeyboardButton(player[1], callback_data=f'choose#{player[0]}#{lobby_id}#{user_id}')])

        return keyboard

    def generate_vote_kb(self, lobby_id, target_id):
        keyboard = [[InlineKeyboardButton('💀', callback_data=f'vote#{lobby_id}#{target_id}#yes'), InlineKeyboardButton('❌', callback_data=f'vote#{lobby_id}#{target_id}#no')]]
        return keyboard
    
    # def generate_loc_list(page):
    #     ...






# boban = KeyboardController()
# boban.generate_locations_keyboard(18, 1, 'nono')
###############################
