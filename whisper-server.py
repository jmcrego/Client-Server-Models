import time
import logging
import argparse
import numpy as np
from faster_whisper import WhisperModel
from flask import Flask, request, jsonify

def run(model, r): 
    logging.debug("[server] request: history={} task={}, lang={}, beam_size={} len(audio)={}".format(r['history'], r['task'], r['lang'], r['beam_size'], len(r['audio'])))
    tic = time.time()
    segments, info = model.transcribe(
        np.asarray(r['audio'], dtype=np.float32),
        language=r['lang'],
        task=r['task'],
        beam_size=int(r['beam_size']),
        vad_filter=True,
        word_timestamps=True,
        initial_prompt=r['history']
    )
    hyp = []
    for segment in segments:
        for word in segment.words:
            hyp.append({'start':word.start, 'end':word.end, 'word':word.word, 'wordP':word.probability})
    out = {'lang': info.language, 'langP': info.language_probability, 'hyp': hyp}
    toc = time.time()
    logging.info('[server] len(audio)={} ntoks={} time={:.2f} time_per_tok={:.2f}'.format(len(r['audio']), len(hyp), toc-tic, (toc-tic)/len(hyp) if len(hyp) else 0))
    logging.debug('[server] answer: {} took {:.2f} sec'.format(out, toc-tic))
    return out

    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='This script launches a Whisper server behind a REST api (use: http://[host]:[port]/whisper).', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--host', type=str, help='Host used (use 0.0.0.0 to allow distant access, otherwise use 127.0.0.1)', default='0.0.0.0')
    parser.add_argument('--port', type=int, help='Port used in local server', default=8000)
    
    group_model = parser.add_argument_group("Whisper")
    group_model.add_argument('--size',    type=str, help='model size: tiny, base, small, medium, large-v1, large-v2', default='tiny')
    group_model.add_argument('--compute', type=str, help='compute type: int8, float16, int8_float16', default='int8')
    group_model.add_argument('--device',  type=str, help='device: cpu, cuda, auto', default='auto')
    
    group_other = parser.add_argument_group("Other")
    group_other.add_argument('--log', type=str, help='logging level: (verbose) debug, info, warning, error, critical (silent)', default='info')
    args = parser.parse_args()

    logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=getattr(logging, 'INFO'), filename=None)
    logging.getLogger('faster_whisper').setLevel(logging.ERROR)    

    w = WhisperModel(args.size, device=args.device, compute_type=args.compute)
    logging.debug('[server] Loaded WhisperModel({}, {}, {})'.format(args.size, args.device, args.compute))
        
    app = Flask(__name__)
    @app.route('/whisper', methods=['POST'])
    def send_data():
        return jsonify(run(w, request.json))
    
    app.run(host=args.host, port=args.port)

