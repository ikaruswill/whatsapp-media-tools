# whatsapp-date-exif
Restore WhatsApp Media exif dates from filenames

## Usage
### Restoring exif dates
```
usage: restore-exif.py [-h] [-r] [-m] path

Restore discarded Exif date information in WhatsApp media based on the filename.

positional arguments:
  path             Path to WhatsApp media folder

options:
  -h, --help       show this help message and exit
  -r, --recursive  Recursively process media
  -m, --mod        Set file modified date
```

### Finding duplicate media files
```
usage: find-duplicates.py [-h] [-c CHUNK_SIZE] [-f] [-r] [--dry-run] path

Remove duplicated media, preserving the file with the shortest filename or earliest date encoded in the filename.

positional arguments:
  path                  Path to WhatsApp media folder

options:
  -h, --help            show this help message and exit
  -c CHUNK_SIZE, --chunk-size CHUNK_SIZE
                        Chunk size for heuristic, smaller values are generally faster but if many files have identical starting chunks, performance degrades as more full hashes are computed
  -f, --force           Delete duplicates without prompting
  -r, --recursive       Recursively process media
  --dry-run             Dry run deletion (no files deleted)
  ```