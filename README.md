# Mandarin HSK 3.0 Words Audio

Pronunciation audio for about 12,500 Mandarin characters and words, with a table
that maps each one to its pinyin and its audio file.

- `words.csv`: one row per entry (`id`, `hanzi`, `pinyin`, `audio`)
- `audio/<id>.mp3`: the pronunciation for that entry
- `scripts/regenerate_audio.py`: regenerates every MP3 from `words.csv`

## Audio details

- Generated with Azure AI Speech, voice `zh-CN-XiaoxiaoNeural`
- Format: MP3, 24 kHz, 48 kbps, mono
- Single characters are synthesized from their pinyin, so characters with several
  readings (行, 长, 了) use the listed reading. Words are synthesized as plain text.

## Using the audio

Look up a row in `words.csv` and play the file in its `audio` column.

```python
import csv
for row in csv.DictReader(open("words.csv", encoding="utf-8")):
    print(row["hanzi"], row["pinyin"], row["audio"])
```

## Regenerating the audio

You need an Azure Speech resource (the free tier covers 500,000 characters a
month; the full list is roughly 20,000 characters, so check current pricing in the
Azure portal).

```bash
pip install -r requirements.txt
export AZURE_SPEECH_KEY=...        # Azure portal > Speech resource > Keys
export AZURE_SPEECH_REGION=eastus  # your resource's region

python scripts/regenerate_audio.py --dry-run   # count characters, no API calls
python scripts/regenerate_audio.py --limit 20  # trial run
python scripts/regenerate_audio.py             # generate missing files
python scripts/regenerate_audio.py --force     # overwrite existing files
```

Existing files are skipped, so an interrupted run resumes where it stopped.
Never commit your Azure key.

## License

The code and word table are covered by the license in [LICENSE](LICENSE).
The audio is synthesized speech from Azure AI Speech. If you redistribute or use
it commercially, check Microsoft's current terms for Azure AI Speech output.
