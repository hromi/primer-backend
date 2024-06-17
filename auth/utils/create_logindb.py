import chromadb
from glob import glob
from torch import save,load
import tempfile
from pathlib import Path
import re
#import numpy as np
chroma_path = Path(tempfile.gettempdir()) / 'chroma_db'
#client = chromadb.PersistentClient(path="/data/chroma/students")
print("init client"+str(chroma_path))
client = chromadb.PersistentClient(path=str(chroma_path))
print("client loaded")
collection = client.get_or_create_collection(name="test",metadata={"hnsw:space": "cosine"})
emb_dir='/data/tokens/de/hallo/'
for target in glob(emb_dir+'*emb'):
    user=re.search("^\w+-\w+",target.replace(emb_dir,"")).group()
    print("adding"+target)
    collection.add(embeddings=[load(target).flatten().tolist()],ids=[target],metadatas=[{"login":user}])
 
