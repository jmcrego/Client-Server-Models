import os
import json
import time
import logging
import argparse
import pyonmttok
import ctranslate2
from flask import Flask, request, jsonify

Tokenizer = None
Translator = None
loaded_cfg = None

def read_json_config(config_file):
    config = None
    if os.path.isfile(config_file):
        with open(config_file, 'r') as file:
            config = json.load(file)
    return config

def load_models_if_required(cfg):
    '''                                                                                                                                                                                                                                                         
    Load tokenizers/ct2_model outside the handler to persist across invocations. Load only if not previously loaded with same cfg                                                                                                                               
    '''
    tok_config = os.path.join(cfg, 'tok_config.json')
    ct2_config = os.path.join(cfg, 'ct2_config.json')

    load_tok_time = 0
    load_ct2_time = 0
    
    global Tokenizer, Translator, loaded_cfg

    if Tokenizer is None or cfg != loaded_cfg:
        config = read_json_config(tok_config)
        if config is not None:
            tic = time.time()
            mode = config.pop('mode', 'aggressive')
            Tokenizer = pyonmttok.Tokenizer(mode, **config)
            load_tok_time = time.time() - tic
            logging.info(f'LOAD: msec={1000 * load_tok_time:.2f} tok_config={tok_config}')

    if Translator is None or cfg != loaded_cfg:
        config = read_json_config(ct2_config)
        if config is not None:
            tic = time.time()
            model_path = config.pop('model_path', None)
            Translator = ctranslate2.Translator(model_path, **config)
            load_ct2_time = time.time() - tic
            logging.info(f'LOAD: msec={1008 * load_ct2_time:.2f} ct2_config={ct2_config}')

    loaded_cfg = cfg
    return load_tok_time, load_ct2_time

def run(r):
    start_time = time.time()
    cfg = r.pop('cfg', None)
    txt = r.pop('txt', None)
    dec = r.pop('dec', {})
    logging.info(f"REQ: cfg={cfg} dec={dec} txt={txt}")

    if txt is None or cfg is None:
        logging.info(f'Error: missing required parameter in request')
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "missing required parameter in request",
                "msec": f"{1000 * (time.time() - start_time):.2f}"
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
                "msec": f"{1000 * (time.time() - start_time):.2f}"
            }
        }
    
    tic = time.time()
    tok, _ = Tokenizer.tokenize(txt)
    tok_time = time.time() - tic
    logging.info(f'TOK: msec={1000 * (time.time() - tic):.2f} tok={tok}')
    
    tic = time.time()
    out = []
    res = Translator.translate_batch([tok], **dec)
    for i in range(len(res[0].hypotheses)):
        out.append({
            'tok': res[0].hypotheses[i],
            'txt': Tokenizer.detokenize(res[0].hypotheses[i]),
            'score': res[0].scores[i] if len(res[0].scores)>i else None,
            'attention': res[0].attention[i] if len(res[0].attention)>i else None
        })
    ct2_time = time.time() - tic
    logging.info(f'CT2: msec={1000 * (time.time() - tic):.2f} out={out}')
    
    return {
        'statusCode': 200,
        'body': {
            "txt": txt,
            "tok": tok,
            "out": out,
            "msec": {
                "load_tok": f"{1000 * load_tok_time:.2f}",
                "load_ct2": f"{1000 * load_ct2_time:.2f}",
                "tok": f"{1000 * tok_time:.2f}",
                "ct2": f"{1000 * ct2_time:.2f}",
                "total": f"{1000 * (time.time() - start_time):.2f}"
            }
        }
    }
        
        
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Description.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host', type=str, help='Host used (use 0.0.0.0 to allow distant access, otherwise use 127.0.0.1)', default='0.0.0.0')
    parser.add_argument('--port', type=int, help='Port used in local server', default=5000)
    parser.add_argument('--cfg',  type=str, help='Load model when launching', default=None)
    args = parser.parse_args()
    logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=getattr(logging, 'INFO'), filename=None)

    if args.cfg is not None:
        _, _ = load_models_if_required(args.cfg)
    
    app = Flask(__name__)    
    @app.route('/translate', methods=['POST'])
    def send_data():
        return jsonify(run(request.json))
    
    app.run(host=args.host, port=args.port)

