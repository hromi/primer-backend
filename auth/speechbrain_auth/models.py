from hashlib import sha256
class Response:
    def __init__(self, similarity, time, login, scrt):
        self.login = login
        self.time = time
        self.similarity = similarity
        self.hash=sha256((login+str(similarity)+scrt).encode('utf-8')).hexdigest()

class Error:
    def __init__(self, message):
        self.message = message
