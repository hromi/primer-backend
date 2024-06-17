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
#import chromadb

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
            .run(input=audio, capture_stdout=True)
        )
    except ffmpeg.Error as e:
        logger.debug(e.stdout)
        logger.debug(e.stderr)

    if err:
        logger.debug(err)
        print(er)
        raise Exception(err)
    return out


class AuthEngine:
    def __init__(self, chroma_collection, conf):
        self.temp_dir=conf["temp_dir"]
        self.token_dir=conf["token_dir"]
        self.auth_threshold=conf["auth_threshold"]
        self.save_threshold=conf["save_threshold"]
        self.n_results=conf["n_results"]
        self.classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")
        self.collection=chroma_collection

    def run(self, audio, token, device="primer"):
        greeting_dir=self.token_dir+token+"/"
        when=str(time.time())
        f = self.temp_dir+"/"+device+"-"+when+".wav"
        print(f)
        try:
            audio = normalize_audio(audio,f)
        except Exception as e:
            logger.debug(str(e)) 
        print("NORMALIZED"+f)
        source_wav=self.classifier.load_audio(f)
        source_batch=source_wav.unsqueeze(0)

        embeddings=self.classifier.encode_batch(source_batch,None,normalize=True).flatten().tolist()
        results=self.collection.query(embeddings,n_results=self.n_results)
        ids=results['ids'][0]
        
        max_sim=0
        login=""
        users = {}
        i=0
        logins=results['metadatas'][0]
        print(results)
        ids=results['ids'][0]
        print(ids)
        for d in results['distances'][0]:
            user=logins[i]['login']
            uid=ids[i]
            if user not in users:
                users[user]=[]
            #chroma returns opposite of cosine, reverting it back
            users[user].append(1-d)
            logger.debug(user+" "+str(1-d))
            i=i+1

        for user in users:
            avg_score=sum(users[user])/len(users[user])
            avg_score=median(users[user])
            logger.debug(user+" "+str(avg_score))
            if avg_score>max_sim and avg_score>float(self.auth_threshold):
                max_sim=avg_score
                login=user

	#accept if fully unambigous or avg_score higher than big threshold
        if max_sim>self.save_threshold or (login in users and len(users[login])==self.n_results):
            self.collection.add(ids=[when],metadatas=[{'device':device,'login':login,'autoadd':True,'when':when,'file':f}],embeddings=[embeddings])
            logger.debug(f"{login}'s greeting added into collection with id {when}")
        else:
            try:
                self.collection.delete(where={"login":"last"})
                self.collection.add(ids=[when],metadatas=[{'login':"last",'when':when,'device':device,'file':f}],embeddings=[embeddings])
                logger.debug(f"{when} added into collection with login last")
            except Exception as e:
                logger.debug(e)
            link=greeting_dir+'/last'
            try:
                os.unlink(link)
            except:
                1
            os.symlink(f,link)
            logger.debug("symlink created")
        return f,max_sim,login


