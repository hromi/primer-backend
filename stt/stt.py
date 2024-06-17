import json,os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from datetime import date
from pyhocon import ConfigFactory
from sanic import Sanic, response
from sanic.log import logger
#import deepspeech
from stt_server.engine import SpeechToTextEngine
from stt_server.models import Response, Error
from os.path import exists
from regex import match,sub,split,UNICODE
import subprocess
from hashlib import sha256
from math import floor,ceil
import jiwer

# Load app configs and initialize STT model
conf = ConfigFactory.parse_file("/home/user/application.conf")
model_path=conf["stt.model_dir"]+conf["stt.default_lang"]+'/'+conf["stt.model_file"]

PREDICTION_AMOUNT=conf["stt.prediction_amount"]
MAX_CER=conf["stt.max_cer"]

engine = SpeechToTextEngine(
    model_path=model_path,
    scorer_path=Path(conf["stt.default_scorer"]).absolute().as_posix(),
    token_dir=conf["stt.token_dir"]
)


#RESETTING STALE VOICE MODEL INFO
f_old=open('/tmp/old_voice','w')
f_old.write("")
f_old.close()

f_oldlang=open('/tmp/old_lang','w')
f_oldlang.write("")
f_oldlang.close()

f_oldscorer=open('/tmp/old_scorer','w')
f_oldscorer.write("")
f_oldlang.close()

learner_dir=conf["hmpl.data_dir"]

# Initialze Sanic and ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=conf["server.threadpool.count"])
app = Sanic("stt_server")

#with this setting it somehow works...with others, it is tricky
app.config.WEBSOCKET_MAX_SIZE = 2 ** 21

def reloader(language,voice="",scorer="",alpha="0.77"):

    f_old=open('/tmp/old_voice','r')
    old_voice=f_old.read()
    f_old.close()

    f_oldlang=open('/tmp/old_lang','r')
    old_lang=f_oldlang.read()
    f_oldlang.close()

    f_oldscorer=open('/tmp/old_scorer','r')
    old_scorer=f_oldscorer.read()
    f_oldscorer.close()

    learner_dir=conf["hmpl.data_dir"]+'/'+voice+'/'+language
    #NEW USER or LANGUAGE APPEARS ON SCENE
    if old_voice != voice or old_lang != language:
        logger.debug("OLD"+old_lang+"::"+old_voice+"NEW"+language+"::"+voice)
        #logger.debug("LANGDIR"+learner_dir)
        new_model=learner_dir+conf["stt.model_file"]
        if exists(new_model):
            logger.debug(new_model+" FOUND, USING IT")
            engine.changeModel(new_model)
        else:
            model_path=conf["stt.model_dir"]+language+conf["stt.model_file"]
            logger.debug(new_model+" NOT FOUND,SWITCHING TO "+model_path)
            engine.changeModel(model_path)
 
        f_old=open('/tmp/old_voice','w')
        f_old.write(voice)
        f_old.close()
 
        f_oldlang=open('/tmp/old_lang','w')
        f_oldlang.write(language)
        f_oldlang.close()

    if old_scorer!=scorer:
        scorer_file=conf["stt.scorer_dir"]+scorer+".scorer"
        if not exists(scorer_file):
            logger.debug(scorer_file+" does not exist");
            if match("^\d+$",scorer):
                logger.debug("scorer id numeric. executing"+conf["utils.scorer_creator"])
                subprocess.run([conf["utils.scorer_creator"],scorer,language,alpha])
        logger.debug("changing scorer")
        engine.model.enableExternalScorer(scorer_file)
        f_oldscorer=open('/tmp/old_scorer','w')
        f_oldscorer.write(scorer)
        f_oldscorer.close()

    return learner_dir


@app.route("/update_model", methods=["GET"])
async def update_model(request):
    f_old=open('/tmp/old_voice','r')
    old_voice=f_old.read()
    f_old.close()
    voice = request.args.get("voice")
    language = request.args.get("lang")
    logger.debug("updatin model"+voice+" "+old_voice)
    if voice == old_voice:
        new_model=conf["hmpl.data_dir"]+'/'+voice+'/'+language+'/'+conf["stt.model_file"]
        if exists(new_model):
            logger.debug(new_model+" UPDATED MODEL FOUND, USING IT")
            engine.changeModel(new_model)
    return response.text("model updated")

@app.route("/", methods=["GET"])
async def healthcheck(_):
    return response.text("welcome to lesen-mikroserver")


