"""New original synthesized temp score/SFX; no sampled or downloaded audio."""
from pathlib import Path
import numpy as np
from scipy.io import wavfile
import subprocess, json
ROOT=Path(__file__).parent
SR=48000
rng=np.random.default_rng(83127)

def freq(midi): return 440*2**((midi-69)/12)
def mallet(midi,duration=0.65):
    t=np.arange(int(SR*duration))/SR; f=freq(midi)
    a=np.minimum(t/.006,1)
    return a*(np.sin(2*np.pi*f*t)*np.exp(-t/0.24)+.20*np.sin(2*np.pi*f*2*t)*np.exp(-t/.11)+.055*np.sin(2*np.pi*f*3*t)*np.exp(-t/.08))
def bass(midi,duration):
    t=np.arange(int(SR*duration))/SR
    env=np.minimum(t/.028,1)*np.minimum((duration-t)/.13,1)*np.exp(-t/1.6)
    return env*(np.sin(2*np.pi*freq(midi)*t)+.12*np.sin(2*np.pi*2*freq(midi)*t))
def pad(notes,duration):
    t=np.arange(int(SR*duration))/SR
    env=np.sin(np.pi*np.minimum(t/.28,1)/2)*np.sin(np.pi*np.minimum((duration-t)/.45,1)/2)
    return sum(np.sin(2*np.pi*freq(n)*t) for n in notes)/len(notes)*env

def place(buf,sound,start,amp=1,pan=0,wrap=False):
    i=int(start*SR); gains=np.sqrt([(1-pan)/2,(1+pan)/2]); sig=sound[:,None]*np.array(gains)[None,:]*amp
    if wrap:
        idx=(np.arange(len(sig))+i)%len(buf)
        np.add.at(buf,idx,sig)
    else:
        n=min(len(sig),len(buf)-i)
        if n>0: buf[i:i+n]+=sig[:n]

def raw_write(stem,x):
    p=ROOT/(stem+'_raw.wav'); wavfile.write(p,SR,x.astype(np.float32)); return p

def finish(stem,x,lufs=-25,peak=-9):
    raw=raw_write(stem,x)
    wav=ROOT/(stem+'.wav'); mp3=ROOT/(stem+'.mp3')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-af',f'loudnorm=I={lufs-min(0,peak+9)}:TP={max(-9,peak)}:LRA=7,volume={min(0,peak+9)}dB','-ar',str(SR),'-c:a','pcm_s16le',str(wav)],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-c:a','libmp3lame','-b:a','192k',str(mp3)],check=True)
    raw.unlink()
    sr,data=wavfile.read(wav); y=data.astype(np.float64)/32768
    return {'wav':wav.name,'mp3':mp3.name,'duration_seconds':len(y)/sr,'sample_rate_hz':sr,'channels':2,'sample_peak_dbfs':round(float(20*np.log10(max(np.max(np.abs(y)),1e-12))),2),'rms_dbfs':round(float(20*np.log10(max(np.sqrt(np.mean(y*y)),1e-12))),2)}

# 96 BPM, 16 bars, 40 seconds. Newly composed C-major pentatonic motifs.
beat=60/96; bar=4*beat; duration=16*bar
music=np.zeros((int(SR*duration),2))
chords=[([60,64,67],48),([57,60,64],45),([53,57,60],41),([55,60,62],43)]
motifs=[[(0,72),(.75,76),(1.5,79),(2.75,76)],[(.5,74),(1.5,72),(2.5,67)],[(0,69),(1,72),(2.25,76),(3,72)],[(.5,74),(1.5,67),(2.5,72)]]
for b in range(16):
    chord,root=chords[b%4]; start=b*bar
    place(music,pad(chord,bar),start,.075,pan=(-.14 if b%2 else .14),wrap=True)
    for off,note in [(0,root),(2,root+7)]: place(music,bass(note,beat*1.55),start+off*beat,.16,wrap=True)
    phrase=motifs[b%4]
    # Sparse second half, with a small original variation in bars 9–12.
    for j,(off,note) in enumerate(phrase):
        if b>=12 and j==1: continue
        if 8<=b<12 and j==len(phrase)-1: note+=12
        sig=mallet(note)
        place(music,sig,start+off*beat,.20,pan=.18*np.sin(b+j),wrap=True)
        place(music,sig,start+off*beat+.105,.025,pan=-.28,wrap=True)
    # Soft brush pulse; no sharp drums.
    for off in [1,3]:
        t=np.arange(int(SR*.10))/SR
        noise=rng.normal(0,1,len(t)); noise=np.convolve(noise,np.ones(7)/7,mode='same')
        brush=noise*np.sin(np.pi*t/.10)**2*np.exp(-t/.055)
        place(music,brush,start+off*beat,.020,pan=.2,wrap=True)
