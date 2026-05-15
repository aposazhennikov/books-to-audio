# Troubleshooting

Run the doctor first:

```powershell
normalize-book doctor
```

Common issues:

- **ComfyUI not reachable**: start ComfyUI and confirm `http://localhost:8188/system_stats` responds.
- **Workflow placeholders missing**: save the workflow in API format and replace static values with placeholders.
- **No audio in assembly**: run `normalize-book audio-qa output\book\chunks_manifest_v2.json`.
- **Some chunks failed**: use the GUI retry checkbox or run `scripts\synthesize_comfyui.py --failed-only`.
- **Scanned PDFs fail**: install Tesseract with the Russian language pack, then use OCR mode `auto` or `force`.
- **WSL checks warn**: only required for the legacy v1 WSL runner; ComfyUI v2 synthesis runs through the Windows process.
