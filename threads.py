import threading
import time 

def print_smth(lobby_id, chat_id, lang_code):
    print(f'lobby id is {lobby_id}, chat_id is {chat_id}, lang_code is {lang_code}')

class MyThread(threading.Thread):
    def __init__(self, threadID, name, counter, function_name, lobby_id, chat_id, lang_code, user_id):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
        self.function_name = function_name
        self.lobby_id = lobby_id
        self.chat_id = chat_id
        self.lang_code = lang_code
        self.user_id = user_id

    def run(self):
        print(f'starting {self.name}')
        threadLock.acquire()
        self.print_time(self.counter)
        threadLock.release()
        self.function_name(self.lobby_id, self.chat_id, self.lang_code, self.user_id)

    def print_time(self, counter):
        while counter:
            time.sleep(1)
            # print(counter)
            counter -= 1


class AnotherThread(threading.Thread):
    def __init__(self, counter, function_name, vote_id_to_end):
        threading.Thread.__init__(self)
        self.counter = counter
        self.function_name = function_name
        self.vote_id = vote_id_to_end

    def run(self):
        print(f'starting {self.name}')
        threadLock.acquire()
        self.print_time(self.counter)
        threadLock.release()
        self.function_name(self.vote_id)

    def print_time(self, counter):
        while counter:
            time.sleep(1)
            # print(counter)
            counter -= 1

threadLock = threading.Lock()
# threads = []

# thread1 = MyThread(1, "Thread-1", 10, print_smth, 12, 1488, 'ru')

# thread1.start()

# threads.append(thread1)