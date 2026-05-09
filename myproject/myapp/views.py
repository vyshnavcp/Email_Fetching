from django.http import HttpResponse
import imaplib
import secrets
from django.shortcuts import render
from myapp.models import * 
from django.shortcuts import redirect, render,get_object_or_404
from datetime import datetime
from django.contrib.auth import authenticate,login, update_session_auth_hash
import imaplib
import email
from email.header import decode_header
import secrets
from django.conf import settings
# Create your views here.

MY_EMAIL = settings.EMAIL_ACCOUNT
MY_PASSWORD = settings.EMAIL_APP_PASSWORD


# LOGIN PAGE
def login_page(request):

    if request.method == "POST":

        entered_email = request.POST.get("entered_email")
        entered_password = request.POST.get("password")

        if entered_email == MY_EMAIL and entered_password == MY_PASSWORD:

            token = secrets.token_hex(16)

            # SAVE TOKEN
            request.session["token"] = token

            return redirect("inbox")

        else:

            return render(request, "myapp/login.html", {
                "error": "Invalid Email or Password"
            })

    return render(request, "login.html")


def inbox(request):

    # CHECK TOKEN
    if not request.session.get("token"):

        return redirect("login")

    try:

        mail = imaplib.IMAP4_SSL("imap.gmail.com")

        mail.login(MY_EMAIL, MY_PASSWORD)

        mail.select("inbox")

        status, messages = mail.search(None, "ALL")

        email_ids = messages[0].split()

        emails = []

        for mail_id in reversed(email_ids[-20:]):

            status, msg_data = mail.fetch(mail_id, "(RFC822)")

            for response_part in msg_data:

                if isinstance(response_part, tuple):

                    msg = email.message_from_bytes(response_part[1])

                    subject, encoding = decode_header(msg["Subject"])[0]

                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    from_email = msg.get("From")

                    date = msg.get("Date")

                    body = ""

                    # GET BODY
                    if msg.is_multipart():

                        for part in msg.walk():

                            content_type = part.get_content_type()

                            if content_type == "text/plain":

                                try:
                                    body = part.get_payload(decode=True).decode()
                                    break
                                except:
                                    pass

                    else:

                        try:
                            body = msg.get_payload(decode=True).decode()
                        except:
                            body = ""

                    emails.append({
                        "id": mail_id.decode(),
                        "subject": subject,
                        "from": from_email,
                        "date": date,
                        "body": body[:300]
                    })

        mail.logout()

        return render(request, "inbox.html", {
            "emails": emails
        })

    except Exception as e:

        return render(request, "inbox.html", {
            "error": str(e)
        })
def email_detail(request, mail_id):

    if not request.session.get("token"):
        return redirect("login")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(MY_EMAIL, MY_PASSWORD)
        mail.select("inbox")

        status, msg_data = mail.fetch(mail_id, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):

                msg = email.message_from_bytes(response_part[1])

                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")

                from_email = msg.get("From")
                date = msg.get("Date")

                body = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        body = ""

        mail.logout()

        return render(request, "email_detail.html", {
            "subject": subject,
            "from": from_email,
            "date": date,
            "body": body
        })

    except Exception as e:
        return HttpResponse(str(e))

def logout_page(request):

    request.session.flush()

    return redirect("login")
    