# A tiny endpoint taper avoids boundary clicks; MP3 decoder padding may affect loop joins.
n=int(.015*SR); music[:n]*=np.linspace(0,1,n)[:,None]; music[-n:]*=np.linspace(1,0,n)[:,None]
assets={}
assets['football_bed']=finish('original_temp_football_bed_40s',music)

# Rounded low ball tap, entirely synthesized.
t=np.arange(int(SR*.28))/SR
noise=rng.normal(0,1,len(t)); noise=np.convolve(noise,np.ones(31)/31,mode='same')
phase=2*np.pi*(145*t+42*.045*(1-np.exp(-t/.045)))
tap=(np.sin(phase)*np.exp(-t/.045)+.16*noise*np.exp(-t/.03))*np.minimum(t/.008,1)*np.minimum((.28-t)/.04,1)
x=np.zeros((int(SR*.45),2)); place(x,tap,.025,.5)
assets['ball_tap']=finish('original_temp_soft_ball_tap',x,-31,-16)
# Airy pass whoosh, lowpass-shaped noise and broad envelope.
t=np.arange(int(SR*.65))/SR; noise=rng.normal(0,1,len(t)); noise=np.convolve(noise,np.hanning(65)/np.hanning(65).sum(),mode='same')
whoosh=noise*np.sin(np.pi*t/.65)**2
x=np.zeros((int(SR*.8),2)); place(x,whoosh,.05,.6,pan=-.10)
assets['soft_whoosh']=finish('original_temp_soft_pass_whoosh',x,-32,-17)
# Gentle two-note success chime, no recognizable theme.
x=np.zeros((int(SR*1.4),2)); place(x,mallet(79,1.05),.05,.25,pan=-.12); place(x,mallet(84,.95),.26,.19,pan=.12)
assets['gentle_chime']=finish('original_temp_gentle_success_chime',x,-30,-16)
manifest={
 'status':'OPTIONAL ORIGINAL TEMP MUSIC/SFX — preview before enabling',
 'provenance':'Newly composed and synthesized for this project using local Python, NumPy/SciPy and FFmpeg. No samples, downloaded tracks, actor voices, or third-party compositions were used.',
 'rights_note':'Original generated project assets, provided for use in this project. This is not licensed Bluey/Peppa music and is not an imitation of either soundtrack. No third-party music license is bundled or required for source samples because none were used.',
 'default_enabled':False,
 'music':{'bpm':96,'bars':16,'key':'C major / pentatonic','loop_note':'40-second near-loop with 15 ms endpoint fades. Prefer WAV and a 30–80 ms crossfade for repeated playback. MP3 decoder padding can introduce a tiny gap.','intended_use':'Optional gentle instrumental bed during football silent montage. Keep off beneath narration unless separately reviewed; when needed reduce a further 8–12 dB.'},
 'quality_notes':['Technically checked for sample rate, duration, finite samples, clipping and encoded readability.','No human listening review has been completed; this is a synthesized temp score, not a professionally produced final soundtrack.','Quiet target levels and soft attacks; playback loudness depends on device and application volume.','Music targeted at -25 LUFS; effects targeted at -30 to -32 LUFS with peak limits -16 to -17 dBTP. Short-effect loudness estimates are approximate.'],
 'assets':assets
}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(ROOT/'README.txt').write_text('OPTIONAL ORIGINAL TEMP MUSIC/SFX\n\nNewly composed/synthesized for this project. No sampled/downloaded music, actor voices, or Bluey/Peppa themes. Default OFF; parent/user preview required before enabling.\n\nFiles: 40-second gentle instrumental football bed and 3 short effects (rounded ball tap, soft pass whoosh, gentle success chime), each as stereo 48 kHz WAV and 192 kb/s MP3.\n\nThe music is a simple newly composed pentatonic mallet motif over soft bass/pads with very quiet brush pulses at 96 BPM. It is a synthesized TEMP track, not a professionally produced final soundtrack.\n\nTechnical validation only; no listening review completed. Music target -25 LUFS. Effects target -30 to -32 LUFS. Audition at low volume. Use WAV and a 30–80 ms crossfade for looping. Keep off beneath narration until mix reviewed.\n\nSee manifest.json for precise file lengths/peaks and compose_original.py for complete reproducible provenance.\n')
print(json.dumps(manifest,indent=2))
