# VIDHI - Voice-Integrated Defense for Holistic Inclusion

🏛️ **AI-Powered Legal Assistant for Indian Citizens**

VIDHI is a comprehensive legal assistance platform that provides accessible legal guidance, government scheme information, and document analysis in 22+ Indian languages with voice support.

## 🚀 Features

### Core Features
- ✅ **22+ Indian Languages** - Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, and more
- ✅ **Voice Input/Output** - Speak your questions, hear responses in your language
- ✅ **Legal AI Chat** - Powered by AWS Bedrock (Claude 3)
- ✅ **Emergency Legal Assistance** - Immediate rights information for urgent situations
- ✅ **User Profiles & History** - Personalized experience with chat history

### Advanced Features
- ✅ **Document Education System** - Interactive teaching for legal documents
- ✅ **Language-Preserved Voice Playback** - Bhojpuri messages stay in Bhojpuri
- ✅ **Legal Glossary** - 100+ legal terms explained simply
- ✅ **Clause Analysis** - Break down complex legal clauses
- ✅ **Government Scheme Search** - Find relevant schemes and benefits

### Technical Features
- ✅ **AWS Bedrock** - Advanced LLM capabilities
- ✅ **AWS Polly** - High-quality text-to-speech (7 Indian languages)
- ✅ **AWS Transcribe** - Accurate speech-to-text (10 Indian languages)
- ✅ **AWS S3** - Secure file storage
- ✅ **AWS DynamoDB** - Fast, scalable database
- ✅ **Response Caching** - Cost optimization
- ✅ **Browser STT Fallback** - Works even without AWS

## 🏗️ Architecture

```
┌─────────────────┐    HTTP/REST    ┌─────────────────┐
│   Frontend      │ ◄──────────────► │   Backend       │
│   (React)       │                 │   (FastAPI)     │
│   Port: 5173    │                 │   Port: 8000    │
└─────────────────┘                 └─────────────────┘
                                            │
                                            ▼
                                    ┌─────────────────┐
                                    │  AWS Services   │
                                    │  • Bedrock      │
                                    │  • Polly        │
                                    │  • Transcribe   │
                                    │  • S3           │
                                    │  • DynamoDB     │
                                    └─────────────────┘
```

## 📁 Project Structure

```
vidhi/
├── vidhi-assistant/          # React Frontend
│   ├── src/
│   │   ├── components/       # UI Components
│   │   ├── pages/           # Pages (Login, Chat, etc.)
│   │   ├── api/             # API Client
│   │   └── utils/           # Utilities
│   ├── package.json
│   └── README.md
│
├── vidhi-backend/           # FastAPI Backend
│   ├── app.py              # Main application
│   ├── configs/            # Configuration
│   ├── services/           # Business logic
│   ├── speech/             # Voice services
│   ├── llm_setup/          # LLM configuration
│   ├── stores/             # Vector stores
│   ├── requirements*.txt   # Dependencies
│   └── README.md
│
├── docs/                   # Documentation
│   ├── COMPLETE_AWS_SETUP_GUIDE.md
│   ├── QUICK_START_REFERENCE.md
│   └── BHASHINI_API_SETUP.md
│
├── README.md              # This file
├── .gitignore            # Git ignore rules
└── LICENSE               # MIT License
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9-3.12 (avoid 3.13 for now)
- Node.js 18+
- AWS Account
- Git

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/vidhi.git
cd vidhi
```

### 2. Setup Backend
```bash
cd vidhi-backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements-windows-minimal.txt

# Configure environment
copy .env.example .env
# Edit .env with your AWS credentials

# Start backend
python app-simple.py
```

