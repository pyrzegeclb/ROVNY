# ROVNY Harness v0.2

**Yerel çalışan, modelden bağımsız AI kodlama çalışma alanı.**

React + TypeScript arayüz, Python backend. Tarayıcıda localhost üzerinden çalışır. Tauri veya Electron gerektirmez. Ollama ve OpenAI uyumlu yerel sunucular için API anahtarı gerekmez.

## Yeni sohbet ekranı

Uygulama artık geniş bir sohbet ekranıyla açılır. Proje açmadan da normal konuşabilirsiniz. **Sohbet** normal yanıt verir; **Plan** dosya değişikliklerini inceleme için hazırlar. Sohbet mesajları kendiliğinden dosya değiştirmez.

- Enter gönderir, Shift+Enter yeni satır açar.
- Yanıtlar yazıldıkça görünür; kare düğme üretimi durdurur.
- **Yeni sohbet** ayrı konuşma açar; sol listeden önceki konuşmalara dönülür.
- Son 20 sohbet ve sohbet başına 80 mesaj tarayıcıda, proje bazında saklanır.
- Dosyaya tıklayınca editör açılır; **Sohbeti genişlet** geniş sohbet alanına döner.
- Çok uzun geçmişin sadece son kısmı modele gönderilir; bunun için ekranda bilgi gösterilir.

Bu bilgisayarda **Qwen3 14B** indirildi ve bağlandı (yaklaşık 9,3 GB). CPU/GPU birlikte kullanıldığı için ilk küçük modelden daha yavaştır. Sonraki açılışlarda önceki `ROVNY-LLM-Baslat.ps1` başlatıcısı aynı kurulumla çalışır. Başka bir bilgisayarda `ollama pull qwen3:14b` komutuyla modeli indirin ve Ayarlar'da model adını seçin.

## Windows'ta hızlı başlangıç

Python 3.11+ ve Node.js 22.12+ kurulu olmalı. ZIP'i bir klasöre çıkarın; PowerShell'i `rovny-harness` klasöründe açın:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
cd frontend
npm ci
npm run build
cd ..\backend
..\.venv\Scripts\python.exe -m rovny
```

Backend'in yazdırdığı `http://127.0.0.1:8765/#token=...` adresini açın. Bu oturum adresini paylaşmayın. **Open project** ile proje klasörünüzün tam yolunu girin.

Teslim edilen ZIP'in içinde derlenmiş `frontend/dist` de var. Sadece çalıştırmak için Node/npm adımlarını atlayıp sanal ortam ve Python bağımlılıklarını kurduktan sonra backend'i başlatabilirsiniz. Kaynakta değişiklik yaparsanız arayüzü yeniden derleyin.

Sonraki açılışlarda depo kökünden:

```powershell
.\scripts\start.ps1
```

PowerShell yürütme ilkesi betiği engellerse politikayı değiştirmek yerine yukarıdaki doğrudan Python başlatma komutunu kullanabilirsiniz. macOS/Linux yönergeleri [README](README.md) içinde.

## Model olmadan deneyin

1. `examples/hello-project` klasörünü açın.
2. Sol menüden **Settings**, sağlayıcı olarak **Demo**, ardından **Save settings** seçin.
3. Agent alanına bir istek yazıp oka basın.
4. `ROVNY_DEMO.md` için diff oluşur. **Apply** dosyayı oluşturur; **Revert** önceki hâle döndürür.

Demo modu sabit bir örnek üretir; gerçek bir model değildir.

## Yerel model bağlama

Ollama kuruluysa:

```sh
ollama pull qwen2.5-coder:7b
```

Ollama sunucusunu çalıştırın. Ayarlarda **Ollama**, adres `http://127.0.0.1:11434`, model `qwen2.5-coder:7b` seçin. Modeli donanımınıza göre değiştirebilirsiniz.

LM Studio / llama.cpp gibi sunucular için **OpenAI-compatible**, örneğin `http://127.0.0.1:1234/v1` ve sunucunuzdaki model kimliğini kullanın. JSON çıktı desteklenmeli.

## Kullanım

- Dosya ağacındaki kutular, modele gönderilecek dosyaları seçer. Dosyaya tıklamak editörde açar.
- Editörde **Preview save** değişikliği plana dönüştürür. Diske yazmak için planı **Apply** ile uygulayın.
- Agent, bir istekten çoklu dosya değişiklik planı üretir; kendi kendine uygulamaz veya komut çalıştırmaz.
- **Snapshots** tam yedek oluşturur ve geri yükler. Geri yükleme öncesinde mevcut hâlin kurtarma yedeği alınır.
- **Terminal**, JSON argüman listesi bekler: `["git", "status", "--short"]`. Her komut için onay kutusunu işaretleyin. Komutlar normal işletim sistemi yetkilerinizle çalışır; bir güvenlik sandbox'ı değildir.
- Dosyalar önizlemeden sonra değişmişse apply/revert reddedilir; böylece eski plan yeni içeriği ezmez.

v0.2 sınırları ve mimari [README](README.md), güvenlik sınırları [SECURITY](docs/SECURITY.md), yapılan kontroller [VALIDATION](docs/VALIDATION.md) içinde. MIT lisanslıdır.
