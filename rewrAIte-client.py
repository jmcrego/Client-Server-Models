import re
import sys
import time
import logging
import argparse
import requests

def send_request_to_server(url, timeout, instruction, sentence, N):
    req = { 'instruction':instruction, 'sentence':sentence, 'N': N}
    tic = time.time()
    try:
        response = requests.post(url, json=req, headers={"Content-Type": "application/json"}, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        logging.error("POST Request Error (ConnectionError): %s", e)
        raise SystemExit(e)
    except requests.exceptions.Timeout as e: 
        logging.error("POST Request Error (Timeout): %s", e)
        raise SystemExit(e)
    except requests.exceptions.ConnectionError as e:
        logging.error("POST Request Error (ConnectionError): %s", e)
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
    except requests.exceptions.JSONDecodeError as e:
        logging.error("Response body did not contain valid json: %s", e)
        raise SystemExit(e)
    logging.debug('server request took {:.2f} sec'.format(time.time()-tic))
    return out


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='This script calls a rewrAIt server.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('url', type=str, help='server url (Ex: http://0.0.0.0:8001/rewrAIte)')
    parser.add_argument('--sentence', type=str, help='input sentence', required=True)
    parser.add_argument('--level', type=str, help='rewriting level: Minimal, Moderate, Extensive', default='Minimal')
    parser.add_argument('--style', type=str, help='writing style: Simple, Profesional, Academic, Casual', default='Simple')
    parser.add_argument('--domain', type=str, help='domain: Generic, Medical, Legal, Bank, Technical', default='Generic')
    parser.add_argument('--lang', type=str, help='language of the paraphrase writer', default='English')
    parser.add_argument('--npar', type=int, help='request npar paraphrases', default=3)
    parser.add_argument('--timeout', type=float, help='url request timeout', default=10.0)
    group_other = parser.add_argument_group("Other")
    group_other.add_argument('--log', type=str, help='logging level: (verbose) debug, info, warning, error, critical (silent)', default='warning')
    args = parser.parse_args()
    logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=getattr(logging, args.log.upper()), filename=None)

    str_domain = f" specialized in the {args.domain} domain" if args.domain != "Generic" else ""
    str_style = f" employing a {args.style} style" if args.style != "Generic" else ""
    instruction = f"You are an expert {args.lang} proofreader{str_domain}{str_style}. Given the text below, first rewrite it fixing errors if any (leave correct parts unchanged), and then write {args.npar} paraphrases with a {args.style} rewriting level. All your sentences must be grammatically correct. Do not add any comments and write only in {args.lang}."
        
    out = send_request_to_server(args.url, args.timeout, instruction, args.sentence, args.npar*2)['hyp']
    for i,l in enumerate(out.split('\n')):
        if len(l) and not re.match(r'^Paraphrases:\s*$', l):
            if i==0:
                print(l)
            else:
                l = re.sub(r'^\d\.\s*', '', l)
                print(l)
