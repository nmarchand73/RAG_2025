# OCR Installation Guide - Windows

Your system needs Ghostscript and Tesseract for OCR. Here's how to install them:

## Option 1: Direct Downloads (Recommended)

### 1. Install Ghostscript

Download and install from official source:
- **Download**: https://ghostscript.com/releases/gsdnld.html
- Choose: **GPL Ghostscript 10.x for Windows (64 bit)**
- Run installer (default settings are fine)
- Typical location: `C:\Program Files\gs\gs10.xx.x\bin\`

### 2. Install Tesseract OCR

Download and install:
- **Download**: https://github.com/UB-Mannheim/tesseract/wiki
- Choose: **tesseract-ocr-w64-setup-x.x.x.exe** (64-bit)
- During installation, select additional language packs if needed:
  - [x] English (default)
  - [x] French (if your PDFs are in French)
- Typical location: `C:\Program Files\Tesseract-OCR\`

### 3. Verify Installation

Open **Command Prompt** and test:

```cmd
gswin64c --version
tesseract --version
```

If you get version numbers, you're ready!

### 4. Run OCR

```bash
# Simple version (no Ghostscript optimization)
python ocr_simple.py --dir pdfs/ pdfs_ocr/

# Full version (with Ghostscript optimization)
python ocr_pdfs.py --dir pdfs/ pdfs_ocr/
```

---

## Option 2: Chocolatey Package Manager

If you want easy package management:

### 1. Install Chocolatey

Open **PowerShell as Administrator** and run:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### 2. Install OCR Tools

Open **Command Prompt as Administrator**:

```cmd
choco install ghostscript -y
choco install tesseract -y
```

### 3. Refresh PATH

Close and reopen Command Prompt, then verify:

```cmd
gswin64c --version
tesseract --version
```

---

## Option 3: Use Simple OCR Script (No Ghostscript)

If you don't want to install Ghostscript, use the simplified script:

```bash
# This only requires Tesseract (no Ghostscript needed)
python ocr_simple.py --dir pdfs/ pdfs_ocr/
```

**Pros:**
- ✅ Fewer dependencies
- ✅ Faster to set up
- ✅ Still works perfectly

**Cons:**
- ⚠️ Larger output files (no PDF optimization)
- ⚠️ Slightly slower processing

---

## Troubleshooting

### "Tesseract not found"

**Fix 1:** Add to PATH manually
1. Open **System Properties** → **Environment Variables**
2. Edit **Path** variable
3. Add: `C:\Program Files\Tesseract-OCR`
4. Click OK and restart Command Prompt

**Fix 2:** Set environment variable
```cmd
setx TESSDATA_PREFIX "C:\Program Files\Tesseract-OCR\tessdata"
```

### "Ghostscript not found"

**Fix:** Add to PATH
1. Find Ghostscript bin folder: `C:\Program Files\gs\gs10.xx.x\bin`
2. Add to PATH (same as above)
3. Restart Command Prompt

### "Language not supported"

During Tesseract installation, make sure you selected the language packs you need.

To add languages later:
1. Download `.traineddata` files from: https://github.com/tesseract-ocr/tessdata
2. Copy to: `C:\Program Files\Tesseract-OCR\tessdata\`

Common languages:
- `eng.traineddata` - English
- `fra.traineddata` - French
- `deu.traineddata` - German
- `spa.traineddata` - Spanish

---

## Quick Test

Test with a single page:

```bash
# Extract first page of PDF for quick test
python -c "import fitz; doc=fitz.open('pdfs/generation4_numero001.pdf'); doc[0].save('test_page.pdf'); doc.close()"

# OCR just that page (fast test)
python ocr_simple.py test_page.pdf test_page_ocr.pdf

# Check if it worked
python -c "import fitz; doc=fitz.open('test_page_ocr.pdf'); print('Text found:', len(doc[0].get_text())); doc.close()"
```

If the last command shows a number > 0, OCR is working!

---

## Recommended Approach

1. **Install Tesseract** (required) - ~5 minutes
2. **Try ocr_simple.py** first - no other dependencies
3. If you want smaller files, **install Ghostscript** later

For your 237-page PDFs, expect:
- **Processing time**: ~10-15 minutes per file
- **Output size**: 50-100MB (simple) or 30-60MB (with Ghostscript)

---

## Need Help?

Check if everything is installed:

```bash
# Run diagnostic script
python -c "import sys; import shutil; print('Python:', sys.version); print('Tesseract:', shutil.which('tesseract')); print('Ghostscript:', shutil.which('gswin64c'))"
```

This will show what's installed and what's missing.
