# VIDHI - GitHub Repository Setup Guide

## Quick Setup (5 Minutes)

### Step 1: Initialize Local Repository

```bash
# Run the automated setup script
setup-github.bat

# Or manually:
git init
git add .
git commit -m "Initial commit: VIDHI - AI Legal Assistant"
```

### Step 2: Create GitHub Repository

1. Go to: https://github.com/new
2. **Repository name**: `vidhi`
3. **Description**: `AI-Powered Legal Assistant for Indian Citizens - 22+ languages, voice I/O, AWS integration`
4. **Visibility**: Public (recommended) or Private
5. **DO NOT** check "Add a README file" (we already have one)
6. **DO NOT** check "Add .gitignore" (we already have one)
7. **License**: None (we already have MIT license)
8. Click **"Create repository"**

### Step 3: Connect Local to GitHub

```bash
# Replace 'yourusername' with your actual GitHub username
git remote add origin https://github.com/yourusername/vidhi.git
git branch -M main
git push -u origin main
```

### Step 4: Verify Upload

Your repository should now be live at:
`https://github.com/yourusername/vidhi`

## Repository Structure

```
vidhi/
├── 📁 vidhi-assistant/          # React Frontend
│   ├── 📁 src/
│   │   ├── 📁 components/       # UI Components
│   │   ├── 📁 pages/           # Pages (Login, Chat)
│   │   ├── 📁 api/             # API Client
│   │   └── 📁 utils/           # Utilities
│   ├── 📄 package.json
│   ├── 📄 README.md
│   └── 📄 vite.config.ts
│
├── 📁 vidhi-backend/           # FastAPI Backend
│   ├── 📄 app.py              # Main application
│   ├── 📄 app-simple.py       # Python 3.13 compatible
│   ├── 📁 configs/            # Configuration
│   ├── 📁 services/           # Business logic
│   ├── 📁 speech/             # Voice services
│   ├── 📁 llm_setup/          # LLM configuration
│   ├── 📁 stores/             # Vector stores
│   ├── 📄 requirements*.txt   # Dependencies
│   └── 📄 README.md
│
├── 📁 docs/                   # Documentation
│   ├── 📄 COMPLETE_AWS_SETUP_GUIDE.md
│   ├── 📄 QUICK_START_REFERENCE.md
│   ├── 📄 BHASHINI_API_SETUP.md
│   └── 📄 WHY_MUMBAI_REGION.md
│
├── 📄 README.md              # Main project overview
├── 📄 .gitignore            # Git ignore rules
├── 📄 LICENSE               # MIT License
├── 📄 setup-github.bat      # Setup script
└── 📄 GITHUB_SETUP.md       # This file
```

## What Gets Uploaded

### ✅ Included Files
- All source code (frontend + backend)
- Documentation and setup guides
- Configuration templates (.env.example)
- Package.json and requirements.txt
- README files and licenses

### ❌ Excluded Files (via .gitignore)
- Environment files (.env)
- API keys and secrets
- Node_modules and Python venv
- Build artifacts and cache files
- Database files and audio cache
- AWS credentials
- Personal data

## Repository Settings

### Recommended Settings

1. **Branch Protection**:
   - Go to Settings → Branches
   - Add rule for `main` branch
   - Require pull request reviews
   - Require status checks

2. **Security**:
   - Go to Settings → Security & analysis
   - Enable Dependabot alerts
   - Enable Secret scanning

3. **Pages** (Optional):
   - Go to Settings → Pages
   - Deploy frontend to GitHub Pages
   - Source: GitHub Actions

### Repository Topics

Add these topics to help others find your project:
```
ai, legal-assistant, indian-languages, aws, fastapi, react, 
voice-recognition, text-to-speech, legal-tech, government-schemes,
bedrock, polly, transcribe, multilingual, accessibility
```

## Collaboration Setup

### For Team Development

1. **Add Collaborators**:
   - Go to Settings → Manage access
   - Click "Invite a collaborator"
   - Add team members

2. **Create Development Workflow**:
   ```bash
   # Create development branch
   git checkout -b development
   git push -u origin development
   
   # Set development as default branch
   # Go to Settings → Branches → Default branch
   ```

3. **Feature Branch Workflow**:
   ```bash
   # Create feature branch
   git checkout -b feature/new-language-support
   
   # Make changes and commit
   git add .
   git commit -m "Add Punjabi language support"
   
   # Push and create pull request
   git push -u origin feature/new-language-support
   ```

## GitHub Actions (CI/CD)

### Automated Testing

Create `.github/workflows/test.yml`:

```yaml
name: Test VIDHI

on: [push, pull_request]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: |
          cd vidhi-backend
          pip install -r requirements-windows-minimal.txt
          python test-installation.py

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: |
          cd vidhi-assistant
          npm install
          npm run build
```

### Automated Deployment

Create `.github/workflows/deploy.yml` for AWS deployment.

## Repository Maintenance

### Regular Updates

```bash
# Pull latest changes
git pull origin main

# Create feature branch
git checkout -b feature/update-dependencies

# Update dependencies
cd vidhi-backend
pip install --upgrade -r requirements.txt

cd ../vidhi-assistant
npm update

# Commit and push
git add .
git commit -m "Update dependencies"
git push -u origin feature/update-dependencies
```

### Release Management

```bash
# Create release branch
git checkout -b release/v1.0.0

# Update version numbers
# Update CHANGELOG.md

# Create release
git tag v1.0.0
git push origin v1.0.0
```

## Troubleshooting

### Common Issues

1. **Large files rejected**:
   ```bash
   # Remove large files from git history
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch large-file.zip' \
     --prune-empty --tag-name-filter cat -- --all
   ```

2. **Sensitive data committed**:
   ```bash
   # Remove sensitive file from history
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch .env' \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **Push rejected**:
   ```bash
   # Force push (use carefully)
   git push --force-with-lease origin main
   ```

### Getting Help

- 📖 GitHub Docs: https://docs.github.com
- 🆘 Git Help: `git help <command>`
- 💬 GitHub Community: https://github.community

## Next Steps

After setting up GitHub:

1. **Configure AWS** (see `docs/COMPLETE_AWS_SETUP_GUIDE.md`)
2. **Set up development environment**
3. **Deploy to production**
4. **Add team members**
5. **Set up CI/CD pipelines**

## Repository URL

Your repository will be available at:
`https://github.com/yourusername/vidhi`

Replace `yourusername` with your actual GitHub username.

## Commands Summary

```bash
# Setup
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/vidhi.git
git push -u origin main

# Daily workflow
git pull origin main
git checkout -b feature/new-feature
# Make changes
git add .
git commit -m "Add new feature"
git push -u origin feature/new-feature
# Create pull request on GitHub

# Release
git tag v1.0.0
git push origin v1.0.0
```