#import sys
import time
import json
import logging
import argparse
from request import send_request_to_server

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='This script sends a request to a distant translation server.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--txt', type=str, nargs='+', help='list of strings to translate', required=True)
    parser.add_argument('--cfg', type=str, help='config resources', default=None)
    parser.add_argument('--url', type=str, help='server url entry point', default='http://0.0.0.0:5000/translate')
    parser.add_argument('--dec', type=str, help='ctranslate2 decoding options in JSON dictionary (see https://opennmt.net/CTranslate2/python/ctranslate2.Translator.html#ctranslate2.Translator.score_batch for available options)', default='{"beam_size": 5, "num_hypotheses": 1}')
    parser.add_argument('--timeout', type=float, help='url request timeout', default=10.0)
    args = parser.parse_args()
    args.dec = json.loads(args.dec)
    logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=logging.INFO, filename=None)

    res = send_request_to_server(args.url, args.timeout, args.cfg, args.dec, args.txt)
    print('data = ' + json.dumps(res.get('data', {}), indent=4, ensure_ascii=False))                
    print('conf = ' + json.dumps(res.get('conf', {}), indent=4, ensure_ascii=False))                
    print('time = ' + json.dumps(res.get('time', {}), indent=4, ensure_ascii=False))                
        
