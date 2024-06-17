import tensorflow as tf

def load_graph(model_path):
    print("Loading model...")
    with tf.io.gfile.GFile(model_path, "rb") as f:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(f.read())
    with tf.Graph().as_default() as graph:
        tf.import_graph_def(graph_def, name="")
    print("Model loaded")
    return graph

graph = load_graph('/data/HMPL/daniel-hromada/de/output_graph.pb')
while 1:
    continue
