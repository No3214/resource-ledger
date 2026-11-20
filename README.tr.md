# Resource Ledger — Kaynak Tüketim Defteri

Küçük işletmelerin aylık elektrik, su ve atık kayıtlarını çevrimdışı doğrulayan,
JSON veya Markdown özet üreten küçük bir araç.

[English documentation](README.md)

**Durum:** çalışan ilk sürüm. Gerçek işletme faturalarıyla saha doğrulaması henüz
yapılmadı. Karbon hesabı, maliyet hesabı, tasarruf iddiası veya sürdürülebilirlik
sertifikası üretmez. Hesap açmaz; ağ, telemetri ve API anahtarı kullanmaz.

## Hızlı başlangıç

Bu komutlar için Python **3.11 veya üzeri** ve Git gerekir. Depoyu indirip aracı
doğrudan çalıştırın; Python paketi kurmak gerekmez:

```sh
git clone https://github.com/No3214/resource-ledger.git
cd resource-ledger
python3 resource_ledger.py examples/synthetic.csv
python3 resource_ledger.py examples/synthetic.csv --format markdown
python3 resource_ledger.py examples/synthetic.csv --output rapor.json
python3 -m unittest discover -s tests -v
```

Python komutunuz `python` ise (Windows'ta yaygındır), `python3` yerine onu kullanın.

Örnekteki bütün işletmeler ve sayılar sentetiktir. Örnek, eksik ölçümleri ve sıfır
faaliyet sayısını bilerek içerir. `--output`, raporu önce hedef klasörde geçici
bir dosyaya tamamen yazar; sonra seçilen rapor yolunu atomik olarak değiştirir.
Yazma, diske aktarma veya değiştirme hatasında eski rapor korunur. Çıktı yolu bir
sembolik/sabit bağlantıysa bağlantının kendisi değiştirilir; bağlantının diğer
hedef dosyası düzenlenmez. `--output` ile girdi CSV'sinin üzerine yazmayı, sabit
bağlantıyla (hard link) verilse bile engeller. Kabuk yönlendirmesi (`>`), araç
başlamadan hedef dosyayı açar veya boşaltır; çıktıyı girdi CSV'sine yönlendirmeyin.
Özel kayıtlarınızı depoya yüklemeyin.

Standart çıktıya veya `--output` ile yazılan raporlar UTF-8 kullanır. Sonraki
görüntüleyiciyi UTF-8 okuyacak şekilde ayarlayın. Başarı kodu dönmeden standart
çıktı tamponu boşaltılır; yazma veya tampon boşaltma hatası çıkış kodu 3 verir.
Borular ve kabuk yönlendirmesi hata durumunda kısmi çıktı bırakabilir. Atomik
dosya değiştirme davranışı için yukarıdaki `--output` seçeneğini kullanın.

## Girdi sözleşmesi

```csv
month,site,metric,amount,unit,activity_count,activity_unit
2026-01,Ornek Kafe,electricity,250,kWh,500,cover
2026-01,Ornek Kafe,water,8.5,m3,500,cover
```

| Alan | Kural |
| --- | --- |
| `month` | Gerçek ay: `YYYY-MM`; yıl `0001`–`9999`. |
| `site` | Aynı saha için aynı yazımı kullanın. Büyük/küçük harf duyarlı; 1–100 karakter. Baş/son boşluk, denetim ve görünmez biçimlendirme karakterleri yasaktır. |
| `metric` | Tam olarak `electricity`, `water` veya `waste`. |
| `amount` | Negatif olmayan, sonlu, düz ondalık sayı. En fazla 24 karakter; `0`, `12`, `12.50` geçerlidir. Virgül, işaret, üslü yazım, `NaN` ve `Infinity` geçersizdir. |
| `unit` | Elektrik için `kWh`, su için `m3`, atık için `kg`. Birim dönüşümü yapılmaz. |
| `activity_count` | İsteğe bağlı, negatif olmayan tamsayı; en fazla 12 basamak. |
| `activity_unit` | Kullanıcının etiketi: harfle başlar; ASCII harf/rakam/alt çizgi/tire, en fazla 40 karakter. `occupied_room_night`, `cover`, `visitor` örnektir. |

`amount`, o sahanın **ilgili aydaki toplam tüketimi veya üretilen atık miktarıdır**;
kümülatif sayaç okuması değildir. Kümülatif sayaç okumalarını içe aktarmadan önce
dönem tüketimine dönüştürün. Araç bir sayının bu iki anlamdan hangisini taşıdığını
kendiliğinden ayırt edemez ve bu dönüşümü yapmaz.

İsteğe bağlı iki sütun birlikte eklenir veya birlikte kaldırılır. Sütunlar varsa
iki hücre de doldurulur veya ikisi de boş bırakılır. Aynı ay/sahanın bütün metrik
satırlarında faaliyet sayısı ve etiketi aynı olmalıdır; boşluk durumu da buna
dahildir. Faaliyet sayısı bütün ay/sahaya aittir, metrik başına tekrar toplanmaz.

Aynı ay/saha/metrik için ikinci satır hatadır. Aynı sayıyı taşısa bile yinelenen
ölçüm otomatik birleştirilmez. UTF-8, isteğe bağlı UTF-8 BOM ve tırnaklı CSV
desteklenir. Eksik/bilinmeyen/yinelenen başlık, boş satır, sütun sayısı uyuşmazlığı,
geçersiz UTF-8 ve bozuk tırnaklama hata verir.

## Özet nasıl okunur?

- İlk ve son kayıt ayı arasındaki bütün aylar ve girdide görülen bütün sahalar
  gösterilir. Eksik ay, saha veya ölçümün miktarı `null` kalır; sıfır yapılmaz.
- Aylık toplamlar yalnız **aynı metrik ve birimdeki kayıtları** toplar. Raporda
  kaç sahanın kayıt verdiği ve hangi bilinen sahaların eksik olduğu yazılır.
  Kısmi kayıt toplamı bütün işletmenin tüketim tahmini değildir.
- Girdide hiç bulunmayan bir saha veya tarih aralığı dışındaki ay keşfedilemez.
  Tamlık ifadesi yalnız girdide bilinen sahalar için geçerlidir.
- Normalleştirme `miktar / faaliyet sayısı` hesabıdır. Pozitif payda gerekir.
  Faaliyet eksikse `activity_not_provided`, sıfırsa `zero_activity_count`, ölçüm
  eksikse `missing_measurement` nedeni ile normalleştirilmiş değer `null` olur.
- Oranlar altı ondalığa `ROUND_HALF_UP` ile yuvarlanır. Miktarlar `Decimal` ile
  hesaplanır ve JSON'da metin olarak saklanır. Farklı faaliyet etiketleri için
  ortak bir portföy oranı hesaplanmaz. İyileşme, neden veya tasarruf çıkarılmaz.

Eşdeğer geçerli satırlar yeniden sıralansa da çıktı aynıdır. Etiketlerdeki HTML
ve açık Markdown sözdizimi kaçırılır. Bazı görüntüleyiciler düz URL ve e-posta
adreslerini kendileri tıklanabilir yapabilir; araç bu davranışı kapatmaz.
**CSV/Excel çıktısı yoktur.**
Sonradan tablo yazılımına aktaran bir uygulama formül enjeksiyonunu ayrıca ele
almalıdır. Araç raporları şifrelemez; dosyaların erişimini siz yönetirsiniz.

## Sınırlar ve sonuç kodları

En fazla 5 MiB girdi, 20.000 veri satırı, alan başına 256 karakter; yukarıdaki
alan sınırları ayrıca geçerlidir. Genişletilmiş rapor en fazla 20.000 saha/ay
dönemi ve 1.200 takvim ayı içerir.

| Çıkış kodu | Anlam |
| --- | --- |
| `0` | Doğrulama ve çıktı başarılı. |
| `2` | Geçersiz girdi/komut parametresi veya girdi dosyasının üzerine yazma denemesi. |
| `3` | Dosya okuma/yazma hatası. |

Doğrulama hatasında yarım rapor üretilmez; mevcut çıktı dosyası değişmez. Hata
mesajları ham veri satırlarını göstermez. `--output` eksik üst klasör oluşturmaz.

## Geliştirme

Testler standart Python kütüphanesini kullanır. CI, Linux'ta Python 3.11–3.15;
Windows ve macOS'ta Python 3.12 ile çalışır. Ayrı bir Python 3.11 işi wheel
paketini temiz bir sanal ortama kurar, kurulu komutları kaynak klasörünün dışında
çalıştırır ve çıktıları kaynak sürümle karşılaştırır. Zorunlu `test` kontrolü,
bütün platform testleri ve paket işi başarılıysa geçer. PyPI'ye paket yayımlanmadı.

Katkı için [CONTRIBUTING.md](CONTRIBUTING.md), güvenlik için
[SECURITY.md](SECURITY.md). Lisans: [MIT](LICENSE). No3214 tarafından geliştirilir.
