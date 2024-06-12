import sys
import time
import logging
import argparse
import requests

def send_request_to_server(url, timeout, sentence, level, style, domain, npar):
    req = { 'sentence':sentence, 'level':level, 'style':style, 'domain':domain, 'npar':npar }
    logging.debug('req: {}'.format(req))
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
    parser.add_argument('--npar', type=str, help='request npar paraphrases', default='three')
    parser.add_argument('--timeout', type=float, help='url request timeout', default=10.0)
    group_other = parser.add_argument_group("Other")
    group_other.add_argument('--log', type=str, help='logging level: (verbose) debug, info, warning, error, critical (silent)', default='warning')
    args = parser.parse_args()
    logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=getattr(logging, args.log.upper()), filename=None)


    print(send_request_to_server(args.url, args.timeout, args.sentence, args.level, args.style, args.domain, args.npar))