@app.websocket("/hmpl/<scorer>/<reference>/<voice>/<language>/<phase>/<feedback>")
async def hmpl(request, ws, scorer, reference, voice, language, phase, feedback):

    token=sub(r'[^\p{L} ]', '', reference, flags=UNICODE).lower()

    #token=reference.lower()
    #scorer="22078"
    #logger.debug(voice+" "+token+" PHASE "+phase)

    d=date.today()-date(2022,9,13)
    iteration=str(d.days)

    learner_dir=reloader(language,voice,scorer)
    logger.debug(f"Received {request.method} request at {request.path}")
    try:
        #print("PREAUDIO")
        audio = await ws.recv()
        #print("POSTAUDIO")
        #print(len(audio))
        inference_start = perf_counter()
        data_dir=learner_dir+'/'+phase+'/'
        #logger.debug("RUNNIN")
        f,meta = await app.loop.run_in_executor(executor, lambda: engine.run(audio,token,language,data_dir,voice,PREDICTION_AMOUNT))
        #logger.debug("PREMETA")
        predictions,timestamps=process_meta(meta)
        #logger.debug("POSTMETA")
        #we are recognizing unknown stuff here
        text,score,segments,cer=check_option_prediction([token],predictions,timestamps,scorer,reference)
        if phase=="0":
            score=0

        inference_end = perf_counter() - inference_start
        await ws.send(json.dumps(Response(text, inference_end,score,segments).__dict__,ensure_ascii=False))
        logger.debug(f"Completed {request.method} request at {request.path} in {inference_end} seconds")
        
        #feedback_prefix='feedback_' if feedback=='ON' else ''
        
        if token==text:
          #csv=open(data_dir+feedback_prefix+'same.'+iteration+'.csv','a')
          csv=open(data_dir+'same.'+iteration+'.csv','a')
        else:
          #csv=open(data_dir+feedback_prefix+'different.'+iteration+'.csv','a')
          csv=open(data_dir+'different.'+iteration+'.csv','a')

        #all_file=data_dir+feedback_prefix+'all.'+iteration+'.csv'
        all_file=data_dir+'all.'+iteration+'.csv'

        if not exists(all_file):
          csv_all=open(all_file,'w')
          csv_all.write('"wav_filename","wav_filesize","transcript","prediction"\n')
        else:
          csv_all=open(all_file,'a')
          csv_all.write('"'+f+'",'+str(os.stat(f).st_size)+',"'+token+'","'+text+'","'+feedback+'"\n')
        csv.write('"'+f+'",'+str(os.stat(f).st_size)+',"'+token+'","'+text+'","'+feedback+'"\n')
        csv.close()
    except Exception as e:  # pylint: disable=broad-except
        logger.debug(f"Failed to process {request.method} request at {request.path}. The exception is: {str(e)}.")
        await ws.send(json.dumps(Error("Something went wrong").__dict__))
    await ws.close()

def process_meta(meta):
    texts=[]
    all_timestamps=[]
    for transcript in meta.transcripts:
        #logger.debug(len(transcript.tokens))
        if not len(transcript.tokens):
            continue
        #logger.debug(transcript.tokens[0])
        text=""
        timestamps=[]
        timestamps.append(transcript.tokens[0].start_time)
        for token in transcript.tokens:
            #WE HAVE PHONEME SEGMENT INFORMATION ... THIS IS SO WONDERFUL !!
            #logger.debug(token.text+" "+str(token.start_time))
            text=text+token.text
            if token.text==' ':
                timestamps.append(token.start_time)
        timestamps.append(token.start_time+0.1)
        texts.append(text.rstrip())
        all_timestamps.append(timestamps)
        #logger.debug("RECOGNIZED "+text+" WITH CONFIDENCE "+str(transcript.confidence))
    #logger.debug("REMOVIN")
    texts=list(filter(len, texts)) #remove empty candidates
    #logger.debug("BUG")
    #return texts[0]
    return texts,all_timestamps