### 3. Setup Frontend
```bash
cd vidhi-assistant

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Configure AWS
Follow the detailed guide: [`docs/COMPLETE_AWS_SETUP_GUIDE.md`](docs/COMPLETE_AWS_SETUP_GUIDE.md)

## 🌐 Live Demo

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 💰 Cost Estimate

### Development
- **S3**: $0.50/month
- **DynamoDB**: $1/month  
- **Bedrock**: $2/month
- **Total**: ~$5/month

### Production (1000 users/day)
- **S3**: $15/month
- **DynamoDB**: $30/month
- **Bedrock**: $80/month
- **Polly**: $20/month
- **Transcribe**: $10/month
- **Total**: ~$155/month

*Optimized from original $300/month estimate*

## 🛠️ Development

### Backend Development
```bash
cd vidhi-backend
venv\Scripts\activate
python app.py  # Full version
# or
python app-simple.py  # Minimal version for Python 3.13
```

### Frontend Development
```bash
cd vidhi-assistant
npm run dev
```

### Testing
```bash
# Backend tests
cd vidhi-backend
python test-installation.py

# Frontend tests
cd vidhi-assistant
npm test
```

## 📚 Documentation

### Setup Guides
- [Complete AWS Setup Guide](docs/COMPLETE_AWS_SETUP_GUIDE.md) - Full AWS configuration
- [Quick Start Reference](docs/QUICK_START_REFERENCE.md) - Quick commands
- [Bhashini API Setup](docs/BHASHINI_API_SETUP.md) - Optional dialect support

### Backend Guides
- [Backend Installation](vidhi-backend/INSTALLATION_STEPS.md) - Step-by-step setup
- [Windows Setup](vidhi-backend/WINDOWS_SETUP.md) - Windows-specific instructions
- [Commands Reference](vidhi-backend/COMMANDS.md) - All commands in one place

### Architecture
- [AWS Architecture](vidhi-assistant/AWS_ARCHITECTURE.md) - Cloud architecture
- [Simple Architecture](vidhi-backend/ARCHITECTURE_SIMPLE.md) - Visual overview

## 🌍 Supported Languages

### AWS Polly (Premium Quality)
- Hindi (hi-IN) - Kajal (Neural)
- Bengali (bn-IN) - Tanishaa (Neural)
- English (en-IN) - Kajal (Neural)
- Tamil (ta-IN) - Shruti (Neural)
- Telugu (te-IN) - Salli (Neural)
- Malayalam (ml-IN) - Raveena (Neural)
- Kannada (kn-IN) - Salli (Neural)

### AWS Transcribe (Speech Recognition)
- Hindi, Bengali, Tamil, Telugu, Marathi
- Gujarati, Kannada, Malayalam, Punjabi, English

### Bhashini (Regional Dialects) - Optional
- Bhojpuri, Maithili, Awadhi
- Additional dialects as available

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues
- **Installation Problems**: See [`vidhi-backend/QUICK_FIX.md`](vidhi-backend/QUICK_FIX.md)
- **AWS Configuration**: See [`docs/COMPLETE_AWS_SETUP_GUIDE.md`](docs/COMPLETE_AWS_SETUP_GUIDE.md)
- **Python 3.13 Issues**: Use `app-simple.py` and `requirements-ultra-minimal.txt`

### Get Help
- 📖 Check documentation in `/docs` folder
- 🐛 Open an issue for bugs
- 💡 Open an issue for feature requests
- 📧 Contact: [your-email@example.com]

## 🎯 Roadmap

### Phase 1 (Current)
- ✅ Core chat functionality
- ✅ Voice input/output
- ✅ Multi-language support
- ✅ AWS integration

### Phase 2 (Next)
- 🔄 Mobile app (React Native)
- 🔄 Offline mode
- 🔄 Advanced document analysis
- 🔄 Integration with legal databases

### Phase 3 (Future)
- 📋 Court case tracking
- 📋 Lawyer directory
- 📋 Legal form generation
- 📋 Video consultations

## 🏆 Awards & Recognition

- 🥇 Built for Indian legal system
- 🌟 Supports 22+ Indian languages
- 🚀 Production-ready architecture
- 💰 Cost-optimized for scale

---

**Made with ❤️ for Indian Citizens**

*Empowering every citizen with accessible legal knowledge*