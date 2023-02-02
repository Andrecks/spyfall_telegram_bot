import psycopg2
import os
import json
import random


class workWithBD:
    # подключение к базе
    conn = psycopg2.connect(database=os.getenv('db'), user=os.getenv('dbuser'),
                            password=os.getenv('dbpass'), host=os.getenv('host'), port=os.getenv('dbport'))  # noqa
    # определение переменной для работы с запросами бд
    cur = conn.cursor()


    def get_lobby_id(self, chat_id):
        self.cur.execute(f'SELECT id FROM lobbies WHERE chat_id = {chat_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def check_lobby_exists(self, chat_id):
        self.cur.execute(f'SELECT * FROM lobbies WHERE chat_id = {chat_id}')
        self.conn.commit()
        return self.cur.fetchone()

    def check_player_exists(self, user_id):
        self.cur.execute(f'SELECT * FROM players WHERE id = {user_id}')
        self.conn.commit()
        return self.cur.fetchone()

    def create_new_lobby(self, chat_id, *args):
        params = list(args)
        if len(params) > 0:
            self.cur.execute(f"INSERT INTO lobbies (chat_id, language) VALUES({chat_id}, '{params[0]}')") # noqa
            self.conn.commit()
            return params[0]
        # default language is set to ru
        self.cur.execute(f"INSERT INTO lobbies (chat_id, language) VALUES({chat_id}, 'ru')") # noqa
        self.conn.commit()
        return 'ru'

    def insert_player(self, user_id, name, username):
        self.cur.execute(f"INSERT INTO players VALUES({user_id}, '{name}', '{username}')")
        self.conn.commit()

    def count_players(self, lobby_id):
        self.cur.execute(f'select count(*) from lobby_players where lobby_id = {lobby_id}')  # noqa
        self.conn.commit()
        return self.cur.fetchone()[0]

    def get_player_list(self, lobby_id):
        self.cur.execute(f'SELECT id FROM players JOIN lobby_players on lobby_id = {lobby_id} AND id = player_id')
        self.conn.commit()
        players = self.cur.fetchall()
        result = []
        for p in players:
            result.append(p[0])
        return result

    def get_player_list_id_name_username(self, lobby_id):
        self.cur.execute(f'SELECT id, name, username FROM players JOIN lobby_players on lobby_id = {lobby_id} AND id = player_id')
        self.conn.commit()
        players = self.cur.fetchall()
        result = []
        for p in players:
            result.append([p[0], p[1], p[2]])
        return result

    def add_player_to_lobby(self, user_id, chat_id):
        lobby_id = self.get_lobby_id(chat_id)
        self.cur.execute(f'INSERT INTO lobby_players VALUES ({user_id}, {lobby_id})')
        self.conn.commit()
        return

    def get_lobby_language(self, chat_id):
        self.cur.execute(f'SELECT language FROM lobbies WHERE chat_id={chat_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def get_lobby_language_from_lobby_id(self, lobby_id):
        self.cur.execute(f'SELECT language FROM lobbies WHERE id={lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def remove_player_from_lobby(self, user_id, chat_id):
        lobby_id = self.get_lobby_id(chat_id)
        self.cur.execute(f'DELETE FROM lobby_players WHERE player_id ={user_id} AND lobby_id={lobby_id}')
        self.conn.commit()
        return

    def give_roles(self, players, roles: list,
                   lobby_id: int, spy_role: str) -> ...:
        player_count = len(players)

        SPY = random.randint(0, player_count - 1)
        FIRST = random.randint(0, player_count - 1)

        given_roles = []
        done = False
        while done is not True:
            random_role_id = random.randint(0, 6)
            if random_role_id not in given_roles:
                given_roles.append(random_role_id)
            if len(given_roles) == player_count:
                done = True
        for i in range(0, player_count):
            if i != SPY:
                role = roles[i]
            else:
                role = "Шпион"

            if i != FIRST:
                active_turn = False
            else:
                active_turn = True
            self.cur.execute(f"UPDATE lobby_players SET role = '{role}', active_turn = {active_turn}, lobby_id = {lobby_id}\n"
                             f"WHERE player_id = {players[i]};")
            self.conn.commit()
        return

    def set_location(self, lobby_id, location):
        self.cur.execute(f"UPDATE lobbies SET location = '{location}' WHERE id = {lobby_id}")
        self.conn.commit()
        pass


    def start_game(self, chat_id, lang_code, spy_role):
        lobby_id = self.get_lobby_id(chat_id)

        # changing column status in table lobbies
        self.cur.execute(f'UPDATE lobbies SET started=True WHERE chat_id = {chat_id}')
        self.conn.commit()

        # get random location from the list
        self.cur.execute(f'SELECT location_packs FROM lobbies WHERE chat_id = {chat_id}')
        self.conn.commit()
        locations = self.cur.fetchone()[0].split('@')
        while("" in locations):
            locations.remove("")

        lang_code = self.get_lobby_language(chat_id)

        selected_pack = random.choice(locations)

        locations_file = open(f'location_packs/locations_{lang_code}.json')
        all_locations = json.load(locations_file)
        selected_location = random.randint(0, len(all_locations[selected_pack]['locations'])-1)
        location = all_locations[selected_pack]['locations'][selected_location]

        players = self.get_player_list(lobby_id)

        self.give_roles(players, location["roles"], lobby_id, spy_role)
        self.set_location(lobby_id, location['name'])

        #TODO: старт игры: поменять статус лобби



    def get_player_role(self, lobby_id, player_id) -> str:
        self.cur.execute(f'SELECT role FROM lobby_players WHERE lobby_id = {lobby_id} AND player_id = {player_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def get_player_name(self, player_id):
        self.cur.execute(f'SELECT name FROM players WHERE id = {player_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def get_player_username(self, player_id):
        self.cur.execute(f'SELECT username FROM players WHERE id = {player_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def get_lobby_location(self, chat_id):
        self.cur.execute(f'SELECT location FROM lobbies WHERE chat_id = {chat_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def check_player_active(self, user_id):
        self.cur.execute(f'SELECT active_turn FROM lobby_players WHERE player_id = {user_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def check_lobby_started(self, lobby_id):
        self.cur.execute(f'SELECT started FROM lobbies WHERE id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def check_lobby_paused(self, lobby_id):
        self.cur.execute(f'SELECT paused FROM lobbies WHERE id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def update_name_username(self, user_id, username, name):
        self.cur.execute(f"UPDATE players SET name = '{name}', username = '{username}' WHERE id = {user_id}")
        self.conn.commit()
        return 

    def update_chat_id(self, old_id, new_id):
        self.cur.execute(f'UPDATE lobbies SET chat_id = {new_id} WHERE chat_id = {old_id}')
        self.conn.commit()
        return

    def get_active_lobbies_chat_ids(self):
        self.cur.execute(f'SELECT chat_id FROM lobbies WHERE started = True AND paused = False')
        self.conn.commit()
        return self.cur.fetchall()[0]

    def get_active_turn_player_name_id_username(self, lobby_id):
        self.cur.execute(f'SELECT name, id, username FROM lobby_players JOIN players ON player_id = id WHERE active_turn = True AND lobby_id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()

    def get_active_answer_player_name_id_username(self, lobby_id):
        self.cur.execute(f'SELECT name, id, username FROM lobby_players JOIN players ON player_id = id WHERE active_answer = True AND lobby_id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()

    def set_player_active_turn(self, user_id, x):
        self.cur.execute(f'UPDATE lobby_players SET active_turn = {x} WHERE player_id = {user_id}')
        self.conn.commit()

    def set_player_active_answer(self, user_id, x):
        self.cur.execute(f'UPDATE lobby_players SET active_answer = {x} WHERE player_id = {user_id}')
        self.conn.commit()

    def get_lobby_id_from_user(self, user_id):
        self.cur.execute(f'SELECT lobby_id FROM lobby_players WHERE player_id = {user_id}')
        self.conn.commit()
        if self.cur.fetchone is None:
            return False
        return self.cur.fetchone()[0]

    def get_target_id_from_username(self, username):
        self.cur.execute(f"SELECT id FROM players WHERE username = '{username}'")
        self.conn.commit()
        return self.cur.fetchone()[0]

    def get_chat_id_from_lobby_id(self, lobby_id):
        self.cur.execute(f'SELECT chat_id FROM lobbies WHERE id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def check_name_username_correct(self, user_id, username, name):
        self.cur.execute(f'SELECT username, name FROM players WHERE id = {user_id}')
        self.conn.commit()
        username_name = self.cur.fetchone()
        if username_name[0] != username or username_name[1] != name:
            self.update_username_name(user_id, username, name)
            print(f'updated username and name of user_id {user_id}')
            print(f'{username_name[1]} -> {name}')
            print(f'{username_name[0]} -> {username}')
        else:
            print(f'name and username correct ({user_id} {username} {name})')

    def update_username_name(self, user_id, username, name):
        self.cur.execute(f"UPDATE players SET name = '{name}', username = '{username}' WHERE id = {user_id}")
        self.conn.commit()
        return

    def check_user_active_answer(self, user_id):
        self.cur.execute(f'SELECT active_answer FROM lobby_players WHERE player_id = {user_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def set_who_asked(self, target_id, user_id):
        self.cur.execute(f'UPDATE lobby_players SET who_asked = {user_id} WHERE player_id = {target_id}')
        self.conn.commit()
        return

    def get_who_asked(self, user_id):
        self.cur.execute(f'SELECT who_asked FROM lobby_players WHERE player_id = {user_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def check_user_id_spy(self, user_id, spy_role):
        self.cur.execute(f"SELECT role FROM lobby_players WHERE player_id = {user_id}")
        self.conn.commit()
        if self.cur.fetchone()[0] == spy_role:
            return True
        return False

    def get_lobby_location_packs(self, lobby_id):
        self.cur.execute(f'SELECT location_packs FROM lobbies WHERE id = {lobby_id}')
        self.conn.commit()
        return [x for x in self.cur.fetchone()[0].split('@') if x != '']

    def set_lobby_paused(self, lobby_id, x):
        self.cur.execute(f'UPDATE lobbies SET paused = {x} WHERE id = {lobby_id}')
        self.conn.commit()
        return

    def get_lobby_location_from_lobby_id(self, lobby_id):
        self.cur.execute(f'SELECT location FROM lobbies WHERE id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def add_score_user(self, user_id, x):
        self.cur.execute(f'UPDATE players SET score = score + {x} WHERE id = {user_id}')
        self.conn.commit()
        return

    def check_user_not_in_another_lobby(self, user_id, cur_lobby):
        self.cur.execute(f'SELECT lobby_id FROM lobby_players WHERE player_id = {user_id}')
        self.conn.commit()
        user_lobby = self.cur.fetchone()
        if user_lobby is None:
            return False
        elif user_lobby != cur_lobby:
                return user_lobby
        return False

    def get_chat_name_from_lobby_id(self, lobby_id):
        self.cur.execute(f'SELECT chat_name FROM lobbies WHERE id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def check_and_update_chat_name(self, chat_id, chat_name):
        self.cur.execute(f'SELECT chat_name FROM lobbies WHERE chat_id = {chat_id}')
        self.conn.commit()
        old_name = self.cur.fetchone()[0]
        if old_name != chat_name:
            self.cur.execute(f"UPDATE lobbies SET chat_name = {chat_name} WHERE chat_id = {chat_id}")
            return
        print(f'✅ {chat_name} == {old_name} ✅')
        return

    def get_vote_time_from_lobby_id(self, lobby_id):
        self.cur.execute(f'SELECT vote_time FROM lobbies WHERE id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def check_vote_started(self, lobby_id):
        self.cur.execute(f'SELECT * FROM spy_votes WHERE lobby_id = {lobby_id}')
        self.conn.commit()
        return(self.cur.fetchone())

    def start_new_vote(self, lobby_id, user_id, chosen_player_id):
        self.cur.execute(f"INSERT INTO spy_votes (lobby_id, player_id, target_id, paused_game, yes_no) VALUES ({lobby_id}, {user_id}, {chosen_player_id}, True, 'yes')")
        self.conn.commit()
        return

    def get_votes_count(self, lobby_id):
        self.cur.execute(f'SELECT COUNT(*) FROM spy_votes WHERE lobby_id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def players_still_not_voted(self, lobby_id, target_id):
        self.cur.execute(f'SELECT player_id FROM spy_votes WHERE lobby_id = {lobby_id}')
        self.conn.commit()
        voted_ids = [x[0] for x in self.cur.fetchall()]

        self.cur.execute(f'SELECT player_id FROM lobby_players WHERE lobby_id = {lobby_id} AND player_id != {target_id}')
        self.conn.commit()
        all_ids = [x[0] for x in self.cur.fetchall()]

        not_voted_ids = []
        for id in all_ids:
            if id not in voted_ids:
                not_voted_ids.append([self.get_player_username(id), id])

        return not_voted_ids

    def get_vote_id(self, user_id, lobby_id):
        self.cur.execute(f'SELECT id FROM spy_votes WHERE player_id = {user_id} AND lobby_id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def check_vote_not_ended(self, vote_id):
        self.cur.execute(f'SELECT lobby_id FROM spy_votes WHERE id = {vote_id}')
        self.conn.commit()
        lobby_id_or_None = self.cur.fetchone()
        if lobby_id_or_None is not None:
            print(f'lobby_id_or_none = {lobby_id_or_None}')
            lobby_id = lobby_id_or_None[0]

            chat_id = self.get_chat_id_from_lobby_id(lobby_id)
            lang_code = self.get_lobby_language(chat_id)
            active_player = self.get_active_answer_player_name_id_username(lobby_id)
            if active_player is not None:
                turn = 'answer'
            else:
                active_player = self.get_active_turn_player_name_id_username(lobby_id)
                turn = 'turn'
            print(f'active_player is {active_player}')
            return_list = [lobby_id, chat_id, lang_code, active_player, turn]

            self.cur.execute(f'DELETE FROM spy_votes WHERE lobby_id = {lobby_id}')
            self.conn.commit()
            return return_list

        return False

    def check_player_in_current_lobby(self, user_id, lobby_id):
        self.cur.execute(f'SELECT * FROM lobby_players WHERE lobby_id = {lobby_id} AND player_id = {user_id}')
        self.conn.commit()
        if self.cur.fetchone() is not None:
            return True
        return False

    def add_vote(self, lobby_id, user_id, target_id, yes_no):
        self.cur.execute(f"INSERT INTO spy_votes (lobby_id, player_id, target_id, paused_game, yes_no) VALUES ({lobby_id}, {user_id}, {target_id}, False, '{yes_no}')")
        self.conn.commit()
        return

    def get_started_vote_player_id_name(self, lobby_id):
        id_name = []
        self.cur.execute(f'SELECT player_id FROM spy_votes WHERE lobby_id = {lobby_id} and paused_game = {True}')
        self.conn.commit()
        id_name.append(self.cur.fetchone()[0])
        self.cur.execute(f'SELECT name FROM players WHERE id = {id_name[0]}')
        self.conn.commit()
        id_name.append(self.cur.fetchone()[0])
        return id_name

    def player_already_voted(self, user_id, lobby_id):
        self.cur.execute(f'SELECT * FROM spy_votes WHERE lobby_id = {lobby_id} AND player_id = {user_id}')
        self.conn.commit()
        if self.cur.fetchone() is not None:
            return True
        return False

    def set_lobby_started(self, lobby_id, x):
        self.cur.execute(f'UPDATE lobbies SET started = {x} WHERE id = {lobby_id}')
        self.conn.commit()
        return

    def check_all_voted_yes(self, lobby_id, player_count):
        self.cur.execute(f"SELECT COUNT (*) FROM spy_votes WHERE lobby_id = {lobby_id} and yes_no = 'yes'")
        self.conn.commit()
        if self.cur.fetchone()[0] == player_count:
            return True
        return False

    def check_target_is_spy(self, lobby_id, target_id, spy_role):
        self.cur.execute(f"SELECT role FROM lobby_players WHERE player_id = {target_id} AND lobby_id = {lobby_id}")
        self.conn.commit()
        if self.cur.fetchone()[0] == spy_role:
            return True
        return False

    def remove_vote_lobby_id(self, lobby_id):
        self.cur.execute(f'DELETE FROM spy_votes WHERE lobby_id = {lobby_id}')
        self.conn.commit()
        return

    def get_spy_name_id(self, spy_role):
        self.cur.execute(f"SELECT name, id FROM players JOIN lobby_players ON id = Player_id AND role = '{spy_role}'")
        self.conn.commit()
        return self.cur.fetchone()

    def get_target_name_id(self, target_id):
        self.cur.execute(f'SELECT name, id FROM players WHERE id = {target_id}')
        self.conn.commit()
        return self.cur.fetchone()

    def get_started_vote_name_id(self, lobby_id):
        self.cur.execute(f'SELECT name, players.id FROM players JOIN spy_votes ON players.id = player_id AND paused_game = True AND lobby_id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()

    def get_vote_id_from_user_id(self, user_id):
        self.cur.execute(f'SELECT id FROM spy_votes WHERE player_id = {user_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def set_chat_name(self, chat_id, chat_name):
        self.cur.execute(f"UPDATE lobbies SET chat_name = '{chat_name}' WHERE chat_id = {chat_id}")
        self.conn.commit()
        return

    def remove_players_from_lobby(self, lobby_id):
        self.cur.execute(f'DELETE FROM lobby_players WHERE lobby_id = {lobby_id}')
        self.conn.commit()
        return

    def save_question_for_user(self, question, player_id):
        self.cur.execute(f"UPDATE lobby_players SET question = '{question}' WHERE player_id = {player_id}")
        self.conn.commit()
        return

    def get_asker_name(self, user_id):
        self.cur.execute(f'SELECT who_asked FROM lobby_players WHERE player_id = {user_id}')
        self.conn.commit()
        asker_id = self.cur.fetchone()[0]

        self.cur.execute(f'SELECT name FROM players WHERE id = {asker_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]

    def get_question_asked(self, user_id):
        self.cur.execute(f'SELECT question FROM lobby_players WHERE player_id = {user_id}')
        self.conn.commit()
        return self.cur.fetchone()[0]
        # print(f'not_voted_usernames = {not_voted_ids}')
    # def get_spy_id(self, lobby_id, spy_role):
    #     self.cur.execute(f"SELECT player_id FROM lobby_players WHERE role = '{spy_role}' AND lobby_id = {lobby_id}")
    #     self.conn.commit()
    #     return self.cur.fetchone()[0]

# boban = workWithBD()
# print(boban.get_lobby_location_packs(18))