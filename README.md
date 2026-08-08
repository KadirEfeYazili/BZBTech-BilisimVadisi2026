# BZB Tech - Katılım Bankacılığı Kampanya Analiz Platformu

Türkiye'deki katılım bankalarının kamuya açık kampanya sayfalarından veri
toplayan, bu veriyi normalize ederek karşılaştırılabilir hâle getiren ve web
arayüzü üzerinden sunan analiz platformu.

> **TEKNOFEST 2026 — Bilişim Vadisi / İkinci Senaryo** · Takım: **BZBTech**

---

## Takım

| Üye | Rol | LinkedIn |
|---|---|---|
| <img src="https://media.licdn.com/dms/image/v2/D4D03AQHHAEqtTBJgCA/profile-displayphoto-shrink_800_800/B4DZWgOnQ3HYAc-/0/1742149941290?e=1787788800&v=beta&t=BhIZVGvM5rTp75XCihiz9u5MgwWPWVklTDAYdm5xAb8" width="64" height="64" alt="Muhammed Zeyd Kurt"><br>**Muhammed Zeyd KURT** | Takım Kaptanı | [linkedin.com/in/zeyd-kurt](https://www.linkedin.com/in/zeyd-kurt/) |
| <img src="https://media.licdn.com/dms/image/v2/D4D03AQEduYy1Z3l8RQ/profile-displayphoto-crop_800_800/B4DZ2xJ52PKQAI-/0/1776793657981?e=1787788800&v=beta&t=nfqyYAWStTic0Un7v0rXtbR-jyX_YFCVM2BcAwzOnLY" width="64" height="64" alt="Kadir Efe Yazılı"><br>**Kadir Efe YAZILI** | Üye | [linkedin.com/in/kadirefeyazili](https://www.linkedin.com/in/kadirefeyazili/) |
| <img src="https://media.licdn.com/dms/image/v2/D4D03AQGvAgSf8uY-8w/profile-displayphoto-crop_800_800/B4DZ_CkkMsGYAI-/0/1785675793642?e=1787788800&v=beta&t=YP1m9gJHxZ0Du5s6egVj4cgai4Mg9I0w-C11Tyqipj4" width="64" height="64" alt="Recep Buğra Aydemir"><br>**Recep Buğra AYDEMİR** | Üye | [linkedin.com/in/recep-bugra-aydemir](https://www.linkedin.com/in/recep-bugra-aydemir/) |
| <img src="https://media.licdn.com/dms/image/v2/D4D03AQEZKBMmGon8wA/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1728472512701?e=1787788800&v=beta&t=ayjXMcYo29C21bOnWc9mSiDA_-FwTham3eMfd9eMGik" width="64" height="64" alt="Batuhan Şenel"><br>**Batuhan ŞENEL** | Üye | [linkedin.com/in/batuhan-senell](https://www.linkedin.com/in/batuhan-senell/) |

---

## Problem

Katılım bankalarının kampanya bilgileri her kurumda farklı biçimde
yayımlanıyor. Analizimizde doğrulanan bazı örnekler:

- **Tarih yapısal bir alanda durmuyor.** Kampanya süresi, koşul metninin içinde
  serbest cümle olarak geçiyor ve en az **7 farklı biçimde** yazılıyor
  (`01.01.2026 - 31.12.2026`, `1-31 Ağustos 2026`, `10 Temmuz – 7 Ağustos 2026`,
  `Son Gün 31.12.2026` …). Bir bankada ise hiçbir kampanyada tarih bulunmuyor.
- **Sayı biçimi Türkçe.** `5.000` beş bin, `5,000` ise beştir — İngilizce
  konvansiyonun tersi.
- **Görünmez karakterler var.** Bir bankanın oran tablosu başlıklarında
  zero-width space ve non-breaking space bulunuyor; temizlenmezse kolon
  eşleştirmesi *sessizce* başarısız oluyor.
- **Biten kampanyalar siteden kalkıyor.** Kimi bankada sert HTTP 404 dönüyor,
  arşiv bulunmuyor. Ham veri saklanmazsa geri getirilemiyor.

Bu proje, dağınık ve kırılgan bu veriyi tek bir düzenli modele indirger;
her değerin **kaynağını** ve **çıkarım güvenilirliğini** kayıt altına alır.

## SPRINT 1 kapsamı

| Alan | Durum |
|---|---|
| Veritabanı şeması (9 tablo) + Alembic göçleri | ⬜ |
| 11 katılım bankası + terminoloji sözlüğü (seed) | ⬜ |
| Türkçe finansal metin normalizasyon kütüphanesi | ⬜ |
| Kazıma altyapısı (robots, soft-404, yeniden deneme, ham HTML arşivi) | ⬜ |
| İki banka scraper'ı (Emlak Katılım, Hayat Finans) | ⬜ |
| REST API (`/health`, `/banks`, `/campaigns`, `/stats`) | ⬜ |
| Web arayüzü (genel bakış + kampanya tablosu) | ⬜ |


---

## Kurulum

### Gereksinimler

| Bileşen | Sürüm | Not |
|---|---|---|
| Python | 3.11 veya üzeri | 3.12 önerilir |
| Node.js | 20 veya üzeri | yalnızca arayüz derlemesi için |
| npm | 10 veya üzeri | Node ile birlikte gelir |

Harici servis gerekmez: PostgreSQL, Redis veya mesaj kuyruğu yoktur.
Geliştirme veritabanı SQLite'tır ve dosya olarak tutulur.


Tüm bağımlılıkların tam listesi ve lisansları için:
[`LICENSES.md`](LICENSES.md)

---

## Ekran görüntüleri

_(Arayüz görselleri eklenecek)_

---

## Lisans

Bu proje [Apache License 2.0](LICENSE) ile lisanslanmıştır.

Bağımlılıkların lisans matrisi: [`LICENSES.md`](LICENSES.md). Projede copyleft
(GPL/AGPL) lisanslı bileşen kullanılmamıştır.

Banka adları ve markaları ilgili kurumlara aittir.
