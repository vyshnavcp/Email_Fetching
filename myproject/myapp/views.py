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
 
 
# ── LOGIN ────────────────────────────────────────────────
def login_page(request):
 
    if request.method == "POST":
        entered_email    = request.POST.get("entered_email")
        entered_password = request.POST.get("password")
 
        if entered_email == MY_EMAIL and entered_password == MY_PASSWORD:
            request.session["token"] = secrets.token_hex(16)
            return redirect("inbox")
 
        return render(request, "login.html", {
            "error": "Invalid Email or Password"
        })
 
    return render(request, "login.html")
 
 
# ── INBOX ────────────────────────────────────────────────
def inbox(request):
 
    if not request.session.get("token"):
        return redirect("login")
 
    if request.method == "POST" and request.POST.get("fetch") == "1":
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
                        date       = msg.get("Date")
                        body       = ""
 
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
 
                        mail_id_str = mail_id.decode()
 
                        # ── Create ticket on first fetch, reuse on repeat ──
                        ticket, _ = Ticket.objects.get_or_create(
                            mail_id=mail_id_str,
                            defaults={
                                "subject": subject,
                                "sender":  from_email,
                                "date":    date,
                                "body":    body,
                            }
                        )
 
                        emails.append({
                            "id":      mail_id_str,
                            "subject": subject,
                            "from":    from_email,
                            "date":    date,
                            "body":    body[:300],
                            "ticket":  ticket.ticket_number,   # always a real TKT-XXXX now
                        })
 
            mail.logout()
 
            return render(request, "inbox.html", {
                "emails":  emails,
                "fetched": True,
            })
 
        except Exception as e:
            return render(request, "inbox.html", {
                "error":   str(e),
                "fetched": True,
            })
 
    return render(request, "inbox.html", {
        "emails":  [],
        "fetched": False,
    })
 
 
# ── EMAIL DETAIL ─────────────────────────────────────────
def email_detail(request, mail_id):
 
    if not request.session.get("token"):
        return redirect("login")
 
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(MY_EMAIL, MY_PASSWORD)
        mail.select("inbox")
 
        status, msg_data = mail.fetch(mail_id, "(RFC822)")
 
        subject = from_email = date = body = ""
 
        for response_part in msg_data:
            if isinstance(response_part, tuple):
 
                msg = email.message_from_bytes(response_part[1])
 
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
 
                from_email = msg.get("From")
                date       = msg.get("Date")
 
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
 
        # Ticket already exists from inbox fetch; get_or_create is just a safety net
        ticket, _ = Ticket.objects.get_or_create(
            mail_id=mail_id,
            defaults={
                "subject": subject,
                "sender":  from_email,
                "date":    date,
                "body":    body,
            }
        )
 
        all_staff = Staff.objects.all()
 
        return render(request, "email_detail.html", {
            "subject":   subject,
            "from":      from_email,
            "date":      date,
            "body":      body,
            "ticket":    ticket,
            "all_staff": all_staff,
        })
 
    except Exception as e:
        return HttpResponse(str(e))
 
 
# ── ASSIGN TICKET ─────────────────────────────────────────
def assign_ticket(request, ticket_id):
 
    if not request.session.get("token"):
        return redirect("login")
 
    ticket = get_object_or_404(Ticket, id=ticket_id)
 
    if request.method == "POST":
        staff_id   = request.POST.get("staff_id")
        status_val = request.POST.get("status")
 
        if staff_id:
            ticket.assigned_to = get_object_or_404(Staff, id=staff_id)
            ticket.status = "assigned"
 
        if status_val in dict(Ticket.STATUS_CHOICES):
            ticket.status = status_val
 
        ticket.save()
 
    return redirect("email_detail", mail_id=ticket.mail_id)
 
 
# ── LOGOUT ────────────────────────────────────────────────
def logout_page(request):
    request.session.flush()
    return redirect("login")
