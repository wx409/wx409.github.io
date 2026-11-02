import sys, subprocess
from pathlib import Path
import numpy as np, av, cv2, imageio_ffmpeg
sys.stdout.reconfigure(encoding='utf-8')
VID = r'H:\王晰巡演素材存档\现场录制视频\五巡\大疆录制上海场20251121\吾巡演上海站_20251121195344_0028_床前明月光_暗潮涌动_我真的受伤了.MP4'
OUT = Path(r'E:\wx\video_clip1')
T0, DUR = 296.0, 24.0
OUTW, OUTH, CROPW = 1080, 1920, 608

cap = cv2.VideoCapture(VID)
cap.set(cv2.CAP_PROP_POS_MSEC, T0*1000)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
writer = cv2.VideoWriter(str(OUT/'_ancho_raw.mp4'), cv2.VideoWriter_fourcc(*'mp4v'), fps, (OUTW, OUTH))
centers = []
frames = []
for i in range(int(DUR*fps)):
    ok, fr = cap.read()
    if not ok: break
    gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, 1.15, 5, minSize=(60,60))
    h, w = fr.shape[:2]
    if len(faces):
        x,y,fw,fh = max(faces, key=lambda f: f[2]*f[3])
        centers.append(x+fw/2)
    else:
        centers.append(np.nan)
    frames.append((fr, w, h))
cap.release()
centers = np.array(centers, dtype=float)
idx = np.arange(len(centers)); good = ~np.isnan(centers)
centers = np.interp(idx, idx[good], centers[good]) if good.any() else np.full(len(centers), frames[0][1]/2)
k=45; sm = np.convolve(np.pad(centers,(k//2,k//2),mode='edge'), np.ones(k)/k, mode='valid')
half = CROPW//2
sm = np.clip(sm, half, frames[0][1]-half)
for (fr,w,h), cx in zip(frames, sm):
    x0 = int(max(0,min(w-CROPW, cx-half)))
    crop = fr[:, x0:x0+CROPW]
    writer.write(cv2.resize(crop,(OUTW,OUTH),interpolation=cv2.INTER_LANCZOS4))
writer.release()
print('帧', len(frames), '| 检出人脸', int(good.sum()))

# 音频：从原视频 296-320s
c = av.open(VID); a = c.streams.audio[0]
c.seek(int(T0*1e6), stream=a)
buf=[]
for fr in c.decode(audio=0):
    arr = fr.to_ndarray(); buf.append(arr.mean(axis=0) if arr.ndim>1 else arr)
x = np.concatenate(buf).astype('float32')[:int(DUR*a.rate)]
import soundfile as sf
sf.write(str(OUT/'_ancho_audio.wav'), x, a.rate)
ff = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff,'-y','-i',str(OUT/'_ancho_raw.mp4'),'-i',str(OUT/'_ancho_audio.wav'),
                '-c:v','libx264','-preset','medium','-crf','20','-c:a','aac','-b:a','192k','-shortest',
                str(OUT/'07_暗潮涌动_预览_296s.mp4')], capture_output=True)
print('完成 07_暗潮涌动_预览_296s.mp4')
