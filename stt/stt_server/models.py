class Response:
    def __init__(self, text, time, score, segments,cer):
        self.text = text
        self.time = time
        self.score = score
        self.segmentation = segments
        self.cer = cer


class Error:
    def __init__(self, message):
        self.message = message
