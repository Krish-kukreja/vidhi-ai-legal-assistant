# VIDHI - Fresh Laptop Setup Guide

Welcome to VIDHI! If you are setting this up on a completely blank laptop with NO dependencies, follow these exact steps from top to bottom.

---

## 1. Prerequisites (Install These First)
Before touching any code, you must install the core structural languages:

1.  **Git:** Download and install from [git-scm.com](https://git-scm.com/). (Allows you to clone this code).
2.  **Node.js (for the Frontend):** Download and install the LTS version from [nodejs.org](https://nodejs.org/). This gives you `npm`.
3.  **Python (for the Backend):** Download and install Python 3.11 or newer from [python.org](https://www.python.org/downloads/).
    *   **CRITICAL WINDOWS STEP:** During the Python installation, check the box at the very bottom that says **"Add python.exe to PATH"**.

---

## 2. Get the Code
Open your terminal (Command Prompt or PowerShell) and run:
```bash
git clone https://github.com/YOUR_USERNAME/vidhi.git
cd vidhi
```
*(Replace YOUR_USERNAME with your actual GitHub username).*

---

## 3. Setup the Frontend (React / Vite)
Open a new terminal window inside the `vidhi` folder:

```bash
# 1. Go into the frontend folder
cd vidhi-assistant

# 2. Install all the necessary packages
npm install

# 3. Start the development server
npm run dev
```
The frontend should now be running at `http://localhost:8081`. Keep this terminal open!

---

## 4. Setup the Backend (Python / FastAPI)
Open a **second** new terminal window inside the `vidhi` folder:

```bash
# 1. Go into the backend folder
cd vidhi-backend

# 2. Create a virtual environment (keeps dependencies isolated)
python -m venv venv

# 3. Activate the virtual environment
# -> On Windows:
venv\Scripts\activate
# -> On Mac/Linux:
source venv/bin/activate

# 4. Install all the required Python packages
pip install -r requirements.txt

# 5. Start the backend server
uvicorn app-simple:app --reload --port 8000
```
The backend should now be running at `http://localhost:8000`.

---

## 5. You're Done!
Open your browser and navigate to `http://localhost:8081`. The VIDHI app is now fully functional on your new laptop!

### 6. Connect your AWS IAM User (Required for the AI)
The user account you created yesterday in AWS is necessary to give the backend permission to use Bedrock (Claude) and Polly (Voice).

1. In your `vidhi-backend` folder on the new laptop, create a new file named exactly `.env` (don't forget the dot!).
2. Open the file and paste your credentials like this:
```env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=ap-south-1
```
3. Save the file.
4. Restart your `uvicorn` backend server. It will automatically read those keys and the AI will wake up!
