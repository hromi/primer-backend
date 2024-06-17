from math import floor,ceil
from regex import match,sub,split

def process_meta(meta):
    texts=[]
    all_timestamps=[]
    for transcript in meta.transcripts:
        print(len(transcript.tokens))
        if not len(transcript.tokens):
            continue
        print(transcript.tokens[0])
        text=""
        #token=sub(r'[^\p{L} ]','',reference.lower())
        timestamps=[]
        timestamps.append(transcript.tokens[0].start_time)
        for token in transcript.tokens:
            #WE HAVE PHONEME SEGMENT INFORMATION ... THIS IS SO WONDERFUL !!
            #print(token.text+" "+str(token.start_time))
            text=text+token.text
            if token.text==' ':
                timestamps.append(token.start_time)
        timestamps.append(token.start_time+0.1)
        texts.append(text.rstrip())
        all_timestamps.append(timestamps)
        print("RECOGNIZED "+text+" WITH CONFIDENCE "+str(transcript.confidence))
    print("REMOVIN")
    texts=list(filter(len, texts)) #remove empty candidates
    print("BUG")
    #return texts[0]
    return texts,all_timestamps


def check_option_prediction(options,predictions,all_timestamps,scorer_id,reference):
    print("running COP")
    rank=1
    for prediction in predictions:
        prediction=prediction.strip()
        #print("BEFOREPOP"+prediction)
        timestamps=all_timestamps.pop(0)
        #print("AFTERPOP")
        #print(options)
        for option in options:
            option=option.strip()
            print("#",option,"#")
            print("#",prediction,"#")
            print("--")
            #prediction matches the purified reference ?
            if prediction == option:
                segment_id=0
                #segment_json="["
                segment_json=[]
                start=str(floor(timestamps.pop(0)*1000))
                print("AFTERPOP")
                #words=prediction.split(" ")
                if len(options)>1:
                    reference_segments=split(r'([^\p{Letter}]+)', option)
                    print("set reference segments to option")
                else:
                    reference_segments=split(r'([^\p{Letter}]+)', reference)
                    print("set reference segments to reference")
                #reference_segments.pop()
                reference_segments=list(filter(lambda r: r is not ' ', reference_segments))
                reference_segments=list(filter(len,reference_segments))
                print(reference_segments)
                for reference_segment in reference_segments:
                    if match(r'[^\p{Letter}]',reference_segment):
                        reference_segment=reference_segment.strip()
                        segment_json.append({"id":"w_"+scorer_id+"_"+str(segment_id),"w":reference_segment,"start":start,"stop":start})
                    else:
                        print("popping for "+reference_segment)
                        stop=str(floor(timestamps.pop(0)*1000))
                        segment_json.append({"id":"w_"+scorer_id+"_"+str(segment_id),"w":reference_segment,"start":start,"stop":stop})
                        start=stop
                    segment_id+=1
                #segment_json=segment_json[:-1]+']'
                return option,rank,segment_json
    return '',0,[]


