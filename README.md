# Weekly Calendar Magazine

A Python app that pulls upcoming Google Calendar events, turns them into a polished weekly digest, and emails the result to your inbox.

## Features
- Reads upcoming events from Google Calendar
- Filters events for the next 7 days
- Formats them into a magazine-style HTML email
- Sends the digest through SMTP (Gmail or any SMTP provider)
- Can be scheduled weekly with GitHub Actions

## Project structure

```text
.
├── app.py
├── .env.example
├── .gitignore
├── requirements.txt
├── templates/
│   └── email_template.html
├── .github/
│   └── workflows/
│       └── weekly_magazine.yml
├── README.md
├── credentials.json   # optional for OAuth setup
├── token.json         # generated locally when using OAuth
└── google-service-account.json  # optional for service account setup
```

## Setup

1. Clone the repository
2. Create a virtual environment
3. Install dependencies
4. Copy `.env.example` to `.env` and fill in your values
5. Run the app

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## Required configuration

### Google Calendar access
There are two common ways to connect the app to Google Calendar:

1. Service account (recommended for automation)
2. OAuth local credentials (simpler to test locally)

### Example `.env`

```env
GOOGLE_CALENDAR_ID=primary
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=your-email@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
DAYS_AHEAD=7
MAGAZINE_TITLE=Weekly Calendar Digest
```

## Google Calendar setup

### Option 1: Service account
1. Create a Google Cloud project
2. Enable the Google Calendar API
3. Create a service account and download the JSON key
4. Share the target calendar with the service account email
5. Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json`

### Option 2: OAuth
1. Enable the Google Calendar API in Google Cloud Console
2. Download `credentials.json`
3. Run the app once to generate `token.json`

## Gmail SMTP setup

For Gmail, use an App Password:
- Enable 2-Step Verification
- Create an App Password
- Set `SMTP_HOST=smtp.gmail.com`
- Set `SMTP_PORT=587`
- Set `SMTP_USE_TLS=true`

## Weekly automation

The included GitHub Actions workflow runs every Monday at 09:00 UTC and can be triggered manually.

Set the following repository secrets in GitHub:
- `GOOGLE_CALENDAR_ID`
- `GOOGLE_APPLICATION_JSON` (optional if using service account)
- `EMAIL_FROM`
- `EMAIL_TO`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `MAGAZINE_TITLE`
- `DAYS_AHEAD`

## Notes
- If there are no upcoming events, the email still sends with a "No upcoming events" message.
- The HTML email is styled to look like a magazine feature layout.

## License

MIT