def check_option_prediction(options,predictions,all_timestamps,scorer_id,reference):
    logger.debug("running COP"+reference+"REF")
    rank=0
    for prediction in predictions:
        prediction=sub(r'\s+$','',prediction)
        prediction=sub(r'^\s+','',prediction)
        #logger.debug("BEFOREPOP"+prediction+"WTF")
        timestamps=all_timestamps.pop(0)
        #logger.debug("OPTIONS")
        #logger.debug(options)
        words=prediction.split(" ")
        n_words=len(words)
        for option in options:
            option=option.strip()
            option_tokens=len(option.split(' '))
           
            if option_tokens != n_words:
                continue

            #prediction matches the purified reference ?
            cer=jiwer.cer(option,prediction)
            print("#",option,"#",'\n',"#",prediction,"#",'\n\n')
            print("CER",cer)
            if prediction == option or cer < MAX_CER:
                segment_id=0
                #segment_json="["
                segment_json=[]
                start=str(floor(timestamps.pop(0)*1000))
                #logger.debug("AFTERPOP")
                #words=prediction.split(" ")
                if len(options)>1:
                    reference_segments=split(r'([^\p{Letter}]+)', option)
                    #logger.debug("set reference segments to option")
                else:
                    reference_segments=split(r'([^\p{Letter}]+)', reference)
                    #logger.debug("set reference segments to reference")
                #reference_segments.pop()
                reference_segments = [s for s in reference_segments if s.strip()]
                logger.debug(reference_segments)
                reference_segments=list(filter(len, reference_segments))
                for reference_segment in reference_segments:
                    if match(r'[^\p{Letter}]',reference_segment):
                        segment_json.append({"id":"w_"+scorer_id+"_"+str(segment_id),"w":reference_segment,"start":start,"stop":start})
                    else:
                        logger.debug("popping for "+reference_segment)
                        try:
                            stop=str(floor(timestamps.pop(0)*1000))
                        except:
                            logger.debug("POP LIST EMPTY")
                            return option,rank2score(rank),segment_json
                        segment_json.append({"id":"w_"+scorer_id+"_"+str(segment_id),"w":reference_segment,"start":start,"stop":stop})
                        start=stop
                    segment_id+=1
                #segment_json=segment_json[:-1]+']'
                #print(segment_json)
                return option,rank2score(rank),segment_json,cer
        rank=rank+1
    return '',0,[],None


def rank2score(rank):
    return PREDICTION_AMOUNT-rank

@app.websocket("/stt/<scorer>/<reference>/<voice>/<language>/<lm_alpha>")
async def stt(request, ws, scorer, reference, voice, language, lm_alpha):
    learner_dir=reloader(language,voice,scorer,lm_alpha)
    token=reference
    #options=sub(r' +',' ',sub(r'[^\p{Letter}§ ]','',token.lower())).split('§')
    options=sub(r' +',' ',sub(r'[^\p{L}§ ]','',sub(r"['’]"," ",token.lower()))).split('§')
    #options=token.lower()
    #options=[token.lower()]
    logger.debug(options)
    logger.debug(f"Received {request.method} request at {request.path}")
    score=0
    try:
        logger.debug("AWAITIN AUDIO")
        audio = await ws.recv()
        print(f"Received audio data: {len(audio)} bytes")
        inference_start = perf_counter()
        logger.debug("TRYING")
        try:
            #f,meta = await app.loop.run_in_executor(executor, lambda: engine.run(audio,scorer_file,token,language,"",voice,PREDICTION_AMOUNT))
            f,meta = await app.loop.run_in_executor(executor, lambda: engine.run(audio,token,language,"",voice,PREDICTION_AMOUNT))
            logger.debug("PROCESSMETA")
            predictions,timestamps=process_meta(meta)
            #emtpy reference indicates no-hypothesis STT, return most plausible prediction
            if reference is '0':
                text=predictions[0]
                segment_json="[]"
                rank=0
            else:
                text,score,segment_json,cer=check_option_prediction(options,predictions,timestamps,scorer,reference)
        except Exception as e:
            logger.debug(str(e))
        #text = await app.loop.run_in_executor(executor, lambda: engine.run(audio))
        inference_end = perf_counter() - inference_start
        await ws.send(json.dumps(Response(text, inference_end,score,segment_json,cer).__dict__,ensure_ascii=False))
        logger.debug(f"Completed {request.method} request at {request.path} in {inference_end} seconds")
        logger.debug([f,text])
        f_base=os.path.basename(f)
        if text:
            if len(text)>200:
                filename=sha256(text.encode('utf-8')).hexdigest()
            else:
                filename=text
            token_dir=conf["stt.token_dir"]+language+"/"+filename+"/"
            if not os.path.isdir(token_dir):
               Path(token_dir).mkdir(parents=True, exist_ok=True)
            new_f=token_dir+f_base
            csv_all=open("/data/recite/all.csv",'a')
            csv_all.write('"'+new_f+'",'+str(os.stat(f).st_size)+',"'+filename+'","'+reference+'"\n')
            csv_all.close()
            os.replace(f,new_f)
            logger.debug("Storing into "+new_f)
        else:
            #if len(token)>23:
            #    token=sha256(token.encode('utf-8')).hexdigest()
            #token_dir=conf["stt.token_dir"]+language+"/UNKNOWN/"+token+"-"
            #new_f=token_dir+f_base
            logger.debug("Removing "+f)
            os.remove(f)

    except Exception as e:  # pylint: disable=broad-except
        logger.debug(f"Failed to process {request.method} request at {request.path}. The exception is: {str(e)}.")
        await ws.send(json.dumps(Error("Something went wrong").__dict__))
    await ws.close()


if __name__ == "__main__":
    app.run(
        host=conf["server.http.host"],
        port=conf["server.http.port"],
        ssl=dict(
            cert=conf["server.http.cert_path"],
            key=conf["server.http.key_path"]
        ),
        access_log=True,
        debug=True,
    )
