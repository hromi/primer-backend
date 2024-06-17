import os,time,wave
from io import BytesIO

import ffmpeg
import numpy as np
from deepspeech import Model

from sanic.log import logger
def normalize_audio(audio,outfile):
    logger.debug(outfile)
    try:
        out, err = (
            ffmpeg.input("pipe:0")
            .output(
                outfile,
                f="WAV",
                acodec="pcm_s16le",
                ac=1,
                ar="16k",
                loglevel="error",
                hide_banner=None,
            )
            #.run(input=audio, capture_stdout=True, capture_stderr=True)
            .run(input=audio, capture_stdout=True)
            #.run(input=audio)
        )
    except ffmpeg.Error as e:
        logger.debug(e.stdout)
        logger.debug(e.stderr)

    #logger.debug("WTF")
    if err:
        logger.debug(err)
        print(er)
        raise Exception(err)
    return out


class SpeechToTextEngine:
    def __init__(self, model_path, scorer_path,token_dir):
        self.model = Model(model_path)
        self.model.enableExternalScorer(scorer_path)
        self.token_dir=token_dir

    def changeModel(self,model_path):
        self.model=Model(model_path)
 
    def run_from_file(self,f,metadata,amount):
        with wave.Wave_read(f) as wav:
            audio = np.frombuffer(wav.readframes(wav.getnframes()), np.int16)
        #if (scorer):
        #    self.model.enableExternalScorer(scorer)
        try:
            if not metadata:
                result = self.model.stt(audio)
            else:
                result = self.model.sttWithMetadata(audio,amount)
                if not len(result.transcripts):
                    raise Exception("Transcript list empty")
        except BaseException as err:
            print("OH WEYA"+e)
            raise Exception(err)
        return f,result

    #def run(self, audio, scorer="", token="", lang="de",hmpl="",voice="",amount=5):
    def run(self, audio, token="", lang="de",hmpl="",voice="",amount=5):
        print("RUN "+hmpl)
        if (hmpl):
            if not os.path.isdir(hmpl):
               from pathlib import Path
               Path(hmpl).mkdir(parents=True, exist_ok=True)
            f = hmpl+token+"-"+str(time.time())+".wav"
        else:
            #token_dir=self.token_dir+lang+"/"+token
            token_dir=self.token_dir+lang+"/TEMP"
            logger.debug("LANG"+lang+"TOK"+token+"TD"+token_dir)
            if not os.path.isdir(token_dir):
               from pathlib import Path
               Path(token_dir).mkdir(parents=True, exist_ok=True)
            f = token_dir+"/"+voice+"-"+str(time.time())+".wav"
        try:
            audio = normalize_audio(audio,f)
        except Exception as e:
            logger.debug(str(e)) 
        #with wave.Wave_read(/audio) as wav:
        return self.run_from_file(f,True,amount)

