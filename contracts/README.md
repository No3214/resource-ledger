# Optional repository contract / İsteğe bağlı depo sözleşmesi

This is a maintainer example using
[Repo Contract Check](https://github.com/No3214/repo-contract-check) against this
public Resource Ledger checkout. It checks three package declarations and the
presence of six files. It does not execute project commands or discover other
repositories. Resource Ledger's normal CSV/report commands need no checker.

## Run the nine checks

Install Repo Contract Check from a local source checkout using its
[installation instructions](https://github.com/No3214/repo-contract-check#quickstart).
No package has been published to PyPI. The checker used for this recipe is
[commit d1d548e](https://github.com/No3214/repo-contract-check/commit/d1d548efc95d986d4709ea6cf5c3f65820da821e),
version `0.1.0`; record its commit as well as its version when repeating the demo.
Downloading source or build dependencies may need a network connection. The
installed check below reads local files only.

With the checker's virtual environment active, run from the **Resource Ledger
repository root**:

```sh
git rev-parse HEAD
repo-contract-check --version
repo-contract-check check contracts/repository.json --roots contracts/roots.example.json --format json
```

Record the first command's output as the target Resource Ledger commit. Local
uncommitted edits are part of the files checked; a commit ID alone does not record
them. For a reproducible demonstration, use a clean checkout. The checker does
not inspect Git status or revisions itself.

Expected result for the published tree containing these files: exit **0** and
`"summary": {"error": 0, "fail": 0, "pass": 9}`. The roots file binds the public
alias to `..`, resolved from **the roots file's directory**, so it contains no
private absolute path. Keep that file in `contracts/` when reusing it.

| Rule group | What is checked |
| --- | --- |
| Package declarations | Python requirement exactly `>=3.11`, declared runtime dependencies exactly `[]`, console entry point exactly `resource_ledger:main`. |
| First-report files | Turkish guide, blank CSV template, expected JSON and Markdown files exist. |
| Verification files | Example acceptance test file and CI workflow file exist. |

An exact declaration comparison is not a Python version compatibility solver.
An empty dependency declaration does not prove all source behavior. File presence
does not prove that the file is correct, that CI ran, or that a real business
pilot succeeded. The existing test suite checks actual outputs separately:

```sh
python3 -m unittest discover -s tests -v
```

Use `python` instead of `python3` if that is your installed command. The three
example acceptance tests compare the committed reference outputs and check the
invalid example/template behavior. They run in the existing CI matrix; this
optional contract introduces no second-repository checkout into required CI.

## See a failed expectation

Create `reports/` if needed. Copy `contracts/repository.json` there as
`contract-wrong.local.json`. In that copy, change only the `python-version` rule's
`expected` value to `>=3.12`. Keep the project's real `pyproject.toml` unchanged.
Run from the same repository root:

```sh
repo-contract-check check reports/contract-wrong.local.json --roots contracts/roots.example.json --format json
```

Expected: exit **1**, eight passing checks, and the `python-version` rule failing
with `value_mismatch`. An unreadable or missing roots configuration is an input
error and returns **2** instead. Inspect the exit code immediately with `echo $?`
in Bash/zsh or `$LASTEXITCODE` in PowerShell. Reports omit local paths and actual
values; aliases and rule IDs remain visible. `reports/` is ignored by Git.

## Türkçe kullanım ve sınırlar

Bu, geliştiricinin iki public aracı birlikte kullanabileceği isteğe bağlı bir
örnektir. Repo Contract Check'i kendi kaynak kurulum yönergesiyle kurup sanal
ortamını etkinleştirin. Üstteki komutları **Resource Ledger kök klasöründe**
çalıştırın. Denenen checker commit'i `d1d548efc95d986d4709ea6cf5c3f65820da821e`;
yalnız `0.1.0` sürüm numarası aynı kodun kullanıldığını kanıtlamaz. Kaynak indirme
ile yerel kontrol ayrı adımlardır; kurulu denetleyici yerel dosyaları okur.

`git rev-parse HEAD` ile hedef Resource Ledger commit'ini kaydedin. Tekrarlanabilir
gösterim için temiz checkout kullanın; kaydedilmemiş değişiklikler de kontrol
edilen dosyalara dahildir. Denetleyici Git durumunu kendisi doğrulamaz.

Normal sonuç dokuz `pass`, çıkış `0`. Hatalı örnek için sözleşmeyi `reports/` içine
kopyalayın; yalnız `python-version` beklentisini `>=3.12` yapın. Yukarıdaki ikinci
denetim komutu sekiz `pass`, bir `value_mismatch` ve çıkış `1` üretmelidir.
Okunamayan kök yapılandırması ise çıkış `2` verir. Asıl proje dosyalarını bu
olumsuz deneme için değiştirmeyin.

Bu sonuçlar seçilmiş bildirim ve dosya varlığı kontrolleridir. Testlerin geçtiği,
CI'ın çalıştığı veya gerçek işletme pilotunun tamamlandığı anlamına gelmez. Gerçek
örnek çıktıları mevcut test paketiyle ve onun CI sonuçlarıyla ayrıca doğrulanır.
İlk işletme raporunu hazırlamak için [Türkçe kullanıcı rehberini](../examples/README.tr.md)
kullanın; tüketim raporu almak için bu geliştirici denetleyicisini kurmak gerekmez.
