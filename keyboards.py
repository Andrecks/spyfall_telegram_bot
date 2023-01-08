from telegram import InlineKeyboardButton


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
    
    def generate_turn_keyboard(self, players):
        # TODO: доделать механику вопросов и остановку и обвинения
        #  [InlineKeyboardButton(f'{start_text} 🚀', callback_data=f'start#{chat_id}#{chat_name}')]
        keyboard = []
        for player in players:
            keyboard.append([InlineKeyboardButton(f'{player[1]} ❓', switch_inline_query_current_chat=f'/ask {player[2]}')])
        return keyboard

    