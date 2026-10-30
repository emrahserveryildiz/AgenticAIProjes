# Nöbetçi — Kurulum ve kullanım kılavuzu

## Kısaca ne işe yarar?

Nöbetçi, IT destek ekibinin gelen bir sorunu ilk incelemesini hızlandıran bir yardımcıdır. Talebi sınıflandırır, runbook'larda çözüm bilgisi arar, izin verilen salt okunur kontrolleri çalıştırır, kaynaklı bir yanıt ve gerekirse destek kaydı taslağı hazırlar. İnsan onayından sonra yerel demo kuyruğuna ticket ekler.

Uygulama VPN sorununu çözmez, kullanıcı hesabını değiştirmez veya gerçek ITSM sisteminde kayıt açmaz. Mevcut örnek sürümde servis ve cihaz verileri demo amaçlıdır.

## Nasıl çalışır?

```text
Talep → Triage → Plan → Runbook araması (RAG) → Salt okunur araçlar
      → Yanıt/ticket taslağı → Güvenlik kontrolü → İnsan onayı → Yerel kayıt
```

Örnek olarak, “VPN bağlanıyor ama kurum içi siteler açılmıyor” talebi VPN kategorisine ayrılır. Ajan VPN runbook'unda ilgili adımları arar, örnek VPN ve cihaz durumunu kontrol eder, sonra kaynaklarını belirterek yanıt verir. Ticket açılması gerekiyorsa önce taslağı gösterir; kullanıcı onaylarsa kaydı **uygulamanın yerel SQLite kuyruğuna** yazar.

## Teknolojiler ve projedeki görevleri

| Teknoloji / yaklaşım | Bu uygulamada ne yapıyor? | Neden kullanılıyor? |
|---|---|---|
| **Python** | Agent akışını, RAG'i, araçları ve veri katmanını çalıştırır. | Mantığı küçük, incelenebilir modüllere ayırır. |
| **Streamlit** | Destek masası, ticket kuyruğu, değerlendirme ve bilgi tabanı ekranlarını sunar. | Kurulum ve demo için web arayüzü sağlar. |
| **OpenAI Python SDK** | `OPENAI_API_KEY` tanımlıysa triage, planlama, yanıt ve araç çağrısı için modele istek gönderir. | Doğal dil taleplerini yapılandırılmış agent adımlarına dönüştürür. |
| **OpenAI embeddings** | Runbook ve kullanıcı sorusunu vektör temsiline çevirip semantik benzerlik araması sağlar. | Aynı kelimeler kullanılmasa bile ilgili runbook bölümünü bulmaya yardım eder. |
| **RAG (BM25 + embedding)** | Markdown runbook'larını başlıklara göre bölümlere ayırır; kelime eşleşmesi ve semantik benzerliği birleştirip kaynaklı bölümler getirir. | Yanıtların kurum yönergelerine dayanmasını ve kaynağın gösterilmesini sağlar. Embedding başarısızsa yerel lexical arama devam eder. |
| **Multi-agent orchestration** | Triage, Planner, Retriever, Diagnostics, Response ve Safety rollerini sıralı bir akışta çalıştırır. | Her adımın sorumluluğunu ve izini görünür kılar. |
| **Tool/function calling** | İzin listesinde bulunan servis durumu ve cihaz envanteri sorgularını modele kullandırır. | Ajanın yalnızca metin üretmek yerine veri almasını sağlar. Demo araçları salt okunurdur. |
| **SQLite hafıza ve audit** | Oturum konuşmalarını, düşük hassasiyetli hafıza kayıtlarını, demo ticket'larını ve agent izlerini yerelde tutar. | Oturum bağlamı ve sonradan incelenebilir işlem izi sağlar. |
| **Human-in-the-loop** | Ticket'ı yazmadan önce kullanıcıya taslağı onaylatır. | Ajanın tek başına kalıcı bir işlem yapmasını önler. |
| **Guardrails ve evaluation** | Kimlik bilgisi isteme/güvenlik korumasını kapatma önerilerini kontrol eder; örnek sorgularda retrieval başarımını ölçer. | Riskli önerileri azaltır, bilgi erişiminin kalitesini görünür kılar. |

## Örnek talep metinleri

### VPN bağlantısı

> LAP-1042 dizüstü bilgisayarımda VPN'e bağlanabiliyorum ama kurum içi siteler açılmıyor. Sorun bugün başladı; yeniden bağlanmayı denedim, düzelmedi. Servis ve cihaz durumunu kontrol et, ilgili runbook kaynağını göster ve sorun sürerse açılmak üzere bir destek bileti taslağı hazırla.

