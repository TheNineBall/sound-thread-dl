import os, urllib
import requests
import argparse
import time
import subprocess
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("url", help='The url of the thread.')
parser.add_argument("--watch", action='store_true', help='Watch for new posts and download them.')
parser.add_argument("--encode", choices=['libx264', 'h264_nven', 'vp9'], default='libx264',
                    help='libx264:mkv slow, h264_nven: mkv fast, vp9: webm')
parser.add_argument("--out", default=None, help='Output path.')
args = parser.parse_args()

TMP_PATH = 'temp'
OUT_FORMAT = {'libx264': 'mkv', 'h264_nven': 'mkv', 'vp9': 'webm'}[args.encode]


class Chan:
    def __init__(self, url, out):
        self.board = 'a'
        self.thread = 1

        url = url.split('#')[0]
        url = url[:-1] if url.endswith('/') else url
        self.thread = url.split('/')[-1]
        self.board = url.split('/')[-3]
        self.out = out if out is not None else self.thread

        if '4channel.org' in url or '4chan.org' in url:
            self.api = url + '.json'
            self.start = self.fourchannel
        elif 'desuarchive' in url:
            self.api = f'https://desuarchive.org/_/api/chan/thread?board={self.board}&num={self.thread}'
            self.start = self.desuarchive
        else:
            raise NotImplementedError

        if not os.path.isdir(TMP_PATH):
            os.mkdir(TMP_PATH)
        if not os.path.isdir(self.out):
            os.mkdir(self.out)

    def watch(self):
        while True:
            self.start()
            time.sleep(60)

    def fourchannel(self):
        data = requests.get(self.api).json()
        errors = []
        for p in tqdm(data['posts']):
            if not 'filename' in p:
                continue
            url = f'http://i.4cdn.org/{self.board}/{str(p["tim"]) + p["ext"]}'
            try:
                self.download(p['filename'] + p['ext'], url, str(p['no']))
            except BaseException:
                errors.append(str(p['no']))
        print(errors)

    def desuarchive(self):
        data = requests.get(self.api).json()
        data = data[list(data)[0]]
        data['posts'][data['op']['num']] = data['op']
        errors = []
        for p in tqdm(data['posts'].values()):
            if p['media'] is None:
                continue
            try:
                self.download(p['media']['media_filename'], p['media']['media_link'], p["num"])
            except BaseException:
                errors.append(str(p["num"]))
        print(errors)

    def download(self, media_name, media_link, p_num):
        if '[sound' in media_name:
            fname = media_name.split('[sound=')[0] + '_' + p_num
            fname = fname[1:] if fname.startswith('_') else fname
            surl = media_name.split('[sound=')[1].split('].')[0]
            if not os.path.isfile(os.path.join(self.out, f'{fname}.{OUT_FORMAT}')):
                sound_tmp = os.path.join(TMP_PATH, fname+'_s.'+surl.split('.')[-1])
                pic_temp = os.path.join(TMP_PATH, fname+'_p.'+media_name.split('.')[-1])
                with open(sound_tmp, 'wb') as sound, open(pic_temp, 'wb') as pic:
                    surl = 'https://' + surl if not surl.startswith('http') else surl
                    sound.write(requests.get(urllib.parse.unquote(surl)).content)
                    pic.write(requests.get(media_link).content)

                if media_name.split('.')[-1] == 'webm':
                    subprocess.run(['ffmpeg', '-stream_loop', '-1', '-i', f'{pic_temp}', '-i', f'{sound_tmp}',
                                    '-strict' , '-2', '-c:v', args.encode, '-c:a', 'copy', '-shortest',
                                    os.path.join(self.out, f'{fname}.{OUT_FORMAT}')])
                elif media_name.split('.')[-1] == 'gif':
                    subprocess.run(['ffmpeg', '-ignore_loop', '0', '-i', f'{pic_temp}', '-i', f'{sound_tmp}',
                                    '-strict' , '-2', '-c:v', args.encode, '-c:a', 'copy', '-shortest',
                                    os.path.join(self.out, f'{fname}.{OUT_FORMAT}')])
                else:
                    subprocess.run(['ffmpeg', '-loop', '0', '-i', f'{pic_temp}', '-i', f'{sound_tmp}',
                                    '-strict', '-2', '-c:v', args.encode, '-vcodec', 'mpeg4', '-c:a', 'copy',
                                    os.path.join(self.out, f'{fname}.{OUT_FORMAT}')])


if __name__ == '__main__':
    c = Chan(args.url, args.out)
    if OUT_FORMAT == 'webm':
        raise NotImplementedError
    if not args.watch:
        c.start()
    else:
        c.watch()
