import os
import json
import time
import logging
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

def lambda_handler(event):
    print(event)
    start_time = time.time()
    cfg = event.get('queryStringParameters', {}).get('cfg', None)
    txt = event.get('queryStringParameters', {}).get('txt', None)
    logging.info(f'REQUEST: cfg={cfg} txt={txt}')

    if txt is None or cfg is None:
        logging.info(f'Error: missing required parameter in request')
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "missing required parameter in request",
                "duration": time.time() - start_time
            })
        }

    load_models_if_required(cfg)

    global tok, ct2
    if tok is None or ct2 is None:
        logging.info(f'error: resources unavailable')
        return {
            'statusCode': 400,
            'body': json.dumps({
                "error": "resources unavailable",
                "duration": time.time() - start_time
            })
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
        'body': json.dumps({
            "txt": txt,
            "txt_tok": txt_tok,
            "out_tok": out_tok,
            "out": out,
            "duration": time.time() - start_time
        })
    }


app = Flask(__name__)

@app.route('/translate', methods=['POST'])
def translate():
    return lambda_handler(request.json)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
