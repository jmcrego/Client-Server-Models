import time
import json
import logging
import requests

def send_request_to_server(url, timeout, cfg, dec, txt):
    req = { 'cfg':cfg, 'dec': dec, 'txt':txt }
    tic = 1000*time.time()
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
        res = response.json()
    except json.JSONDecodeError as e:
        logging.error("Response body did not contain valid json: %s", e)
        raise SystemExit(e)
    logging.debug('server request took {:.2f} msec'.format(1000*time.time()-tic))
    return res
