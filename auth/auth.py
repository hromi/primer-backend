import json,os
from pathlib import Path
#from time import perf_counter
from sanic import Sanic, response
from sanic.log import logger
#from os.path import exists
#from re import match
import hashlib
from pyhocon import ConfigFactory
import torch,torchaudio
from speechbrain_auth.engine_chroma import AuthEngine
from concurrent.futures import ThreadPoolExecutor
import chromadb

#monkey patch necessary for some Jetsons
setattr(torch.distributed, "is_initialized", lambda : False)

conf = ConfigFactory.parse_file("/home/mame/application.conf")

chromaclient=chromadb.PersistentClient(conf["chroma_path"])
collection = chromaclient.get_or_create_collection(name="test",metadata={"hnsw:space": "cosine"})


engine = AuthEngine(
    collection,
    conf
)

# Initialze Sanic and ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=conf["server.threadpool.count"])
app = Sanic("auth_server")

#with this setting it somehow works...with others, it is tricky
app.config.WEBSOCKET_MAX_SIZE = 2 ** 21

@app.route("/", methods=["GET"])
async def healthcheck(_):
    return response.text("welcome to lesen-mikroserver-auth")

#special route to manually associate username with last embedding
@app.route("/last/<login>", methods=["GET"])
async def last(request, login):
    result = collection.get(where={'login': 'last'})
    if result and 'ids' in result and result['ids']:
        collection.update(ids=[str(result['ids'][0])], metadatas=[{'login': login}])
        return response.text(f"chroma item with login last updated to {login}")
    else:
        return response.text("No chroma item found with login last", status=404)

@app.websocket("/auth/<token>/<device>")
async def auth(request, ws, token, device):
    audio = await ws.recv()
    
    # voice identification
    f,similarity,login = await app.loop.run_in_executor(executor, lambda: engine.run(audio,token.lower(),device))

   # following lines are to authenticate against third party system (e.g. Kastalia KMS), make sure You use the same secret on both sides 
   # Concatenating the strings and encoding them to UTF-8
    data_to_hash = (login + str(similarity) + conf["scrt"]).encode('utf-8')
    # Creating a SHA-256 hash of the UTF-8 encoded string
    hash = hashlib.sha256(data_to_hash).hexdigest()

    await ws.send('{"login":"'+login+'","similarity":'+str(similarity)+',"hash":"'+hash+'"}')
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
