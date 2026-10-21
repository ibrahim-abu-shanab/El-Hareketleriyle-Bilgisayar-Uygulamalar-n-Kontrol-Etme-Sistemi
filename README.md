# JestKontrol — El Hareketiyle Bilgisayar Uygulamalarını Kontrol Etme Sistemi

Fırat Üniversitesi · Bilgisayar Mühendisliği Tasarımı projesi.

Standart bir web kamerasından elin 21 eklem noktası gerçek zamanlı izlenir. El hareketleri fare imlecine, tıklamaya, sürükle-bırakmaya, sayfa kaydırmaya ve sistem ses düzeyine dönüştürülür. Görüntü yalnızca bu bilgisayarda işlenir; kaydedilmez ve ağa gönderilmez.

## Özellikler

| Gereksinim | Karşılığı |
|---|---|
| F1 Kamera akışı | Kamera seçimi, aynalama, çözünürlük (varsayılan 640×480) |
| F2 El tespiti | MediaPipe Hands, 21 nokta; el kaybolunca imleç yerinde kalır |
| F3 İmleç | İşaret parmağı ucu, aktif alan ve üstel yumuşatma |
| F4 Sol tık / sürükle | Başparmak + işaret; 0,3 sn tutunca sürükleme başlar |
| F5 Sağ tık | Başparmak + orta parmak |
| F6 Kaydırma | İşaret ve orta parmak kalkık, el yukarı/aşağı |
| F7 Ses | Başparmak–işaret mesafesi (pycaw) |
| F8 Duraklat / acil durdurma | Yumruk 1 sn; değiştirilebilir genel kısayol (varsayılan `Ctrl+Alt+G`) |
| F9 Arayüz | Kontrol paneli, hareketler, ayarlar (otomatik kayıt), Türkçe/English, koyu/açık tema, mini pencere |
| F10 Test ve performans | FPS testi ve tıklama doğruluk testi, geçmiş, CSV dışa aktarma |

## Gereksinimler

- Windows 10 veya 11
- Python 3.12
- Bir web kamerası

## Kurulum

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Çalıştırma

```powershell
python -m jestkontrol                                   # grafik arayüz
python -m jestkontrol --headless --mode mouse --debug   # pencere olmadan; FPS ve hareketleri konsola yazar
```

`--mode` için `mouse`, `scroll` veya `volume` seçilebilir. Ayarlar ve test geçmişi `%APPDATA%\JestKontrol` klasöründe tutulur.

### Hareketler

| Hareket | Nasıl yapılır | Mod |
|---|---|---|
| İmleç hareketi | İşaret parmağını kaldırın; parmak ucu imleci taşır | Fare |
| Sol tık | Başparmak ile işaret parmağının uçlarını kısa süre birleştirin | Fare |
| Sürükle ve bırak | Sol tık hareketini tutun, eli taşıyın, parmakları ayırın | Fare |
| Sağ tık | Başparmak ile orta parmağın uçlarını kısa süre birleştirin | Fare |
| Kaydırma | İşaret ve orta parmak kalkıkken eli yukarı/aşağı taşıyın | Kaydırma |
| Ses düzeyi | Başparmak–işaret mesafesi sesi belirler | Ses |
| Duraklat / devam | Yumruk yapıp 1 saniye tutun | Hepsi |

Eşik değerleri (tıklama eşiği, bekleme süresi, kaydırma hızı vb.) Ayarlar sayfasından değiştirilebilir. Varsayılanlar henüz gerçek kullanıcılarla ayarlanmamıştır.

### Kısayollar

| Tuş | İşlev |
|---|---|
| `Ctrl+Alt+G` (Ayarlar'dan değiştirilebilir) | Her uygulamada sistemi başlatır / durdurur |
| `Ctrl+1` … `Ctrl+5` | Sayfalar arası geçiş |
| `Ctrl+M` | Mini pencere |
| `Esc` | Çalışan testi durdurur |

## Testler

```powershell
python -m pytest
```

Birim testleri kamera gerektirmez. Her dış bağımlılık (kamera, MediaPipe, fare, ses, kısayol) sahte bir nesneyle değiştirilir.

## Mimari

Clean Architecture; bağımlılıklar yalnızca içe doğrudur ve `tests/test_architecture.py` bunu denetler.

```
src/jestkontrol/
  domain/          saf Python: el noktaları, geometri, hareket olayları, ayarlar, kısayol
  application/     kullanım senaryoları: hareket tanıyıcılar, motor, çalışma döngüsü, testler, i18n, port arayüzleri
  infrastructure/  port uygulamaları: OpenCV, MediaPipe, PyAutoGUI, pycaw, Win32 kısayol, JSON/CSV
  ui/              CustomTkinter arayüzü (yalnızca application/domain kullanır)
  bootstrap.py     bileşenleri birbirine bağlayan tek yer
tests/             pytest
design/            arayüz tasarımları ve tasarım değişkenleri (tokens.json)
```

Yeni bir hareket eklemek için `application/recognizers/` altına bir tanıyıcı ve `application/actions.py` içine bir işleyici eklemek yeterlidir.

## Ekip

- Muhammed Hammud Elalavi (takım kaptanı)
- Yasir Elkeleş
- İbrahim Ebu Şeneb
