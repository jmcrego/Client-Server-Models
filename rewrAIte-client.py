import re
import sys
import time
import logging
import argparse
import requests

def send_request_to_server(url, timeout, instruction, text, N):
    req = { 'instruction':instruction, 'text':text, 'N': N}
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
    parser.add_argument('--text',     type=str,   help='text to rewrite', required=True)
    parser.add_argument('--lang',     type=str,   help='language of the writer', default='English')
    parser.add_argument('--n',        type=int,   help='number of paraphrases requested', default=3)
    parser.add_argument('--level',    type=str,   help='rewriting level: Minimal, Moderate, Extensive', default='Minimal')
    parser.add_argument('--style',    type=str,   help='style of the writer: Simple, Profesional, Academic, Casual', default='Simple')
    parser.add_argument('--domain',   type=str,   help='domain of the writer: Generic, Medical, Legal, Bank, Technical', default='Generic')
    parser.add_argument('--timeout',  type=float, help='url request timeout', default=10.0)
    group_other = parser.add_argument_group("Other")
    group_other.add_argument('--log', type=str, help='logging level: (verbose) debug, info, warning, error, critical (silent)', default='warning')
    args = parser.parse_args()
    logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=getattr(logging, args.log.upper()), filename=None)

    str_domain = f" specialized in the {args.domain} domain" if args.domain != "Generic" else ""
    str_style = f" employing a {args.style} style" if args.style != "Generic" else ""

    instruction = f"""You are an expert proofreader employing language={args.lang}, domain={args.domain} and writing style={args.style}. Rewrite first the text below only correcting errors (do not add/remove/replace words unless incorrect), and add {args.n} different paraphrases to the original text. All your sentences must be grammatically correct and convey the same meaning. Your output does not contain explanations. Your only write in {args.lang}. Follow the next formatting exemples:

<txt> Mon ami ne veux pas manger de la viande. </txt>
<fix> Mon ami ne veut pas manger de viande. </fix>
<par> Mon ami n'aime pas manger de la viande. </par>
<par> Je ne mange pas de viande, selon mon ami. </par>
<par> Mon ami préfère ne pas manger de viande. </par>

<txt> Leaders of the world's seven richer nations are expected to agre a plan to use frozen Russian assets to raise money for Ukraine. </txt>
<fix> Leaders of the world's seven richest nations are expected to agree on a plan to use frozen Russian assets to raise money for Ukraine. </fix>
<par> The leaders of the world's seven richest nations are anticipated to reach a consensus on a strategy to tap into frozen Russian assets to fund Ukraine. </par>
<par> It is expected that the leaders of the seven wealthiest nations will agree on a plan to access frozen Russian assets to provide funds for Ukraine. </par>
<par> The leaders of the seven richest nations are expected to concur on a strategy to use frozen Russian assets to generate funds for Ukraine's benefit. </par>"""


    out = send_request_to_server(args.url, args.timeout, instruction, '<txt> '+args.text+' </txt>', args.n*2)['hyp']
    for i,l in enumerate(out.split('\n')):
        if len(l):
            print(l)

