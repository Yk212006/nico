# NICO on Android Phone — Access Anywhere

## Step 1: Get Termux

1. Install **F-Droid** from https://f-droid.org (enable "Allow from this source" in settings)
2. Open F-Droid, search **Termux**, install it
3. Open Termux

> **DO NOT** use the Play Store version — it's outdated and broken.

## Step 2: Install NICO

In Termux, paste each line (tap Enter after each):

```bash
pkg update && pkg upgrade -y
pkg install -y python git
git clone https://github.com/Yk212006/nico.git
cd nico
pip install -e .[web]
```

This takes 2-3 minutes.

## Step 3: Get a working Gemini key

**This is the most reliable method** (creates a fresh Google Cloud project):

1. On your phone browser, go to https://console.cloud.google.com
2. Sign in with your Google account
3. At the top, click the project dropdown → **New Project**
4. Name: `nico` → **Create**
5. Go to ☰ menu → **APIs & Services** → **Library**
6. Search "Generative Language API" → click it → **Enable**
7. Go to ☰ menu → **APIs & Services** → **Credentials**
8. Click **Create Credentials** → **API Key**
9. Copy the key (starts with `AIza...` or `AQ.`)

**If it still gives AQ. key**, go back to step 6, make sure Generative Language API is **Enabled** (shows "API Enabled" badge), then create a new key again.

Set the key in Termux:
```bash
export GEMINI_API_KEY="paste-your-key-here"
export NICO_DEFAULT_PROVIDER=gemini
```

## Step 4: Run NICO

```bash
cd nico
python -m nico.web_api
```

You'll see the server start. Test it:
- Open Chrome on your phone
- Go to `http://localhost:8080`
- You should see the NICO chat UI

## Step 5: Access from anywhere

**Open a 2nd Termux session** (swipe from left edge → New Session):

```bash
pkg install -y cloudflared
cloudflared tunnel --url http://localhost:8080
```

It prints:
```
https://random-name.trycloudflare.com
```

Open that URL on your Pi, friend's phone, laptop — anywhere.

## Step 6: Keep the phone on

- Keep Termux running in the background
- Keep your phone charged and connected to WiFi/mobile data
- Don't let your phone sleep (Settings → Developer Options → Stay awake while charging)

## Step 7: Auto-start (optional)

Each time you reboot your phone:

```bash
# In Termux:
cd nico
export GEMINI_API_KEY="your-key"
export NICO_DEFAULT_PROVIDER=gemini
python -m nico.web_api
```

---

## Troubleshooting

### "Generative Language API not found"
Make sure you enabled it in step 6. Go back and verify.

### Key still has 0 quota
Try creating the key **after** enabling the API (not before). Order matters.

### Termux closes when phone sleeps
Go to Android Settings → Apps → Termux → **Ignore battery optimizations** → **Allow**

### "pip not found"
```bash
pkg install -y python
```

### Model not responding
Try with a simpler model:
```bash
export GEMINI_API_KEY="your-key"
export NICO_DEFAULT_PROVIDER=gemini
```
Then restart NICO.

---

**Cost**: $0. Gemini free tier gives 60 requests/minute, no credit card needed.
