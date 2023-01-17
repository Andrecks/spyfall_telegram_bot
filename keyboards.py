from telegram import InlineKeyboardButton
from bd_utils import workWithBD


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

    def generate_turn_keyboard(self, players, lobby_id, turn_kb_target):
        # TODO: доделать механику вопросов и остановку и обвинения
        #  [InlineKeyboardButton(f'{start_text} 🚀', callback_data=f'start#{chat_id}#{chat_name}')]

        # ('@username', id)
        active_player = bd_unit.get_active_turn_player_name_id_username(lobby_id)
        keyboard = [[InlineKeyboardButton(turn_kb_target.format(active_player[0]),
                            callback_data=f'target#{active_player[1]}#{lobby_id}')]]
        for player in players:
            if player[0] != active_player[1]:
                keyboard.append([InlineKeyboardButton( text=f'{player[2]}❓', switch_inline_query_current_chat = f'{player[1]}, ')])
        return keyboard

    def generate_answer_keyboard(self, answer_text, turn_kb_target, active_user_id):
        active_player = bd_unit.get_player_name(active_user_id)
        return [[InlineKeyboardButton(answer_text, switch_inline_query_current_chat='')],
                [InlineKeyboardButton(turn_kb_target.format(active_player),
                            callback_data=f'target#{active_user_id}#')]]
###############################

    # def generate_turn_keyboard(self, players, lobby_id, turn_kb_target):
    #     # TODO: доделать механику вопросов и остановку и обвинения
    #     #  [InlineKeyboardButton(f'{start_text} 🚀', callback_data=f'start#{chat_id}#{chat_name}')]

    #     # ('@username', id)
    #     active_player = bd_unit.get_active_turn_player_name_id(lobby_id)
    #     keyboard = [[InlineKeyboardButton(turn_kb_target.format(active_player[0]),
    #                         callback_data=f'target#{active_player[1]}#{lobby_id}')]]
    #     for player in players:
    #         if player[0] != active_player[1]:
    #             keyboard.append([InlineKeyboardButton( text=f'{player[1]}❓', callback_data=f'ask#{lobby_id}#{player[1]}')])
    #     return keyboard
