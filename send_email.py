import os
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import markdown

def send_email(subject, body, to_email, from_email, password, smtp_server, smtp_port):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    # Convert Markdown to HTML
    html_body = markdown.markdown(body)

    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    parser = argparse.ArgumentParser(description="Send email with markdown content.")
    parser.add_argument("--file", type=str, required=True, help="Path to markdown file")
    parser.add_argument("--subject", type=str, default="Daily Paper Feed", help="Email subject")
    args = parser.parse_args()

    from_email = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    to_email = os.environ.get("EMAIL_RECEIVER", from_email)
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    if not from_email or not password:
        print("Error: EMAIL_SENDER and EMAIL_PASSWORD environment variables must be set.")
        return

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            body = f.read()
    except FileNotFoundError:
        print(f"Error: File {args.file} not found.")
        return

    send_email(args.subject, body, to_email, from_email, password, smtp_server, smtp_port)

if __name__ == "__main__":
    main()
