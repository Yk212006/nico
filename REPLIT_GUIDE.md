# NICO on Replit — Complete Setup

## Step 1: Create Replit account

1. Go to https://replit.com
2. Click **"Sign up"** → **"Continue with GitHub"** (easiest)
3. No credit card needed

## Step 2: Import NICO from GitHub

1. Click the **"Create"** button (top-left) → **"Import from GitHub"**
2. In the **"GitHub URL"** field, paste:
   ```
   https://github.com/Yk212006/nico
   ```
3. Click **"Import from GitHub"**
4. Wait 1-2 minutes for it to clone

## Step 3: Set up environment

1. In the left sidebar, click the **padlock icon** (Secrets) — it's below the file explorer
2. Add these secrets (click **"New Secret"** for each):

   | Key | Value |
   |-----|-------|
   | `OPENAI_API_KEY` | `sk-...your-openai-key...` |
   | `NICO_DEFAULT_PROVIDER` | `openai` |
   | `NICO_PORT` | `8080` |
   | `GOOGLE_CREDENTIALS_FILE` | `credentials.json` |
   | `GOOGLE_TOKEN_FILE` | `/home/runner/.nico/google_token.json` |

   *(If using Google Calendar/Gmail, you also need to upload `credentials.json` — see Step 4)*

## Step 4: Upload Google credentials (optional)

Only if you use Google Calendar/Gmail:

1. In the **Files** panel (sidebar), click the **three dots** (⋮) → **"Upload file"**
2. Select your `credentials.json` file from your computer
3. Make sure the filename is exactly `credentials.json` (matching `GOOGLE_CREDENTIALS_FILE`)

## Step 5: Create the run script

1. In the **Files** panel, click the **"New file"** button (📄+)
2. Name it: `replit.nix`
3. Paste:
   ```nix
   { pkgs }: {
     deps = [
       pkgs.python311
       pkgs.python311Packages.pip
     ];
   }
   ```

4. Click **"New file"** again
5. Name it: `.replit`
6. Paste:
   ```yaml
   language = "python3"
   run = "python -m nico.web_api"
   ```

## Step 6: Install dependencies

1. Click the **"Shell"** tab (bottom panel, next to Console)
2. Run:
   ```bash
   pip install -e .[web,google]
   ```

   *(If you want Google Assistant too: `pip install -e .[web,google,assistant]`)*

   Wait for it to finish (may take 1-2 minutes).

## Step 7: Run NICO

1. Click the big **"Run"** button (top bar)
2. The first run will trigger Google OAuth — look at the **Console** tab for a URL like:
   ```
   Please visit this URL to authorize: https://accounts.google.com/o/oauth2/auth?...
   ```
3. **Copy that full URL**, paste it into your browser, sign in with your Google account, and copy the authorization code back into the Console.

4. After that, the server starts and Replit shows a **webview** panel. Click the **"Open in a new tab"** icon (top-right of the webview) to get the public URL.

## Step 8: Access from anywhere

Your Replit URL looks like:
```
https://nico.your-username.replit.app
```

Open that on any device — phone, Pi, laptop, anywhere.

**Bookmark it** — that URL stays the same.

---

## Important Notes

### Replit sleeps after inactivity
If no one visits for ~1 hour, the server goes to sleep. When you visit the URL again:
- It takes **15-30 seconds** to wake up
- After waking, NICO runs normally

To wake it up faster, just visit the Replit project page and click **Run** before using the URL.

### First OAuth (Google Calendar/Gmail)
The first time you run, you'll need to authenticate via the Console. After that, the token is saved and you won't need to do it again.

### If something breaks
```bash
# In Shell:
pkill -f nico.web_api
pip install -e .[web,google]
# Then click Run again
```

---

## Done

Open `https://nico.your-username.replit.app` from your Pi, phone, laptop — anywhere with internet. NICO runs on Replit's servers, your Pi does nothing but display the webpage.
