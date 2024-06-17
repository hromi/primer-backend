import os,time,wave,re
from io import BytesIO
import ffmpeg
import heapq
import numpy as np
#from deepspeech import Model
from speechbrain.pretrained import EncoderClassifier
from glob import glob
from torch.nn import CosineSimilarity
from torch import save,load
from sanic.log import logger
from statistics import median

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


class AuthEngine:
    def __init__(self, temp_dir, token_dir):
        self.temp_dir=temp_dir
        self.token_dir=token_dir
        self.classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir="pretrained_models/spkrec-ecapa-voxceleb")
        self.cos=CosineSimilarity(dim=-1)

#def run(self, audio, scorer="", token="", lang="de",hmpl="",voice="",amount=5):
    def run(self, audio, token, lang="de",threshold="0.4"):
        greeting_dir=self.token_dir+lang+"/"+token+"/"
        logger.debug("LANG"+lang+"TOK"+token+"TD"+greeting_dir)
        f = self.temp_dir+"/anonymous-"+str(time.time())+".wav"
        try:
            audio = normalize_audio(audio,f)
        except Exception as e:
            logger.debug(str(e)) 
        #with wave.Wave_read(/audio) as wav:
        source_wav=self.classifier.load_audio(f)
        source_batch=source_wav.unsqueeze(0)
        emb1=self.classifier.encode_batch(source_batch,None,normalize=True)
        max_sim=0
        login=""
        logger.debug(greeting_dir)
        users = {}
        for target in glob(os.path.join(greeting_dir, '*-*')):
            if re.search(r'wav$',target):
                emb2_file=target.replace("wav","emb")
                if not os.path.isfile(emb2_file):
                    target_wav=self.classifier.load_audio(target)
                    target_batch=target_wav.unsqueeze(0)
                    emb2 = self.classifier.encode_batch(target_batch, None, normalize=True)
                    save(emb2,emb2_file)
            #logger.debug(target)
        #for target in glob(os.path.join(greeting_dir, '*-*.emb')):
            #login=target.replace(greeting_dir,"").split("-")
            #user=re.search("^\w+-\w+",target.replace(greeting_dir,"")).group()
            #target_wav=self.classifier.load_audio(target)
            #target_batch=target_wav.unsqueeze(0)
            #emb2_file=target.replace("wav","emb")
            elif re.search(r'emb$',target):
                if os.path.isfile(target):
                    emb2=load(target)
            else:
                continue
            user=re.search("^\w+-\w+",target.replace(greeting_dir,"")).group()
            #else:
            #    emb2 = self.classifier.encode_batch(target_batch, None, normalize=True)
            #    save(emb2,target.replace("wav","emb"))
            #score = self.classifier.similarity(emb1, emb2)
            score = self.cos(emb1, emb2)[0][0].item()
            if user not in users:
                users[user]=[]
            users[user].append(score)
            #logger.debug(user+" "+str(score))
            #logger.debug(target+" "+str(score))

        for user in users:
            n_neighbors=3;
            n_closest=heapq.nlargest(n_neighbors,users[user]);
            avg_score=sum(n_closest)/len(n_closest);
            #avg_score=sum(users[user])/len(users[user])
            #avg_score=median(users[user])
            logger.debug(user+" "+str(avg_score))
            if avg_score>max_sim and avg_score>float(threshold):
                max_sim=avg_score
                login=user
        return f,max_sim,login


