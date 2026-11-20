# Kendi verinizle ilk rapor

[English guide](README.md) · [Girdi kuralları](../README.tr.md#girdi-sözleşmesi)

Ana README'deki indirme adımından sonra komutları depo klasöründe çalıştırın.
Python 3.11 veya üzeri gerekir. Sisteminizdeki komut `python` ise, Windows dahil,
`python3` yerine onu kullanın. Bu klasördeki dosyalar sentetik örnek veya boş
şablondur; hiçbiri gerçek işletme pilotunun yapıldığını göstermez.

## 1. Açıklamalı örneği çalıştırın

Önce çıktı ve özel veri klasörlerini oluşturun, ardından okunabilir raporu üretin:

```sh
python3 -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True); Path('private-data').mkdir(exist_ok=True)"
python3 resource_ledger.py examples/synthetic.csv --format markdown --output reports/example.md
```

Beklenen çıkış kodu: **0**. `reports/example.md` dosyasını
[synthetic.expected.md](synthetic.expected.md) ile karşılaştırın. JSON için:

```sh
python3 resource_ledger.py examples/synthetic.csv --output reports/example.json
```

Beklenen dosya [synthetic.expected.json](synthetic.expected.json). Sekiz girdi
satırı, iki saha ve iki ay içerir. Şu değerleri elle de kontrol edin:

| Kontrol | Beklenen sonuç |
| --- | --- |
| Ocak elektrik | `1200.50 + 250 = 1450.5 kWh` |
| Ocak su | `45.25 + 8.5 = 53.75 m3` |
| Ocak atık | `110 + 35 = 145 kg` |
| Şubat elektrik | `1000 kWh`; Demo Cafe ölçümü eksik olduğu için kısmi kapsam |
| Şubat atık | JSON'da `null`, Markdown'da uzun çizgi; ölçüm yok, sıfır değil |
| Şubat Demo Guesthouse faaliyet başına elektrik | `null`, nedeni `zero_activity_count` |

Bu örnek sıfır **faaliyet sayısını** gösterir; ölçülmüş sıfır tüketim içermez.
Kapsam, girdinin herhangi bir yerinde bulunan sahalara aittir. Baştan hiç girilmemiş
bir sahayı araç keşfedemez. Kısmi toplam, eksik tüketimin tahmini değildir.

## 2. Hatalı dosyayı deneyin, örnek rapor korunsun

Yukarıdaki aynı **sentetik** çıktı yolunu kullanın:

```sh
python3 resource_ledger.py examples/invalid-duplicate.csv --format markdown --output reports/example.md
```

Beklenen çıkış kodu: **2**. Standart hata akışında yinelenen ölçüm açıklaması çıkar.
Kodu görmek için hemen ardından Bash/zsh'de `echo $?`, PowerShell'de `$LASTEXITCODE`
çalıştırın. Önceki `reports/example.md` değişmemelidir. Metni şöyle kontrol edin:

```sh
python3 -c "from pathlib import Path; assert Path('reports/example.md').read_text(encoding='utf-8') == Path('examples/synthetic.expected.md').read_text(encoding='utf-8'); print('PASS: example report preserved')"
```

Yinelenen kaydı düzeltirken kaynak belgeleri kontrol edip o ay için amaçlanan tek
ölçümü tutun. Araç aynı miktarı içeren yinelenen satırları da toplamaz.

## 3. Kendi CSV dosyanızı hazırlayın

Beş sütunlu [template.csv](template.csv) dosyasını özel klasörünüze kopyalayın:

```sh
python3 -c "from pathlib import Path; data=Path('examples/template.csv').read_bytes(); f=Path('private-data/my-ledger.csv').open('xb'); f.write(data); f.close()"
```

Komut mevcut dosyanın üzerine yazmayı reddeder. Tekrar kullanırken mevcut kopyanızı
düzenleyin veya başka bir ad seçin. **Şablonda ölçüm yoktur; en az bir veri satırı
ekleyene kadar bilerek çıkış 2 verir.**

İlk denemede tek saha, tek takvim ayı ve kontrol edebildiğiniz kaynak kayıtlarla
başlayın. Kümülatif sayaç okumasını değil, o ayın tüketimini girin. Eşleşmeler:
`electricity/kWh`, `water/m3`, `waste/kg`; birim dönüşümü yapılmaz. Saha adını hep
aynı yazın. Virgül içeren ad tırnaklanmalıdır; örneğin `"İzmir, Merkez"`.

Bilinmeyen ölçüm için **o ay/saha/metrik satırını eklemeyin**. Miktar hücresini boş
bırakmayın veya yerine `0` yazmayın. Yalnız gerçekten ölçülmüş sıfır için `0` girin.
Faaliyet sütunlarını daha sonra birlikte ekleyebilirsiniz; tutarlılık kuralları
ana README'de. Bu sütunlar olmadan tüketim miktarları geçerlidir, faaliyet başına
oranlar hesaplanmaz.

Kaydedilen dosyayı metin olarak önizleyin: **UTF-8, sütun ayracı virgül, ondalık
ayracı nokta**. UTF-8 BOM olabilir veya olmayabilir. `.csv` uzantısı bu ayarları
garanti etmez; Excel'in ayracı bölge ve uygulama ayarlarına göre değişebilir.
Microsoft'un [CSV dışa aktarma][csv-export] ve [UTF-8 içe aktarma][csv-utf8]
açıklamalarına bakabilirsiniz.

| Belirti | Düzeltme |
| --- | --- |
| Başlık `month;site;metric;amount;unit` | Virgülle ayrılmış biçimde dışa aktarın. |
| Miktar `"8,5"` veya `8,5` | Kaynak miktarı doğrulayıp `8.5` yazın; dosyadaki bütün virgülleri değiştirmeyin. |
| Türkçe karakterler bozuk | UTF-8 kaydedin; tablo yazılımının metin/CSV içe aktarma önizlemesini kullanın. |
| Çıkış 3 ile dosya hatası | Girdi dosyasının ve hedef klasörün varlığını, yazma iznini kontrol edin. |

## 4. Rapor alın ve kaynakla karşılaştırın

Özel CSV dosyanızı doldurduktan sonra:

```sh
python3 resource_ledger.py private-data/my-ledger.csv --format markdown --output reports/my-report.md
```

Geçerli veri ve başarılı çıktı için **0** beklenir. Dönemi, saha yazımını,
birimleri, en az bir miktarı kaynak belgeye göre ve raporlanan her toplamı ilgili
kaynak miktarlara göre kontrol edin. Eksik metrikler eksik kalır. JSON isterseniz
`--format markdown` seçeneğini kaldırıp `--output reports/my-report.json` kullanın.

`private-data/` ve `reports/` Git tarafından yok sayılır; bu şifreleme veya erişim
kontrolü değildir. Faturaları, işletme girdilerini ve raporları özel tutun. Yukarıdaki
gibi `--output` kullanın; çıktıyı girdi CSV dosyanızın üzerine yönlendirmeyin.

[pilot-record.md](pilot-record.md) formunu `reports/` klasörüne kopyalayıp kabul
notlarınızı doldurun. Yardım gerekip gerekmediğini, kaynak karşılaştırmasını ve
daha sonraki tekrar kullanımını kaydedin. Başlangıç durumu **NOT_RUN**. Bu setin
yayımlanması veya sentetik testlerin geçmesi, gerçek işletme pilotunun geçtiği
anlamına gelmez.

[csv-export]: https://support.microsoft.com/en-us/excel/get-started/import-or-export-text-txt-or-csv-files
[csv-utf8]: https://support.microsoft.com/en-us/excel/opening-csv-utf-8-files-correctly-in-excel
