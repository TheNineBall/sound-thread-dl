import os, urllib
import requests
import argparse
import time
from ffmpeg import video
import subprocess
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("url", help='The url of the thread.')
parser.add_argument("--watch", action='store_true', help='Watch for new posts and download them.')
args = parser.parse_args()

#TODO make these arguments, need to change the ffmpeg stuff for the format
TMP_PATH = 'temp'
OUT_PATH = 'out'
OUT_FORMAT = 'mkv'

class Chan:
    def __init__(self, url):
        self.board = 'a'
        self.thread = 1

        url = url.split('#')[0]
        url = url[:-1] if url.endswith('/') else url
        self.thread = url.split('/')[-1]
        self.board = url.split('/')[-3]

        if '4channel.org' in url or '4chan.org' in url:
            self.api = url + '.json'
            raise NotImplementedError
        elif 'desuarchive' in url:
            self.api = f'https://desuarchive.org/_/api/chan/thread?board={self.board}&num={self.thread}'
        else:
            raise Exception

        if not os.path.isdir(TMP_PATH):
            os.mkdir(TMP_PATH)
        if not os.path.isdir(OUT_PATH):
            os.mkdir(OUT_PATH)

    def watch(self):
        while True:
            self.download()
            time.sleep(60)

    def download(self):
        data = requests.get(self.api).json()
        data = data[list(data)[0]]
        errors = []
        for p in tqdm(data['posts'].values()):
            if p['media'] is None:
                continue
            name = p['media']['media_filename']
            if '[sound' in name:
                fname = name.split('[sound=')[0] + '_' + p["num"]
                fname = fname[1:] if fname.startswith('_') else fname
                surl = name.split('[sound=')[1].split('].')[0]
                try:
                    if not os.path.isfile(os.path.join(OUT_PATH, f'{fname}.{OUT_FORMAT}')):
                        sound_tmp = os.path.join(TMP_PATH, fname+'_s.'+surl.split('.')[-1])
                        pic_temp = os.path.join(TMP_PATH, fname+'._p'+name.split('.')[-1])
                        with open(sound_tmp, 'wb') as sound, open(pic_temp, 'wb') as pic:
                            surl = 'https://' + surl if not surl.startswith('http') else surl
                            sound.write(requests.get(urllib.parse.unquote(surl)).content)
                            pic.write(requests.get(p['media']['media_link']).content)
                        if name.split('.')[-1] == 'webm':
                            subprocess.run(['ffmpeg', '-stream_loop', '-1', '-i', f'{pic_temp}', '-i', f'{sound_tmp}',
                                            '-strict' , '-2', '-c:v', 'libx264', '-c:a', 'copy', '-shortest',
                                            os.path.join(OUT_PATH, f'{fname}.{OUT_FORMAT}')])
                        elif name.split('.')[-1] == 'gif':
                            subprocess.run(['ffmpeg', '-ignore_loop', '0', '-i', f'{pic_temp}', '-i', f'{sound_tmp}',
                                            '-strict' , '-2', '-c:v', 'libx264', '-c:a', 'copy', '-shortest',
                                            os.path.join(OUT_PATH, f'{fname}.{OUT_FORMAT}')])
                        else:
                            subprocess.run(['ffmpeg', '-loop', '0', '-i', f'{pic_temp}', '-i', f'{sound_tmp}',
                                            '-strict', '-2', '-c:v', 'vp9', '-c:a', 'copy',
                                            os.path.join(OUT_PATH, f'{fname}.{OUT_FORMAT}')])
                except BaseException:
                    errors.append(p["num"])
        print('failed posts: ', errors)


if __name__ == '__main__':
    c = Chan(args.url)
    if not args.watch:
        c.download()
    else:
        c.watch()
