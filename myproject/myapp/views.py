from django.http import HttpResponse
import imaplib
import secrets
from django.shortcuts import render
from django.core.files.base import ContentFile 
from myapp.models import * 
from django.shortcuts import redirect, render,get_object_or_404
from datetime import datetime
from django.contrib.auth import authenticate,login, update_session_auth_hash
import imaplib
import email
from email.header import decode_header
import secrets
from django.conf import settings
from django.core.paginator import Paginator  

# Create your views here.



MY_EMAIL = settings.EMAIL_ACCOUNT
MY_PASSWORD = settings.EMAIL_APP_PASSWORD
 
 

def login_page(request):

    if request.method == "POST":
        entered_email = request.POST.get("entered_email")
        entered_password = request.POST.get("password")

        if entered_email == MY_EMAIL and entered_password == MY_PASSWORD:
            request.session["token"] = secrets.token_hex(16)
            request.session["role"] = "admin"
            return redirect("inbox")
        staff = Staff.objects.filter(email=entered_email).first()

        if staff:
            request.session["staff_email"] = staff.email
            request.session["role"] = "staff"
            return redirect("staff_asigned_ticket")
        
        return render(request, "login.html", {
            "error": "Invalid Email or Password"
        })

    return render(request, "login.html")
 
def inbox(request):
 
    if not request.session.get("token"):
        return redirect("login")
 
    if request.method == "POST" and request.POST.get("fetch") == "1":
        try:
            mail_conn = imaplib.IMAP4_SSL("imap.gmail.com")
            mail_conn.login(MY_EMAIL, MY_PASSWORD)
            mail_conn.select("inbox")
 
            status, messages = mail_conn.search(None, "ALL")
            email_ids = messages[0].split()
 
            emails = []
 
            for mail_id in reversed(email_ids[-20:]):
 
                status, msg_data = mail_conn.fetch(mail_id, "(RFC822)")
 
                for response_part in msg_data:
                    if not isinstance(response_part, tuple):
                        continue
 
                    msg = email.message_from_bytes(response_part[1])
 
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")
 
                    from_email = msg.get("From")
                    date = msg.get("Date")
 
                    text_body = ""
                    html_body = ""
                    attachments = []
 
                    mail_id_str = mail_id.decode()
 
                    # ── Parse email parts ──
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition", ""))
 
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    text_body = part.get_payload(decode=True).decode(errors="ignore")
                                except:
                                    pass
 
                            elif content_type == "text/html" and "attachment" not in content_disposition:
                                try:
                                    html_body = part.get_payload(decode=True).decode(errors="ignore")
                                except:
                                    pass
 
                            elif "attachment" in content_disposition or part.get_filename():
                                filename = part.get_filename()
                                if filename:
                                    file_data = part.get_payload(decode=True)
                                    attachments.append({
                                        "filename": filename,
                                        "content_type": content_type,
                                        "data": file_data,
                                    })
                    else:
                        try:
                            text_body = msg.get_payload(decode=True).decode(errors="ignore")
                        except:
                            pass
 
                    # ── Get or create ticket ──
                    ticket, created = Ticket.objects.get_or_create(
                        mail_id=mail_id_str,
                        defaults={
                            "subject": subject,
                            "sender": from_email,
                            "date": date,
                            "body": text_body or html_body,
                        }
                    )
 
                    # ── Save attachments (avoid duplicates) ──
                    for att in attachments:
                        if not ticket.attachments.filter(filename=att["filename"]).exists():
                            TicketAttachment.objects.create(
                                ticket=ticket,
                                filename=att["filename"],
                                content_type=att["content_type"],
                                file=ContentFile(att["data"], name=att["filename"]),
                            )
 
                    emails.append({
                        "id":          mail_id_str,
                        "subject":     subject,
                        "sender":      from_email,
                        "date":        date,
                        "body":        (text_body or html_body)[:300],
                        "ticket":      ticket.ticket_number,
                        "status":      ticket.status,
                        "assigned_to": ticket.assigned_to.name if ticket.assigned_to else None,
                    })
 
            mail_conn.logout()
 
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
 
 
def email_detail(request, mail_id):
 
    if not request.session.get("token"):
        return redirect("login")
 
    try:
        mail_conn = imaplib.IMAP4_SSL("imap.gmail.com")
        mail_conn.login(MY_EMAIL, MY_PASSWORD)
        mail_conn.select("inbox")
 
        status, msg_data = mail_conn.fetch(mail_id, "(RFC822)")
 
        subject = ""
        from_email = ""
        date = ""
        text_body = ""
        html_body = ""
        attachments = []
 
        for response_part in msg_data:
            if not isinstance(response_part, tuple):
                continue
 
            msg = email.message_from_bytes(response_part[1])
 
            subject, encoding = decode_header(msg.get("Subject"))[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="ignore")
 
            from_email = msg.get("From")
            date = msg.get("Date")
 
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
 
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            text_body = part.get_payload(decode=True).decode(errors="ignore")
                        except:
                            pass
 
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        try:
                            html_body = part.get_payload(decode=True).decode(errors="ignore")
                        except:
                            pass
 
                    elif "attachment" in content_disposition or part.get_filename():
                        filename = part.get_filename()
                        if filename:
                            file_data = part.get_payload(decode=True)
                            attachments.append({
                                "filename": filename,
                                "content_type": content_type,
                                "data": file_data,
                            })
            else:
                try:
                    text_body = msg.get_payload(decode=True).decode(errors="ignore")
                except:
                    pass
 
        mail_conn.logout()
 
        # ── Ensure ticket exists ──
        ticket, created = Ticket.objects.get_or_create(
            mail_id=mail_id,
            defaults={
                "subject": subject,
                "sender": from_email,
                "date": date,
                "body": text_body or html_body,
            }
        )
 
        # ── Save attachments (avoid duplicates) ──
        for att in attachments:
            if not ticket.attachments.filter(filename=att["filename"]).exists():
                TicketAttachment.objects.create(
                    ticket=ticket,
                    filename=att["filename"],
                    content_type=att["content_type"],
                    file=ContentFile(att["data"], name=att["filename"]),
                )
 
        all_staff = Staff.objects.all()
 
        # Strip all <img> tags from html_body to prevent broken external images
        import re as _re
        safe_html = _re.sub(r'<img[^>]*>', '', html_body, flags=_re.IGNORECASE) if html_body else ""
 
        return render(request, "email_detail.html", {
            "subject":    subject,
            "from_email": from_email,
            "date":       date,
            "body":       text_body,   # plain text — preferred
            "html_body":  safe_html,   # html with <img> stripped
            "ticket":     ticket,
            "all_staff":  all_staff,
        })
 
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")
 
 
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
        elif status_val in dict(Ticket.STATUS_CHOICES):
            # Only update status manually if no staff assignment is happening
            ticket.status = status_val

        ticket.save()

    return redirect("email_detail", mail_id=ticket.mail_id)
 

