# Hafta 3 - Görüntü İşleme ve El Tespiti

**Sorumlu:** İbrahim Ebu Şeneb

## Yapılan geliştirme
- OpenCV ile web kamerasından görüntü alma (640 x 480)
- MediaPipe Hand Landmarker ile tek elin 21 noktasını tespit etme
- El iskeletini görüntü üzerine çizme
- İşaret parmağı ucu (8 numaralı nokta) piksel koordinatlarını gösterme
- FPS değerini görüntüleme

## Kurulum (Windows PowerShell, Python 3.11)
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe hand_tracking.py
```
İlk çalıştırmada Google MediaPipe resmi model dosyası indirilir. İnternet bağlantısı gereklidir. Programdan çıkmak için **Q** tuşuna basın.

## Henüz yapılmayanlar
Fare kontrolü, gesture algoritmaları ve GUI entegrasyonu bu modülün kapsamında değildir. Gerçek kamera / FPS test sonucu bilgisayarda doğrulanmalıdır.

## Kaynak
https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python
