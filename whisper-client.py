import sys
import time
import logging
import argparse
from Streamer import Streamer

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='This script reads audio data from the available microphone (or wav/mp3 file) and performs (or simulates) ASR/ST using a Whisper server.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('url', type=str, help='server url (Ex: http://0.0.0.0:8000/whisper)')
    group_audio = parser.add_argument_group("Audio")    
    group_audio.add_argument('--channels', type=int, help='channels: 1 (mono), 2 (stereo)', default=1)
    group_audio.add_argument('--srate', type=int, help='sample rate', default=16000)
    group_audio.add_argument('--block', type=int, help='size of audio block stored', default=4096)
    group_audio.add_argument('--file', type=str, help='stream this wav/mp3 file rather than microphone', default=None)
    group_audio.add_argument('--play', action='store_true', help='play audio while streaming file')
    group_stream = parser.add_argument_group("Stream")    
    group_stream.add_argument('--task', type=str, help='task to perform: transcribe, translate', default='transcribe')
    group_stream.add_argument('--lang', type=str, help='force language', default=None)
    group_stream.add_argument('--beam', type=int, help='beam size', default=5)
    group_stream.add_argument('--every', type=float, help='minimum delay (seconds) between transcriptions', default=2.0)
    group_stream.add_argument('--max_segment_time', type=float, help='segment larger than this amount of words are forced to confirm', default=6.0)
    group_stream.add_argument('--min_common_words', type=int, help='minimum number of common words to confirm a prefix', default=2)
    group_stream.add_argument('--min_remain_words', type=int, help='minimum number of remaining words after confirmed prefix', default=1)
    group_stream.add_argument('--timeout', type=int, help='url request timeout', default=10.0)
    group_other = parser.add_argument_group("Other")
    group_other.add_argument('--log', type=str, help='logging level: (verbose) debug, info, warning, error, critical (silent)', default='warning')
    args = parser.parse_args()
    logging.basicConfig(format='[%(asctime)s.%(msecs)03d] %(levelname)s %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=getattr(logging, args.log.upper()), filename=None)
    #logging.getLogger('faster_whisper').setLevel(logging.ERROR)

    s = Streamer(
        args.url,
        timeout=args.timeout,
        channels=args.channels,
        samplerate=args.srate,
        blocksize=args.block,
        audio_file=args.file,
        task=args.task,
        lang=args.lang,
        beam_size=args.beam,
        every=args.every,
        min_common_words=args.min_common_words,
        min_remain_words=args.min_remain_words,
        max_segment_time=args.max_segment_time,
        play=args.play,
    )
    
    #logging.info('Processing... use [Ctrl+c] to terminate streaming')
    if not args.file:
        print('Processing... use [Ctrl+c] to terminate streaming', file=sys.stderr)
    else:
        print('Processing file {}'.format(args.file), file=sys.stderr)
    tic = time.time()
    try:
        s()
    except KeyboardInterrupt:
        logging.info('KeyboardInterrupt')
    #logging.info('Done, audio duration={:.2f} sec'.format(time.time()-tic))
    #print('Done, audio duration={:.2f} sec'.format(time.time()-tic), file=sys.stderr)