def logout_page(request):
    request.session.flush()
    return redirect("login")

def staff_asigned_ticket(request):
    staff_email=request.session.get('staff_email')
    if not staff_email:
        return redirect("login")
    staff = get_object_or_404(Staff, email=staff_email)

    tickets = Ticket.objects.filter(assigned_to=staff)

    return render(request, "staff_asigned_ticket.html", {
        "tickets": tickets,
        "staff": staff
    })

def staff_ticket_detail(request, ticket_id):
    staff_email = request.session.get("staff_email")
 
    if not staff_email:
        return redirect("login")
 
    staff = get_object_or_404(Staff, email=staff_email)
    ticket = get_object_or_404(Ticket, id=ticket_id, assigned_to=staff)

    if request.method == "POST":
        if request.POST.get("action") == "close":
            ticket.status = "closed"
            ticket.save()
            return redirect("staff_asigned_ticket")
 
    return render(request, "staff_ticket_detail.html", {
        "ticket": ticket,
        "attachments": ticket.attachments.all(),
    })

def ticket_list(request):
    if not request.session.get("token"):
        return redirect("login")
 
    from django.core.paginator import Paginator
 
    # ── Unassigned ──
    unassigned_qs = Ticket.objects.filter(status="unassigned")
    unassigned_page = request.GET.get("unassigned_page", 1)
    unassigned_paginator = Paginator(unassigned_qs, 10)
    unassigned_tickets = unassigned_paginator.get_page(unassigned_page)
 
    # ── Assigned ──
    assigned_qs = Ticket.objects.filter(status="assigned")
    assigned_page = request.GET.get("assigned_page", 1)
    assigned_paginator = Paginator(assigned_qs, 10)
    assigned_tickets = assigned_paginator.get_page(assigned_page)
 
    # ── Closed ──
    closed_qs = Ticket.objects.filter(status="closed")
    closed_page = request.GET.get("closed_page", 1)
    closed_paginator = Paginator(closed_qs, 10)
    closed_tickets = closed_paginator.get_page(closed_page)
 
    return render(request, "ticket_list.html", {
        "unassigned_tickets": unassigned_tickets,
        "assigned_tickets":   assigned_tickets,
        "closed_tickets":     closed_tickets,
    })