Beklenen akış: VPN sınıflandırması, VPN runbook araması, örnek servis/cihaz sorgusu, kaynaklı yanıt ve onay bekleyen ticket taslağı.

### Parola değişikliğinden sonra VPN

> Parolamı değiştirdikten sonra VPN bağlanmıyor. Kayıtlı kimlik bilgileriyle ilgili güvenli adımları açıkla; benden parola veya doğrulama kodu isteme.

Beklenen akış: VPN runbook'undan ilgili adımlar ve gizli bilgi istememe kontrolü.

### Şüpheli e-posta

> Ekinde dosya olan şüpheli bir e-posta aldım. Ek dosyayı açmalı mıyım? Güvenli bildirim adımını ve gerekiyorsa ticket taslağını hazırla.

Beklenen akış: Güvenlik/Email yönlendirmesi, phishing runbook kanıtı, eki açmama uyarısı ve gerekirse onaylı eskalasyon.

### Uygulamaya erişim

> İç uygulamada erişim reddedildi hatası alıyorum. Erişim grubumu doğrudan değiştirme; gereken bilgileri ve yönetici onayına sunulacak adımları anlat.

Beklenen akış: Access runbook'u, doğrudan yetki değişikliğini reddetme, eksik bilgi sorusu veya onay talebi taslağı.

## Windows'ta yerel demo kurulumu

1. ZIP'i ayıklayın ve PowerShell'i proje klasöründe açın.
2. Aşağıdaki komutlarla sanal ortam oluşturup bağımlılıkları yükleyin:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

3. `.env` dosyasını açıp `OPENAI_API_KEY` alanına **bu uygulama/kişi için yetkilendirilmiş anahtarı** yerel olarak ekleyin. Anahtarı kaynak koda, `.env.example` dosyasına, Git'e, ZIP'e, e-posta eki veya sohbet mesajına koymayın.
4. Uygulamayı başlatın:

```powershell
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` adresi açılır. Anahtar tanımlıysa arayüz model bağlantısını gösterir. API erişimi yoksa uygulama yerel demo moduna dönebilir.

## Şirket içinde paylaşım ve API anahtarı

**ZIP dosyasının içinde API anahtarı bulunmaz.** Tek bir kişisel anahtarı tüm çalışanlarla paylaşmayın. OpenAI belgeleri anahtarları kaynak koda/repository'ye koymamak, secret manager veya ortam değişkeniyle uygulamaya vermek ve ekip üyelerine ayrı anahtarlar sağlamak yönünde öneri veriyor. Şirket sunucusunda merkezi dağıtım yapılacaksa kurumsal yöneticinin yönettiği, kapsamı ve kullanım takibi belirlenmiş bir service account anahtarı bir secret manager üzerinden sunucuya verilmelidir. Uygulamayı her çalışan yerelde çalıştıracaksa şirketin onayladığı kullanıcı/anahtar modelini kullanın.

API anahtarı tanımlandığında runbook içeriği embedding oluşturmak için, kullanıcının talebi ve bulunan runbook parçaları da model adımları için OpenAI API'ye gönderilir. Şirket verisini yüklemeden önce kurumunuzun veri sınıflandırma ve yapay zekâ kullanım kurallarını uygulayın. Kullanım ve harcama eşiklerini OpenAI Platform'dan izleyin.

## Demo ile gerçek sistem arasındaki fark

- VPN/e-posta servis durumu ve cihaz envanteri `data/` içindeki örnek verilerden okunur.
- Ticket, harici ticket sistemine değil yerel SQLite veritabanına yazılır.
- Bu pakette ServiceNow, Jira Service Management, Active Directory, VPN gateway veya gerçek endpoint yönetimi bağlantısı yoktur.
- Gerçek entegrasyon için şirket kimlik doğrulaması, erişim yetkileri, servis API'leri, veri saklama politikası, gözlemleme ve güvenlik incelemesi ayrıca tasarlanmalıdır.

## Teslim içeriği

- Kaynak kodu ve modüler agent akışı
- `README.md`: kısa proje tanımı ve kurulum
- Bu dosya: teknoloji açıklaması, şirket içi kullanım ve örnek talepler
- `screenshots/`: uygulama ekran görüntüleri
- `.env.example`: boş anahtar şablonu

