# Push Flocrawl to Hugging Face Spaces

Simple step-by-step guide.

**Hugging Face Space (Git repo):**  
[https://huggingface.co/spaces/venkyeswar/flocrawl](https://huggingface.co/spaces/venkyeswar/flocrawl)

**Git clone URL:**  
`https://huggingface.co/spaces/venkyeswar/flocrawl`

---

## Step 1: Get your API token

1. Go to [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Click **Create new token**
3. Give it a name (e.g. "flocrawl deploy")
4. Select **Write** access
5. Copy the token (starts with `hf_`)

**Important:** Never share or commit your token. If it was exposed, revoke it and create a new one.

---

## Step 2: Login to Hugging Face

Open a terminal and run:

```bash
pip install huggingface_hub
huggingface-cli login
```

When asked, paste your token and press Enter.

---

## Step 3: Clone your Space

```bash
cd c:\Git_Files\Fission\opensource\flocrawl
git clone https://huggingface.co/spaces/venkyeswar/flocrawl hf-flocrawl
cd hf-flocrawl
```

---

## Step 4: Copy your files

Copy these folders/files from the flocrawl project into `hf-flocrawl`:

- `src`
- `requirements.txt`
- `pyproject.toml`
- `README.md`
- `Dockerfile`

---

## Step 5: Add frontmatter to README

Open `README.md` inside `hf-flocrawl` and add this at the very top:

```yaml
---
title: Flocrawl MCP
emoji: 🔍
sdk: docker
app_port: 7860
---
```

Leave a blank line after `---`, then your existing README content below.

---

## Step 6: Push to Hugging Face

```bash
git add .
git commit -m "Add flocrawl MCP server"
git push origin main
```

If prompted for credentials:

- **Username:** `venkyeswar`
- **Password:** paste your Hugging Face token

**Alternative – use token in remote URL (no prompt):**

```bash
git remote set-url origin https://venkyeswar:YOUR_TOKEN@huggingface.co/spaces/venkyeswar/flocrawl
git push origin main
```

Replace `YOUR_TOKEN` with your actual token. Use this only if the normal push keeps asking for a password.

---

## Troubleshooting

**"Invalid user token" or "401 Unauthorized" when using `huggingface-cli login`:**

1. **Revoke the old token and create a new one** at https://huggingface.co/settings/tokens (old or exposed tokens stop working)
2. **Logout first:** `huggingface-cli logout`, then try `huggingface-cli login` again
3. **Check the token:** no spaces, starts with `hf_`, has **Write** access
4. **Skip login and push with token in the URL** (Step 6 alternative) – this works even when `huggingface-cli login` fails

---

## Done

Your Space will be at: [https://huggingface.co/spaces/venkyeswar/flocrawl](https://huggingface.co/spaces/venkyeswar/flocrawl)

---

## Updating later

1. Copy the updated files again into `hf-flocrawl`
2. Run:
  ```bash
   cd hf-flocrawl
   git add .
   git commit -m "Update"
   git push origin main
  ```

