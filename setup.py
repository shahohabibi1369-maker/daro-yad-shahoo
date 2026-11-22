import os, re, sys, wave, struct, math, shutil
from PIL import Image, ImageDraw

res = 'android/app/src/main/res'

# ---- launcher icons ----
img = Image.open('icon.png').convert('RGB')
for d, s in {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}.items():
    p = f'{res}/mipmap-{d}'
    os.makedirs(p, exist_ok=True)
    r = img.resize((s, s), Image.LANCZOS)
    for n in ('ic_launcher', 'ic_launcher_round', 'ic_launcher_foreground'):
        r.save(f'{p}/{n}.png')
shutil.rmtree(f'{res}/mipmap-anydpi-v26', ignore_errors=True)

# ---- small notification icon ----
os.makedirs(f'{res}/drawable', exist_ok=True)
layer = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
ImageDraw.Draw(layer).rounded_rectangle((8, 30, 88, 66), radius=18, fill=(255, 255, 255, 255))
layer.rotate(45, resample=Image.BICUBIC).save(f'{res}/drawable/ic_stat_dose.png')

# ---- alarm sound (about 12 seconds of beeps) ----
os.makedirs(f'{res}/raw', exist_ok=True)
sr = 22050
frames = []
for rep in range(8):
    for k in range(3):
        n = int(sr * 0.18)
        for i in range(n):
            frames.append(int(14000 * math.sin(2 * math.pi * 988 * i / sr) * (1 - 0.3 * i / n)))
        frames += [0] * int(sr * 0.08)
    frames += [0] * int(sr * 0.7)
w = wave.open(f'{res}/raw/alarm.wav', 'wb')
w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
w.writeframes(b''.join(struct.pack('<h', x) for x in frames))
w.close()

# ---- manifest: permissions (no USE_EXACT_ALARM: Play allows it only for clock/calendar apps) ----
mp = 'android/app/src/main/AndroidManifest.xml'
s = open(mp, encoding='utf-8').read()
if 'xmlns:tools' not in s:
    s = s.replace('<manifest ', '<manifest xmlns:tools="http://schemas.android.com/tools" ', 1)
names = ['SCHEDULE_EXACT_ALARM', 'POST_NOTIFICATIONS', 'VIBRATE', 'RECEIVE_BOOT_COMPLETED', 'CAMERA', 'WAKE_LOCK']
perms = ''.join(f'    <uses-permission android:name="android.permission.{p}"/>\n' for p in names)
perms += '    <uses-permission android:name="android.permission.USE_EXACT_ALARM" tools:node="remove"/>\n'
perms += '    <uses-feature android:name="android.hardware.camera" android:required="false"/>\n'
if '<application' not in s:
    sys.exit('manifest: <application not found')
s = s.replace('<application', perms + '    <application', 1)
s = re.sub(r'<activity\b', '<activity android:showWhenLocked="true" android:turnScreenOn="true"', s, count=1)
open(mp, 'w', encoding='utf-8').write(s)

# ---- gradle: version + signing ----
gp = 'android/app/build.gradle'
g = open(gp, encoding='utf-8').read()
run = os.environ.get('GITHUB_RUN_NUMBER', '1')
g, n1 = re.subn(r'versionCode\s+\d+', f'versionCode {run}', g, count=1)
g, n2 = re.subn(r'versionName\s+"[^"]*"', f'versionName "1.0.{run}"', g, count=1)
if not (n1 and n2):
    sys.exit('gradle: versionCode/versionName pattern not found')
if os.environ.get('KS_FILE'):
    sign = """signingConfigs {
        release {
            storeFile file(System.getenv('KS_FILE'))
            storePassword System.getenv('KS_PASS')
            keyAlias 'upload'
            keyPassword System.getenv('KS_PASS')
            storeType 'pkcs12'
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release"""
    g, n3 = re.subn(r'buildTypes\s*\{\s*release\s*\{', lambda m: sign, g, count=1)
    if not n3:
        sys.exit('gradle: buildTypes/release pattern not found')
open(gp, 'w', encoding='utf-8').write(g)
print('customize done, versionCode', run)
