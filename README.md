# Email Scheduler

Welcome to **Email Scheduler**! This is a simple web application that lets you schedule emails to be sent automatically, even if you have no idea how programming works. You can send emails to many people, set them to repeat, and keep your data private.

---

## What does this app do?

- Lets you schedule emails to be sent later, or on a repeating schedule (like every day, week, month, etc).
- You can send to one or many email addresses at once.
- You log in with your Google account (so you don’t have to remember another password).
- Your messages and (optionally) the recipient addresses can be hashed, so nobody can read them except the sender and receiver.
- You get a simple, modern web page to manage everything.
- All your actions are logged to a file for troubleshooting (but you can ignore this if you don’t care).

---

## Features (in plain English)

- **Schedule emails**: Pick a time and date, and your email will be sent automatically.
- **Send to many people**: Just type in all the email addresses you want (separated by comma, space, or new line).
- **Repeat sending**: Want to send a reminder every week? You can!
- **Google login**: Safe and easy. No new passwords to remember.
- **Privacy**: You can choose to hash (scramble) your message and/or the recipient addresses.
- **Easy to use**: The web page is simple and works on your phone or computer.
- **Free and open source**: No hidden fees, no tricks.

---

## How do I use it? (Step by step, for total beginners)

### 1. Install Python
If you don’t have Python, download it from [python.org](https://www.python.org/downloads/). Install Python 3.8 or newer.

### 2. Download the code
Clone this repository from GitHub, or download the ZIP and extract it.

### 3. Open a terminal (Command Prompt, PowerShell, or Terminal app)
Navigate to the project folder (the one with `requirements.txt` in it).

### 4. Install the required Python packages
Type this and press Enter:
```
pip install -r requirements.txt
```

### 5. Set up Google login (OAuth)
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project (if you don’t have one)
- Enable the Gmail API
- Create OAuth 2.0 credentials (Client ID and Secret)
- Download the credentials or copy the values
- Set them as environment variables, or put them in a `.env` file (see `.env.example`)

### 6. Run the app
Type this and press Enter:
```
python -m src.app
```

### 7. Open the app in your browser
Go to [http://localhost:5000](http://localhost:5000)

### 8. Log in with Google and start scheduling emails!

---

## Where do I see logs?
- All logs (errors, info, etc.) are saved in a file called `app.log` in your project folder.
- If you don’t care, you can ignore it. If you want to see what happened, just open `app.log` with any text editor.
- **Never upload `app.log` to GitHub!**

## Where is my data stored?
- All scheduled jobs are saved in a file called `jobs.db` (an SQLite database).
- This file is only for your use. **Never upload `jobs.db` to GitHub!**

---

## Deployment (for advanced users)
- Push your code to GitHub
- Deploy backend to Render.com, Railway, or similar free service
- (Optional) Use GitHub Actions for scheduled jobs

---

## Project Folder Structure (what’s in here?)
```
email-scheduler/
├── src/
│   ├── app.py           # Main app code
│   ├── auth/            # Google login code
│   ├── email/           # Email sending and validation
│   ├── models/          # Database models
│   └── scheduler/       # Scheduling logic
├── requirements.txt     # List of Python packages you need
├── .gitignore           # Tells git to ignore log and database files
├── README.md            # This file
├── templates/           # HTML files for the web interface
│   └── index.html
├── static/              # CSS and static files
│   └── style.css
├── jobs.db (ignored)    # Your data (never upload)
├── app.log (ignored)    # Log file (never upload)
```

---

## FAQ (for the truly lost)

**Q: I see `app.log` and `jobs.db`. Should I upload them to GitHub?**
A: No! These files are for your computer only. They are ignored by git.

**Q: I get an error about missing packages.**
A: Make sure you ran `pip install -r requirements.txt` in the project folder.

**Q: I get an error about Google credentials.**
A: You need to set up Google OAuth and put your credentials in a `.env` file or as environment variables.

**Q: I don’t know how to use the terminal.**
A: Search for “how to open terminal on [your operating system]” and follow the steps above.

**Q: I broke something.**
A: Delete `jobs.db` and `app.log` and start over, or ask for help on GitHub.

---

## License
MIT. Do whatever you want, but don’t blame me if you break something.
