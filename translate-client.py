#import sys
import time
import json
import logging
import argparse
import requests

def send_request_to_server(url, timeout, cfg, dec, txt):
    req = { 'cfg':cfg, 'dec': dec, 'txt':txt }
    try:
        response = requests.post(url, json=req, headers={"Content-Type": "application/json"}, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        logging.error("POST Request Error (ConnectionError): %s", e)
        raise SystemExit(e)
    except requests.exceptions.Timeout as e: 
        logging.error("POST Request Error (Timeout): %s", e)
        raise SystemExit(e)
    except requests.exceptions.TooManyRedirects as e: 
        logging.error("POST Request Error (TooManyRedirects): %s", e)
        raise SystemExit(e)
    except requests.exceptions.HTTPError as e:
        logging.error("POST Request Error (HTTPError): %s", e)
        raise SystemExit(e)
    except requests.exceptions.RequestException as e: 
        logging.error("POST Request Error (RequestException): %s", e)
        raise SystemExit(e)

    try:
        out = response.json()
    except json.JSONDecodeError as e:
        logging.error("Response body did not contain valid json: %s", e)
        raise SystemExit(e)
    return out


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

    tic = time.time()
    res = send_request_to_server(args.url, args.timeout, args.cfg, args.dec, args.txt)
    print(json.dumps(res.get('data', {}), indent=4, ensure_ascii=False))                
    print(json.dumps(res.get('stats', {}), indent=4, ensure_ascii=False))                
    logging.info(f'client msec={1000*(time.time()-tic)}')
        
