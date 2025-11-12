# How to Upload Project to GitHub

Complete guide to upload your chatbot project to GitHub.

## ⚠️ Important: Before You Start

**NEVER commit these files:**
- `.env` file (contains API keys and passwords)
- `node_modules/` folder
- `.venv/` folder
- `__pycache__/` folders
- Database files

The `.gitignore` file has been created to automatically exclude these files.

## Method 1: Using Git Command Line (Recommended)

### Step 1: Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the **"+"** icon in the top right → **"New repository"**
3. Fill in:
   - **Repository name**: `cache-digitech-chatbot` (or your preferred name)
   - **Description**: "AI Chatbot powered by Google Gemini with RAG"
   - **Visibility**: Choose Public or Private
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
4. Click **"Create repository"**

### Step 2: Initialize Git in Your Project

Open PowerShell/Terminal in your project directory:

```bash
# Navigate to project root
cd C:\Users\risha\Downloads\finalbot

# Initialize git repository
git init

# Check git status (should show all files)
git status
```

### Step 3: Add Files to Git

```bash
# Add all files (respects .gitignore)
git add .

# Verify what will be committed
git status
```

**Important**: Make sure `.env` file is NOT in the list! If it is, check your `.gitignore` file.

### Step 4: Create First Commit

```bash
# Create initial commit
git commit -m "Initial commit: Cache Digitech Chatbot with RAG"

# Or with more details:
git commit -m "Initial commit: Cache Digitech Chatbot

- AI chatbot powered by Google Gemini 2.5 Flash
- RAG implementation with Pinecone
- Knowledge base management
- Web crawling capabilities
- Admin panel with analytics
- React frontend widget"
```

### Step 5: Connect to GitHub and Push

```bash
# Add GitHub repository as remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# Example:
# git remote add origin https://github.com/ronanop/cache-digitech-chatbot.git

# Rename default branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

**Note**: You'll be prompted for GitHub username and password (or personal access token).

### Step 6: Verify Upload

1. Go to your GitHub repository page
2. Refresh the page
3. You should see all your files!

## Method 2: Using GitHub Desktop (GUI Method)

### Step 1: Install GitHub Desktop

1. Download from: https://desktop.github.com/
2. Install and sign in with your GitHub account

### Step 2: Add Repository

1. Open GitHub Desktop
2. Click **"File"** → **"Add Local Repository"**
3. Click **"Choose"** and select your project folder: `C:\Users\risha\Downloads\finalbot`
4. Click **"Add Repository"**

### Step 3: Commit Files

1. You'll see all changed files in the left panel
2. **Verify `.env` is NOT listed** (it should be grayed out)
3. Write commit message: "Initial commit: Cache Digitech Chatbot"
4. Click **"Commit to main"**

### Step 4: Publish to GitHub

1. Click **"Publish repository"** button at the top
2. Choose:
   - **Name**: Your repository name
   - **Description**: "AI Chatbot powered by Google Gemini"
   - **Visibility**: Public or Private
3. Click **"Publish Repository"**

## Method 3: Using VS Code (If You Use VS Code)

### Step 1: Open in VS Code

1. Open VS Code
2. **File** → **Open Folder** → Select your project folder

### Step 2: Initialize Git

1. Open Terminal in VS Code (`` Ctrl+` ``)
2. Run:
```bash
git init
git add .
git commit -m "Initial commit: Cache Digitech Chatbot"
```

### Step 3: Push to GitHub

1. Click **Source Control** icon (left sidebar)
2. Click **"..."** menu → **"Publish to GitHub"**
3. Choose repository name and visibility
4. Click **"Publish"**

## 🔐 Security Checklist

Before pushing, verify:

- [ ] `.env` file is NOT in git (check with `git status`)
- [ ] No API keys in code files
- [ ] No passwords in code
- [ ] `.gitignore` includes `.env`
- [ ] Database files are excluded
- [ ] `node_modules/` is excluded

### Verify .env is Ignored

```bash
# Check if .env is tracked
git ls-files | grep .env

# Should return nothing. If it shows .env, remove it:
git rm --cached .env
git commit -m "Remove .env from tracking"
```

## 📝 Adding .env.example Instead

Create a template file for others (without real keys):

```bash
# Copy .env to .env.example (already created)
# Edit .env.example and replace real values with placeholders
```

The `.env.example` file shows what environment variables are needed without exposing secrets.

## 🔄 Updating Repository Later

After making changes:

```bash
# Check what changed
git status

# Add changed files
git add .

# Commit changes
git commit -m "Description of changes"

# Push to GitHub
git push
```

## 📋 Common Commands Reference

```bash
# Check status
git status

# Add all files
git add .

# Add specific file
git add filename.py

# Commit changes
git commit -m "Your commit message"

# Push to GitHub
git push

# Pull latest changes
git pull

# View commit history
git log

# Create new branch
git checkout -b feature-name

# Switch branches
git checkout main
```

## 🐛 Troubleshooting

### Issue: "Authentication failed"

**Solution**: Use Personal Access Token instead of password:
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo` (full control)
4. Copy token and use it as password when pushing

### Issue: ".env file is being tracked"

**Solution**:
```bash
# Remove from git tracking
git rm --cached .env

# Add to .gitignore (already done)
# Commit the change
git commit -m "Remove .env from tracking"
```

### Issue: "Repository not found"

**Solution**: 
- Check repository name is correct
- Verify you have access to the repository
- Check remote URL: `git remote -v`

### Issue: "Large file upload fails"

**Solution**: 
- Check file sizes: `git ls-files | xargs ls -lh`
- Remove large files: `git rm large-file.pdf`
- Use Git LFS for large files if needed

## 📚 Next Steps After Upload

1. **Add Repository Description**: Go to repository → Settings → Update description
2. **Add Topics**: Add tags like `python`, `fastapi`, `chatbot`, `ai`, `rag`
3. **Set Up GitHub Actions**: For CI/CD (optional)
4. **Add License**: If you want to specify license
5. **Create Releases**: Tag versions for releases

## 🎯 Repository Settings Recommendations

1. **Branch Protection**: Settings → Branches → Add rule for `main` branch
2. **Secrets**: Settings → Secrets → Add repository secrets (for CI/CD)
3. **Collaborators**: Settings → Collaborators → Add team members
4. **Webhooks**: Settings → Webhooks → Add for deployments

## 📖 Additional Resources

- [GitHub Docs](https://docs.github.com/)
- [Git Cheat Sheet](https://education.github.com/git-cheat-sheet-education.pdf)
- [GitHub Desktop Guide](https://docs.github.com/en/desktop)

---

**Need Help?** Check GitHub's official documentation or open an issue in your repository.

