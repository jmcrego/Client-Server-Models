import os
import json
import time
import logging
import argparse
import pyonmttok
import ctranslate2
from flask import Flask, request, jsonify
from socketserver import ThreadingMixIn

Tokenizer = None
Translator = None
loaded_cfg = None
logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=getattr(logging, 'INFO'), filename=None)


def load_models_if_required(cfg):
    '''                                                                                                                                                                                                                                                         
    Load tokenizers/ct2_model outside the handler to persist across invocations. Load only if not previously loaded with same cfg                                                                                                                               
    '''
    load_tok_time = 0.
    load_ct2_time = 0.

    global Tokenizer, Translator, loaded_cfg
    
    if cfg is None or not os.path.isdir(cfg) or cfg == loaded_cfg:
        return load_tok_time, load_ct2_time
    
    tok_config = os.path.join(cfg, 'tok_config.json')
    ct2_config = os.path.join(cfg, 'ct2_config.json')

    def read_json_config(config_file):
        if os.path.isfile(config_file):
            try:
                with open(config_file, 'r') as file:
                    content = file.read()
                    config = json.loads(content)
                    return config
            except (json.JSONDecodeError, IOError):
                return None
            except Exception:
                return None
        return None

    config_tok = read_json_config(tok_config)
    config_ct2 = read_json_config(ct2_config)

    if config_tok is None or config_ct2 is None:
        return load_tok_time, load_ct2_time
                
    tic = time.time()
    if 'bpe_model_path' in config_tok: ### the bpe file must be in the cfg directory
        config_tok['bpe_model_path'] = os.path.join(cfg, os.path.basename(config_tok['bpe_model_path']))
    mode = config_tok.pop('mode', 'aggressive')
    Tokenizer = pyonmttok.Tokenizer(mode, **config_tok)
    load_tok_time = 1000*(time.time() - tic)
    logging.info(f'LOAD: msec={load_tok_time} tok_config={tok_config}')

    tic = time.time()
    model_path = config_ct2.pop('model_path', None) ### delete it from config
    model_path = cfg ### the model must be in the cfg directory  
    Translator = ctranslate2.Translator(model_path, **config_ct2)
    load_ct2_time = 1000*(time.time() - tic)
    logging.info(f'LOAD: msec={load_ct2_time} ct2_config={ct2_config}')

    loaded_cfg = cfg
        
    return load_tok_time, load_ct2_time

def run(r):
    start_time = 1000*time.time()
    cfg = r.pop('cfg', None)
    txt = r.pop('txt', [])
    dec = r.pop('dec', {})
    logging.info(f"REQ: cfg={cfg} dec={dec} txt={txt}")

    if len(txt)==0:
        logging.info(f'Error: missing txt parameter in request')
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "missing txt parameter in request",
                "msec": 1000*time.time() - start_time
            })
        }

    if loaded_cfg is None and cfg is None:
        logging.info(f'Error: missing cfg parameter in request')
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "missing cfg parameter in request",
                "msec": 1000*time.time() - start_time
            })
        }
    
    load_tok_time, load_ct2_time = load_models_if_required(cfg)
    
    global Tokenizer, Translator
    
    if Tokenizer is None or Translator is None:
        logging.info(f'error: resources unavailable')
        return {
            'statusCode': 400,
            'body': {
                "error": "resources unavailable",
                "msec": 1000*time.time() - start_time
            }
        }
    
    tic = time.time()
    tok, _ = Tokenizer.tokenize_batch(txt)
    assert len(tok) == len(txt)
    tok_time = 1000*(time.time() - tic)
    logging.info(f'tok={tok_time} ms')
    

    tic = time.time()
    trn = Translator.translate_batch(tok, **dec)
    assert len(trn) == len(tok)
    ct2_time = 1000*(time.time() - tic)
    logging.info(f'ct2={ct2_time} ms')

    tic = time.time()
    data = []
    for i in range(len(trn)):
        hyp = []
        for j in range(len(trn[i].hypotheses)):
            hyp.append({
                'txt': Tokenizer.detokenize(trn[i].hypotheses[j]),
                'tok': ' '.join(trn[i].hypotheses[j]),
                'score': trn[i].scores[j] if len(trn[i].scores)>i else None,
                'attention': trn[i].attention[j] if len(trn[i].attention)>j else None
            })
        data.append({
            'txt': txt[i],
            'tok': ' '.join(tok[i]),
            'hyp': hyp
        })
    pos_time = 1000*(time.time() - tic)
    logging.info(f'pos={pos_time} ms')
    logging.info(f'DATA: {data}')

    return {
        'statusCode': 200,
        "data": data,
        "conf": {
            "cfg": loaded_cfg,
            "dec": dec
        },
        "time": {
            "load_tok": load_tok_time,
            "load_ct2": load_ct2_time,
            "tok": tok_time,
            "ct2": ct2_time,
            "pos": pos_time
        }
    }
        
class ThreadedFlaskServer(ThreadingMixIn, Flask): #this class is for multithreading
    pass

#app = Flask(__name__) #without multithreading
app = ThreadedFlaskServer(__name__) #with multithreading
@app.route('/translate', methods=['POST'])
def translate():
    return jsonify(run(request.json))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Description.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host', type=str, help='Host used (use 0.0.0.0 to allow distant access, otherwise use 127.0.0.1)', default='0.0.0.0')
    parser.add_argument('--port', type=int, help='Port used in local server', default=5000)
    parser.add_argument('--cfg',  type=str, help='Load model when launching', default=None)
    args = parser.parse_args()

    if args.cfg is not None:
        _, _ = load_models_if_required(args.cfg)
    
    #You can run Flask directly using this script (for development), Ex: python translate-server.py
    #or run app class with gunicorn (loads the app object, not main), Ex: gunicorn -w 1 --threads 100 translate-server:app -b 0.0.0.0:5000

    app.run(host=args.host, port=args.port, threaded=True) #threaded allows multithreading

