# Git CLI

TUI to tracks git repository

## Requirements

- Python 3.9+
- Git
- GitHub CLI (`gh`) untuk login, PR, dan issue

## Import repository

Buat file teks dengan satu path repository lokal per baris:

```text
# repos.txt
~/code/api
~/code/web
```

Di TUI, masukkan path file tersebut pada **Import file repository** lalu pilih **Import repository**. Path relatif dihitung dari lokasi file. Registry tersimpan otomatis di `~/Library/Application Support/git-cli/repos.json` pada macOS atau `$XDG_CONFIG_HOME/git-cli/repos.json` / `~/.config/git-cli/repos.json` pada Linux.
