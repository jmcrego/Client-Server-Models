import os
import json
import time
import logging
import argparse
import pyonmttok
import ctranslate2
from flask import Flask, request, jsonify

tok = None
ct2 = None
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

    global tok, ct2, loaded_cfg

    if tok is None or cfg != loaded_cfg:
        config = read_json_config(tok_config)
        if config is not None:
            tic = time.time()
            mode = config.pop('mode', 'aggressive')
            tok = pyonmttok.Tokenizer(mode, **config)
            logging.info(f'LOAD: msec={1000 * (time.time() - tic):.2f} tok_config={tok_config}')

    if ct2 is None or cfg != loaded_cfg:
        config = read_json_config(ct2_config)
        if config is not None:
            tic = time.time()
            model_path = config.pop('model_path', None)
            ct2 = ctranslate2.Translator(model_path, **config)
            logging.info(f'LOAD: msec={1008 * (time.time() - tic):.2f} ct2_config={ct2_config}')

    loaded_cfg = cfg
    return

def run(r):
    #cfg = event.get('queryStringParameters', {}).get('cfg', None)
    #txt = event.get('queryStringParameters', {}).get('txt', None)
    cfg = r.get('cfg', None)
    txt = r.get('txt', None)
    logging.info(f"REQ: cfg={cfg} txt={txt}")
    start_time = time.time()

    if txt is None or cfg is None:
        logging.info(f'Error: missing required parameter in request')
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "missing required parameter in request",
                "msec": f"{1000 * (time.time() - start_time):.2f}"
            })
        }

    load_models_if_required(cfg)

    global tok, ct2
    
    if tok is None or ct2 is None:
        logging.info(f'error: resources unavailable')
        return {
            'statusCode': 400,
            'body': {
                "error": "resources unavailable",
                "msec": f"{1000 * (time.time() - start_time):.2f}"
            }
        }

    tic = time.time()
    txt_tok, _ = tok.tokenize(txt)
    tok_time = time.time() - tic
    logging.info(f'TOK: msec={1000 * (time.time() - tic):.2f} txt_tok={txt_tok}')

    tic = time.time()
    out_tok = ct2.translate_batch([txt_tok])[0].hypotheses[0]
    ct2_time = time.time() - tic
    logging.info(f'CT2: msec={1000 * (time.time() - tic):.2f} out_tok={out_tok}')

    tic = time.time()
    out = tok.detokenize(out_tok)
    tok_time = time.time() - tic
    logging.info(f'TOK: msec={1000 * (time.time() - tic):.2f} out={out}')

    return {
        'statusCode': 200,
        'body': {
            "txt": txt,
            "txt_tok": txt_tok,
            "out_tok": out_tok,
            "out": out,
            "msec": f"{1000 * (time.time() - start_time):.2f}"
        }
    }


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Description.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host', type=str, help='Host used (use 0.0.0.0 to allow distant access, otherwise use 127.0.0.1)', default='0.0.0.0')
    parser.add_argument('--port', type=int, help='Port used in local server', default=5000)
    args = parser.parse_args()
    logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=getattr(logging, 'INFO'), filename=None)
    
    app = Flask(__name__)    
    @app.route('/translate', methods=['POST'])
    def send_data():
        return jsonify(run(request.json))
    
    app.run(host=args.host, port=args.port)
