import time

class GameLoop:
    def __init__(self, game_manager, event_queue):
        self.game = game_manager
        self.queue = event_queue

    def start(self):
        while True:
            self.processEvents()
            time.sleep(0.01)

    def processEvents(self):
        while not self.queue.empty():
            event = self.queue.get()
            self.game.handleEvent(event)