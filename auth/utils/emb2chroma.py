import os,re
import chromadb
users = {}
client = chromadb.PersistentClient(path="/data/chroma/logins")
collection = client.get_or_create_collection(name="logins")
greeting_dir="/data/tokens/de/hallo"
for target in glob(os.path.join(greeting_dir, '*-*')):
    if re.search(r'emb$',target):
        if os.path.isfile(target):
            emb2=load(target)
        else:
            continue
        user=re.search("^\w+-\w+",target.replace(greeting_dir,"")).group()
        print(user,emb2)
        #score = self.cos(emb1, emb2)[0][0].item()
        #if user not in users:
        #    users[user]=[]
        #users[user].append(score)
        #for user in users:
        #    n_neighbors=3;
        #    n_closest=heapq.nlargest(n_neighbors,users[user]);
        #    avg_score=sum(n_closest)/len(n_closest);
        #   logger.debug(user+" "+str(avg_score))
        #    if avg_score>max_sim and avg_score>float(threshold):
        #        max_sim=avg_score
        #        login=user
        #print(f,max_sim,login)


