#import sys
import os
import time
import logging
import numpy as np
import threading
import requests
import sounddevice as sd
import soundfile as sf
from faster_whisper.audio import decode_audio

RESET = "\033[0m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_WHITE = "\033[97m"

def save(self, data, file_name, samplerate=16000):
    """ 
    Save each audio data split (transcripts) into files
    file_name: the output file name (available extensions: 'AIFF', 'AU', 'AVR', 'CAF', 'FLAC', 'HTK', 'SVX', 'MAT4', 'MAT5', 'MPC2K', 'MP3', 'OGG', 'PAF', 'PVF', 'RAW', 'RF64', 'SD2', 'SDS', 'IRCAM', 'VOC', 'W64', 'WAV', 'NIST', 'WAVEX', 'WVE', 'XI')
    """
    logging.info('save data = {}'.format(data.shape))
    sf.write(file_name, data, samplerate)

def send_audio_to_server(url, timeout, audio, history, task, lang, beam_size, start, samplerate):
    req = { 'audio':audio.tolist(), 'history':history, 'task':task, 'lang':lang, 'beam_size':beam_size }
    
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
    logging.debug('server request took {:.2f} sec time(audio)={} ntoks={}'.format(time.time()-tic, len(audio)/samplerate, len(out['hyp'])))

    for i in range(len(out['hyp'])):
        out['hyp'][i]['start'] = int(out['hyp'][i]['start'] * samplerate) + start
        out['hyp'][i]['end'] = int(out['hyp'][i]['end'] * samplerate) + start
    return out


class Segments():
    def __init__(self, samplerate, min_common_words, min_remain_words, max_segment_time):
        self.samplerate = samplerate
        self.min_common_words = min_common_words
        self.min_remain_words = min_remain_words
        self.max_segment_time = max_segment_time
        self.tini = time.time()
        s = { 'start':0, 'end':0, 'lang':'', 'langP':'', 'pref':[{'start':0, 'end':0, 'word':''}], 'hyp':[] }
        self.segments = [s]

    def __call__(self, start, end, lang, langP, pref, hyp, finish=False):
        t = { 'start':start, 'end':end, 'lang':lang, 'langP':langP, 'pref':pref, 'hyp':hyp }
        self.segments.append(t)
        self.log()
        """
        We now identify if a prefix of the last hypothesis is confirmed using either:
        - the last segment is too long (> self.max_segment_time) and has at least 2 words
        - the prev/last hypotheses:
          + start at the same time AND
          + share a common prefix (larger than self.min_common_words) AND
          + there must be at least self.min_remain_words between end of prefix and end of hyp
        """
        last = self.segments[-1]
        prev = self.segments[-2]

        if finish:
            k_common = len(last['hyp'])
            self.confirm(k_common)
            print()
            return
        
        duration_time = (last['end'] - last['start']) / self.samplerate
        
        if len(last['hyp']) > self.min_remain_words and duration_time > self.max_segment_time:
            """ too long segment with at least min_remain_words+1 words, force confirmation """
            k_common = len(last['hyp']) - self.min_remain_words
            self.confirm(k_common)
            return

        if last['start'] != prev['start']:
            logging.debug('[Streamer] FAIL diff start')
            return
            
        """ compute the number of initial common tokens between last and prev hypotheses """
        k_common = sum([prev['hyp'][i]['word']==last['hyp'][i]['word'] and (i==0 or prev['hyp'][i-1]['word']==last['hyp'][i-1]['word']) for i in range(min(len(last['hyp']), len(prev['hyp'])))])

        """ compute min common/remain words """
        k_common = min(k_common, (len(last['hyp']) - self.min_remain_words))
        if k_common >= self.min_common_words and len(last['hyp']) - k_common >= self.min_remain_words:
            self.confirm(k_common)
            return
                        
        logging.debug('[Streamer] FAIL no common/remain words')
        return

    def confirm(self, k_common):
        """ remove the initial k_common words from hyp and add them to the end of pref """
        assert len(self.segments)
        assert len(self.segments[-1]['hyp']) >= k_common
        self.segments[-1]['pref']   += self.segments[-1]['hyp'][:k_common]
        self.segments[-1]['hyp']     = self.segments[-1]['hyp'][k_common:]
        #logging.info("[Streamer] CONFIRM                                 < {} +++ {} > k={}".format(self.pref(), self.hyp(), k_common))
        real_time = time.time() - self.tini
        conf_time = self.confirmed() / self.samplerate
        logging.info("[Streamer] CONFIRM k={} delay={:.2f}".format(k_common, real_time-conf_time))
        logging.debug("[Streamer] real: {:.2f} conf: {:.2f} delay: {:.2f}".format(real_time, conf_time, real_time-conf_time))
        ### clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"\r{BRIGHT_YELLOW}{self.pref()} {BRIGHT_WHITE}{self.hyp()}{RESET}", end="")
            
    def confirmed(self):
        return self.segments[-1]['pref'][-1]['end']
    
    def pref(self, get_list=False):
        if get_list:
            return self.segments[-1]['pref']
        return ''.join([ x['word'] for x in self.segments[-1]['pref'] ]).strip()

    def hyp(self, get_list=False):
        if get_list:
            return self.segments[-1]['hyp']
        return ''.join([ x['word'] for x in self.segments[-1]['hyp'] ]).strip()
                    
    def log(self):
        s = self.segments[-1]
        indexs = "[{}-{}]".format(s['start'], s['end'])
        indexs += ''.join([" "]*(15-len(indexs)))
        times = "[{:.2f}-{:.2f}]".format(s['start']/self.samplerate, s['end']/self.samplerate)
        times += ''.join([" "]*(15-len(times)))
        logging.info("[Streamer] SEGMENT {} {} < {} +++ {} >".format(indexs, times, self.pref(), self.hyp()))
    
class Streamer():

    def __init__(self, url, timeout=10.0, channels=1, samplerate=16000, blocksize=4096, audio_file=None, task='transcribe', lang=None, beam_size=5, every=1.0, min_common_words=2, min_remain_words=2, max_segment_time=5.0, play=False):
        self.url = url
        self.timeout = timeout
        self.channels = channels
        self.blocksize = blocksize
        self.samplerate = samplerate
        self.audio_file = decode_audio(audio_file, sampling_rate=samplerate) if audio_file is not None else None
        self.mic = sd.default.device[0] if self.channels == 1 else sd.default.device[1]
        self.min_common_words = min_common_words
        self.min_remain_words = min_remain_words
        self.max_segment_time = max_segment_time
        self.beam_size = beam_size
        self.task = task
        self.lang = lang
        self.every = every
        """
        audio: the entire audio wave
        segments: list containing information from each call to whisper
        audio_lock: to prevent from concurrent access (read/write) to audio
        """
        self.audio = np.empty(0, dtype=np.float32)
        self.segments = Segments(self.samplerate, self.min_common_words, self.min_remain_words, self.max_segment_time)
        self.audio_lock = threading.Lock()

        if audio_file is not None and play:
            self.play()
        

    def __call__(self):

        def callback(indata, frames, time, status):
            """
            This function is employed by sd.InputStream to store the wave continuously read from the mic into self.audio. Called whenever new blocksize floats are available read from the mic.
            - indata: numpy.ndarray (block_size, 1) dtype=float32 containing audio captured from microphone.
            - frames: indicate the number of floats (same as block_size)
            - time:   time indication
            - status: exit indication
            """
            if status:
                logging.error('callback error: '.format(status))
            with self.audio_lock:
                self.audio = np.concatenate((self.audio, indata.squeeze()), dtype=np.float32)
            logging.debug('[callback] len(audio)={}'.format(len(self.audio)))

        def callback_fake(indata, frames, time, status):
            """
            This function is employed by sd.InputStream to store the wave continuously read from the mic into self.audio. Called whenever new blocksize floats are available read from the mic.
            - indata: numpy.ndarray (block_size, 1) dtype=float32 containing audio captured from microphone.
            - frames: indicate the number of floats (same as block_size)
            - time:   time indication
            - status: exit indication
            """
            if status:
                logging.error('callback_fake error: '.format(status))
            with self.audio_lock:
                self.audio = self.audio_file[:len(self.audio)+len(indata.squeeze())]
            logging.debug('[callback_fake] len(audio)={}'.format(len(self.audio)))
        
        """
        infinite loop (stopped using [Ctrl+c]) or end of audio_file
        """
        
        with sd.InputStream(device=self.mic, channels=self.channels, callback=callback_fake if self.audio_file is not None else callback, blocksize=self.blocksize, samplerate=self.samplerate):
            next_stream = time.time() + self.every
            while True:
                now = time.time()
                if next_stream-now > 0:
                    logging.info('sleep({:.2f})'.format(next_stream-now))
                    time.sleep(next_stream-now)
                else:
                    logging.info('late({:.2f})'.format(now-next_stream))                    
                next_stream += self.every
                self.transcribe()
                if self.audio_file is not None and len(self.audio) == len(self.audio_file):
                    break
            self.transcribe(finish=True)

    def transcribe(self, finish=False):
        logging.info('stream({:.2f})'.format(time.time()-self.segments.tini))
        start = self.segments.confirmed()
        pref = self.segments.pref(get_list=True)
        with self.audio_lock:
            end = len(self.audio)
        out = send_audio_to_server(self.url, self.timeout, self.audio[start:end], self.segments.pref(), self.task, self.lang, self.beam_size, start, self.samplerate)
        self.segments(start, end, out['lang'], out['langP'], pref, out['hyp'], finish=finish)

            
    def play(self, wait=False):
        """ 
        Play audio data
        """
        logging.info('playing')
        sd.play(self.audio_file, self.samplerate)
        if wait:
            sd.wait()

