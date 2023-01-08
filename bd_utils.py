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

    def count_players(self, chat_id):
        self.cur.execute(f'select count(*) as cnt from lobbies right join lobby_players on chat_id = {chat_id}')  # noqa
        self.conn.commit()
        return self.cur.fetchone()[0]

    def get_player_list(self, lobby_id):
        self.cur.execute(f'SELECT id FROM players RIGHT JOIN lobby_players on lobby_id = {lobby_id} AND id = player_id')
        self.conn.commit()
        players = self.cur.fetchall()
        result = []
        for p in players:
            result.append(p[0])
        return result

    def get_player_list_id_name_username(self, lobby_id):
        self.cur.execute(f'SELECT id, name, username FROM players RIGHT JOIN lobby_players on lobby_id = {lobby_id} AND id = player_id')
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

    def remove_player_from_lobby(self, user_id, chat_id):
        lobby_id = self.get_lobby_id(chat_id)
        self.cur.execute(f'DELETE FROM lobby_players WHERE player_id ={user_id} AND lobby_id={lobby_id}')
        self.conn.commit()
        return

    def give_roles(self, players, roles: list,
                   lobby_id: int) -> ...:
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

            self.cur.execute(f"UPDATE lobby_players SET role = '{role}', active_turn = {active_turn}\n"
                             f"WHERE player_id = {players[i]} AND lobby_id = {lobby_id};")
            self.conn.commit()
        return

    def set_location(self, lobby_id, location):
        self.cur.execute(f"UPDATE lobbies SET location = '{location}' WHERE id = {lobby_id}")
        self.conn.commit()
        pass


    def start_game(self, chat_id, lang_code):
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

        selected_pack = random.choice(locations)

        locations_file = open('location_packs/locations.json')
        all_locations = json.load(locations_file)
        selected_location = random.randint(0, len(all_locations[f'{selected_pack}_{lang_code}']['locations'])-1)
        location = all_locations[f'{selected_pack}_{lang_code}']['locations'][selected_location]

        players = self.get_player_list(lobby_id)

        self.give_roles(players, location["roles"], lobby_id)
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

    def get_active_turn_player_name(self, lobby_id):
        self.cur.execute(f'SELECT name, id FROM players JOIN lobby_players on id = player_id and active_turn = True and lobby_id = {lobby_id}')
        self.conn.commit()
        return self.cur.fetchone()

    def check_lobby_started(self, lobby_id):
        self.cur.execute(f'SELECT started FROM lobbies WHERE id = {lobby_id}')
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

# boban = workWithBD()
# print(boban.get_player_list_id_name_username(18))