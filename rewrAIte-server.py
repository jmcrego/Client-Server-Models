import time
import logging
import argparse
import numpy as np
import ctranslate2
from transformers import AutoTokenizer
from flask import Flask, request, jsonify

def run(generator, tokenizer, r):
    instruction = r['instruction']
    text = r['text']
    N = int(r['N'])
    prompt = f'<s>[INST] <<SYS>>\n{instruction}\n<</SYS>>\n\n{text} [/INST]'
    tic = time.time()
    max_length = len(tokenizer.encode(text)) * (N+1)
    logging.debug(f"[server] text with {len(tokenizer.encode(text))} tokens, N={N}")
    prompt_tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(prompt))
    logging.debug(f"[server] request: max_length={max_length} prompt={prompt}")
    results = generator.generate_batch([prompt_tokens], max_length=max_length, include_prompt_in_result=False)
    output = tokenizer.decode(results[0].sequences_ids[0])
    toc = time.time()
    logging.debug('[server] response: time={:.2f} length={} output={}'.format(toc-tic, len(results[0].sequences_ids[0]), output))
    return {'hyp': output}

    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='This script launches an LLM server behind a REST api (use: http://[host]:[port]/whisper).', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host', type=str, help='Host used (use 0.0.0.0 to allow distant access, otherwise use 127.0.0.1)', default='0.0.0.0')
    parser.add_argument('--port', type=int, help='Port used in local server', default=8001)
    group_model = parser.add_argument_group("LLM")
    group_model.add_argument('--model_id',  type=str, help='HF model id', default='mistralai/Mistral-7B-v0.3')
    group_model.add_argument('--model_dir', type=str, help='model local directory', default='/nfs/RESEARCH/senellarta/dev/research/ct2-mistral-instruct')
    group_model.add_argument('--compute', type=str, help='compute type: int8, float16, int8_float16', default='float32')
    group_model.add_argument('--device',  type=str, help='device: cpu, cuda, auto', default='auto')    
    group_other = parser.add_argument_group("Other")
    group_other.add_argument('--log', type=str, help='logging level: (verbose) debug, info, warning, error, critical (silent)', default='info')
    args = parser.parse_args()
    
    logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=getattr(logging, args.log.upper()), filename=None)
    logging.getLogger('transformers').setLevel(logging.ERROR)    
    logging.getLogger('ctranslate2').setLevel(logging.ERROR)    
    
    t = AutoTokenizer.from_pretrained(args.model_id)
    logging.debug('[server] Loaded tokenizer {}'.format(args.model_id))
    
    g = ctranslate2.Generator(args.model_dir, device=args.device, compute_type=args.compute)
    logging.debug('[server] Loaded {}({}, {})'.format(args.model_dir, args.device, args.compute))
        
    app = Flask(__name__)
    @app.route('/rewrAIte', methods=['POST'])
    def send_data():
        return jsonify(run(g, t, request.json))
    
    app.run(host=args.host, port=args.port)

