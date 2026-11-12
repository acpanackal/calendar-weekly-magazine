from __future__ import annotations

import html
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else value


def parse_event_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_calendar_service() -> Any:
    service_account_path = setting("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_path and Path(service_account_path).is_file():
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    token_path = BASE_DIR / "token.json"
    oauth_path = BASE_DIR / "credentials.json"
    credentials: Credentials | None = None
    if token_path.is_file():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not oauth_path.is_file():
                raise FileNotFoundError(
                    "Google credentials unavailable. Configure GOOGLE_APPLICATION_CREDENTIALS "
                    "for a service account, or add credentials.json for local OAuth."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(oauth_path), SCOPES)
            credentials = flow.run_local_server(port=0)
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def list_upcoming_events(days_ahead: int = 7) -> list[dict[str, Any]]:
    if days_ahead < 1:
        raise ValueError("DAYS_AHEAD must be at least 1.")

    service = get_calendar_service()
    now = datetime.now(timezone.utc)
    response = (
        service.events()
        .list(
            calendarId=setting("GOOGLE_CALENDAR_ID", "primary"),
            timeMin=now.isoformat(),
            timeMax=(now + timedelta(days=days_ahead)).isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=2500,
        )
        .execute()
    )

    events = []
    for event in response.get("items", []):
        start = event.get("start", {})
        end = event.get("end", {})
        events.append(
            {
                "title": event.get("summary") or "Untitled event",
                "description": event.get("description") or "",
                "location": event.get("location") or "",
                "start": parse_event_time(start.get("dateTime") or start.get("date")),
                "end": parse_event_time(end.get("dateTime") or end.get("date")),
                "all_day": "date" in start,
                "calendar_link": event.get("htmlLink") or "",
            }
        )

    def sort_key(event: dict[str, Any]) -> float:
        value = event["start"]
        if value is None:
            return float("inf")
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()

    return sorted(events, key=sort_key)


def format_date(value: datetime | None, include_time: bool = True) -> str:
    if value is None:
        return "Date to be confirmed"
    if include_time:
        return value.strftime("%a, %b %d · %I:%M %p").replace(" 0", " ")
    return value.strftime("%A, %b %d")


def make_event_cards(events: list[dict[str, Any]]) -> str:
    if not events:
        return '<div class="empty-state"><p>No upcoming events this week. Enjoy the breathing room.</p></div>'

    cards = []
    for index, event in enumerate(events, start=1):
        start, end = event["start"], event["end"]
        if event["all_day"]:
            time_label = "All day"
        elif start and end and start.date() == end.date():
            time_label = f"{start.strftime('%I:%M %p').lstrip('0')} – {end.strftime('%I:%M %p').lstrip('0')}"
        elif start and end:
            time_label = f"{format_date(start)} – {format_date(end)}"
        else:
            time_label = format_date(start)

        description = html.escape(event["description"][:220])
        location = html.escape(event["location"])
        description_html = f'<p class="event-description">{description}</p>' if description else ""
        location_html = f'<p class="event-location">📍 {location}</p>' if location else ""
        link = html.escape(event["calendar_link"], quote=True)
        link_html = f'<a class="event-link" href="{link}">Open in Google Calendar →</a>' if link else ""
        cards.append(
            f'''<article class="event-card">
              <div class="event-index">{index:02d}</div>
              <div class="event-content">
                <p class="event-date">{html.escape(format_date(start, include_time=False))}</p>
                <h3>{html.escape(event["title"])}</h3>
                <p class="time-line">🕒 {html.escape(time_label)}</p>
                {description_html}{location_html}{link_html}
              </div>
            </article>'''
        )
    return "\n".join(cards)


def render_email_html(events: list[dict[str, Any]]) -> str:
    template = (BASE_DIR / "templates" / "email_template.html").read_text(encoding="utf-8")
    title = html.escape(setting("MAGAZINE_TITLE", "The Week Ahead") or "The Week Ahead")
    issue_date = html.escape(datetime.now().strftime("%B %d, %Y"))
    return (
        template.replace("{{MAGAZINE_TITLE}}", title)
        .replace("{{ISSUE_DATE}}", issue_date)
        .replace("{{EVENT_COUNT}}", str(len(events)))
        .replace("{{EVENT_CARDS}}", make_event_cards(events))
    )


def send_email(subject: str, html_body: str) -> None:
    required = ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]
    missing = [name for name in required if not setting(name)]
    if missing:
        raise ValueError("Missing email configuration: " + ", ".join(missing))

    recipients = [address.strip() for address in (setting("EMAIL_TO") or "").split(",") if address.strip()]
    if not recipients:
        raise ValueError("EMAIL_TO must contain at least one recipient.")

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = setting("EMAIL_FROM")
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText("Your email client does not support HTML email.", "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    host = setting("SMTP_HOST") or ""
    port = int(setting("SMTP_PORT", "587") or "587")
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        if (setting("SMTP_USE_TLS", "true") or "true").lower() == "true":
            server.starttls()
            server.ehlo()
        server.login(setting("SMTP_USERNAME") or "", setting("SMTP_PASSWORD") or "")
        server.sendmail(setting("EMAIL_FROM") or "", recipients, message.as_string())


def main() -> None:
    days_ahead = int(setting("DAYS_AHEAD", "7") or "7")
    events = list_upcoming_events(days_ahead)
    title = setting("MAGAZINE_TITLE", "The Week Ahead") or "The Week Ahead"
    subject = f"{title} · {datetime.now().strftime('%b %d, %Y')}"
    send_email(subject, render_email_html(events))
    print(f"Sent weekly digest with {len(events)} event(s).")


if __name__ == "__main__":
    main()
