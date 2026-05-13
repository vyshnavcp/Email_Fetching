from django.template.loader import render_to_string
from myapp.models import SentEmail
from django.http import JsonResponse
from urllib.request import Request
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
import email as _email
import re as _re
from email.header import decode_header
from django.db.models import Q
from django.core.mail import EmailMessage

# Create your views here.

MY_EMAIL = settings.EMAIL_HOST_USER
MY_PASSWORD = settings.EMAIL_HOST_PASSWORD

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
            if staff.status == "inactive":
                return render(request, "login.html", {
                    "error": "Your account is inactive"})
            if staff.check_password(entered_password):
                request.session["staff_id"] = staff.id
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
                    ticket, created = Ticket.objects.get_or_create(
                        mail_id=mail_id_str,
                        defaults={
                            "subject": subject,
                            "sender": from_email,
                            "date": date,
                            "body": text_body or html_body,
                        }
                    )
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
    is_manual = not mail_id.isdigit()
    if is_manual:
        ticket = get_object_or_404(Ticket, mail_id=mail_id)
        all_staff = Staff.objects.all()

        return render(request, "email_detail.html", {
            "subject":    ticket.subject,
            "from_email": ticket.sender,
            "date":       ticket.date,
            "body":       ticket.body,
            "html_body":  "",
            "has_html":   False,
            "ticket":     ticket,
            "all_staff":  all_staff,
        })
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

        ticket, created = Ticket.objects.get_or_create(
            mail_id=mail_id,
            defaults={
                "subject": subject,
                "sender": from_email,
                "date": date,
                "body": text_body or html_body,
            }
        )

        for att in attachments:
            if not ticket.attachments.filter(filename=att["filename"]).exists():
                TicketAttachment.objects.create(
                    ticket=ticket,
                    filename=att["filename"],
                    content_type=att["content_type"],
                    file=ContentFile(att["data"], name=att["filename"]),
                )

        all_staff = Staff.objects.all()

        safe_html = ""
        if html_body:
            safe_html = _re.sub(r'<img[^>]*>', '', html_body, flags=_re.IGNORECASE)

        return render(request, "email_detail.html", {
            "subject":    subject,
            "from_email": from_email,
            "date":       date,
            "body":       text_body,
            "html_body":  safe_html,
            "has_html":   bool(safe_html.strip()),
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
        staff_id = request.POST.get("staff_id")

        old_staff = ticket.assigned_to

        if staff_id:
            new_staff = get_object_or_404(Staff, id=staff_id)
            ticket.assigned_to = new_staff
            ticket.status = "assigned"
            ticket.save()

            # 🟢 HISTORY LOGIC
            if not old_staff:
                TicketHistory.objects.create(
                    ticket=ticket,
                    staff=new_staff,
                    action="assigned",
                    description=f"Assigned to {new_staff.name}"
                )
            else:
                TicketHistory.objects.create(
                    ticket=ticket,
                    staff=new_staff,
                    action="reassigned",
                    description=f"Reassigned from {old_staff.name} to {new_staff.name}"
                )

    return redirect("email_detail", mail_id=ticket.mail_id)
 

def logout_page(request):
    request.session.flush()
    return redirect("login")

def staff_asigned_ticket(request):
    staff_id = request.session.get("staff_id")

    if not staff_id:
        return redirect("login")

    staff = get_object_or_404(Staff,id=staff_id )
    tickets = Ticket.objects.filter(assigned_to=staff)
    return render(request, "staff_asigned_ticket.html", {
        "tickets": tickets,
        "staff": staff
    })


def staff_ticket_detail(request, ticket_id):
    staff_email = request.session.get("staff_email")
    if not staff_email:
        return redirect("login")
 
    staff  = get_object_or_404(Staff, email=staff_email)
    ticket = get_object_or_404(Ticket, id=ticket_id, assigned_to=staff)
 
    if request.method == "POST":
 
        if request.POST.get("action") == "close":
            ticket.status = "closed"
            ticket.save()
            return redirect("staff_asigned_ticket")
 
        if request.POST.get("action") == "add_note":
            note_text = request.POST.get("note", "").strip()
            if note_text:
                TicketNote.objects.create(ticket=ticket, staff=staff, note=note_text)
                TicketHistory.objects.create(
                    ticket=ticket, staff=staff,
                    action="note", description=note_text,
                )
            return redirect("staff_ticket_detail", ticket_id=ticket.id)
 
        if request.POST.get("action") == "edit_note":
            note_id  = request.POST.get("note_id")
            new_text = request.POST.get("note", "").strip()
            note = get_object_or_404(TicketNote, id=note_id, staff=staff)
            note.note = new_text
            note.save()
            return redirect("staff_ticket_detail", ticket_id=ticket.id)
    html_body  = ""
    text_body  = ticket.body or ""  
 
    try:
        mail_conn = imaplib.IMAP4_SSL("imap.gmail.com")
        mail_conn.login(MY_EMAIL, MY_PASSWORD)
        mail_conn.select("inbox")
        status, msg_data = mail_conn.fetch(str(ticket.mail_id), "(RFC822)")
 
        for part in msg_data:
            if not isinstance(part, tuple):
                continue
 
            msg = _email.message_from_bytes(part[1])
 
            if msg.is_multipart():
                for mp in msg.walk():
                    ct   = mp.get_content_type()
                    disp = str(mp.get("Content-Disposition", ""))
                    if ct == "text/html" and "attachment" not in disp:
                        try:
                            html_body = mp.get_payload(decode=True).decode(errors="ignore")
                        except Exception:
                            pass
                    elif ct == "text/plain" and "attachment" not in disp and not text_body:
                        try:
                            text_body = mp.get_payload(decode=True).decode(errors="ignore")
                        except Exception:
                            pass
            else:
                ct = msg.get_content_type()
                if ct == "text/html" and not html_body:
                    try:
                        html_body = msg.get_payload(decode=True).decode(errors="ignore")
                    except Exception:
                        pass
 
        mail_conn.logout()
 
    except Exception:
        pass
    safe_html = ""
    if html_body:
        safe_html = _re.sub(r'<img[^>]*>', '', html_body, flags=_re.IGNORECASE)
 
    return render(request, "staff_ticket_detail.html", {
        "ticket":      ticket,
        "attachments": ticket.attachments.all(),
        "notes":       ticket.notes.all().order_by("-created_at"),
        "body":        text_body,
        "html_body":   safe_html,
        "has_html":    bool(safe_html.strip()),
    })

def ticket_list(request):
    if not request.session.get("token"):
        return redirect("login")
 
    from django.core.paginator import Paginator

    unassigned_qs = Ticket.objects.filter(status="unassigned")
    unassigned_page = request.GET.get("unassigned_page", 1)
    unassigned_paginator = Paginator(unassigned_qs, 10)
    unassigned_tickets = unassigned_paginator.get_page(unassigned_page)

    assigned_qs = Ticket.objects.filter(status="assigned")
    assigned_page = request.GET.get("assigned_page", 1)
    assigned_paginator = Paginator(assigned_qs, 10)
    assigned_tickets = assigned_paginator.get_page(assigned_page)

    closed_qs = Ticket.objects.filter(status="closed")
    closed_page = request.GET.get("closed_page", 1)
    closed_paginator = Paginator(closed_qs, 10)
    closed_tickets = closed_paginator.get_page(closed_page)
 
    return render(request, "ticket_list.html", {
        "unassigned_tickets": unassigned_tickets,
        "assigned_tickets":   assigned_tickets,
        "closed_tickets":     closed_tickets,
    })
    
def ticket_history(request, ticket_id):

    admin_logged = request.session.get("token")
    staff_email = request.session.get("staff_email")

    if not admin_logged and not staff_email:
        return redirect("login")

    ticket = get_object_or_404(Ticket, id=ticket_id)

    if staff_email and not admin_logged:
        staff = get_object_or_404(Staff, email=staff_email)
        if ticket.assigned_to != staff:
            return redirect("staff_asigned_ticket")

    history = ticket.history.all().order_by("created_at")

    grouped_history = []
    current_block = None

    for h in history:
        if h.action in ["assigned", "reassigned", "closed", "reopened"]:
            current_block = {
                "event": h,
                "notes": []
            }
            grouped_history.append(current_block)

        elif h.action == "note" and current_block:
            current_block["notes"].append(h)

    return render(request, "ticket_history.html", {
        "ticket": ticket,
        "grouped_history": grouped_history
    })

def create_staff(request):

    if request.method == 'POST':
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        staff = Staff.objects.create(name=name,email=email, status="active")
        staff.set_password(password)
        staff.save()
        return redirect('staff_list')

    return render(request,'create_staff.html')

def staff_list(request):
    staffs = Staff.objects.all().order_by("-id")
    return render(request,'staff_list.html',{
        'staffs': staffs
    })


def filter_staffs(request):
    staffs = Staff.objects.all().order_by("-id")
    search = request.GET.get("search")
    status = request.GET.get("status")
    if search:
        staffs = staffs.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search)
        )

    # STATUS FILTER
    if status:
        staffs = staffs.filter(status=status)
    data = []
    for staff in staffs:
        data.append({

            "id": staff.id,

            "name": staff.name,

            "email": staff.email,

            "status": staff.status,
        })
    return JsonResponse({
        "staffs": data
    })


def change_staff_status(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    if staff.status == "active":
        staff.status = "inactive"
    else:
        staff.status = "active"
    staff.save()
    return JsonResponse({
        "success": True
    })

def create_ticket(request):

    staff_id = request.session.get('staff_id')

    if not staff_id:
        return redirect('login')

    staff = Staff.objects.get(id=staff_id)

    if request.method == 'POST':

        subject = request.POST.get("subject")
        sender = request.POST.get("sender")
        body = request.POST.get("body")

        ticket = Ticket.objects.create(
            mail_id=f"MAIL-{Ticket.objects.count()+1}",
            subject=subject,
            sender=sender,
            body=body,
            created_by=staff,
            date=datetime.now().strftime("%d %b %Y %I:%M %p")
        )
        files = request.FILES.getlist("attachments")
        for file in files:
            TicketAttachment.objects.create(
                ticket=ticket,
                file=file,
                filename=file.name,
                content_type=file.content_type
                
            )

        return redirect("staff_asigned_ticket")

    return render(request, "create_ticket.html", {
        "staff": staff
    })

def tickets_list(request):

    staffs = Staff.objects.all()

    return render(request, 'tickets_list.html', {
        'staffs': staffs
    })


def filter_tickets(request):

    tickets = Ticket.objects.select_related(
        "assigned_to"
    ).all().order_by("-created_at")

    # SEARCH
    search = request.GET.get("search")

    if search:

        tickets = tickets.filter(

            Q(subject__icontains=search) |

            Q(ticket_number__icontains=search) |

            Q(sender__icontains=search) |

            Q(assigned_to__name__icontains=search)

        )
    status = request.GET.get("status")

    if status:
        tickets = tickets.filter(status=status)
    staff = request.GET.get("staff")

    if staff:
        tickets = tickets.filter(assigned_to_id=staff)
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    if from_date:
        tickets = tickets.filter(created_at__date__gte=from_date)

    if to_date:
        tickets = tickets.filter(created_at__date__lte=to_date)

    data = []

    for ticket in tickets:

        data.append({

            "ticket_number": ticket.ticket_number,

            "subject": ticket.subject,

            "sender": ticket.sender,

            "status": ticket.status,

            "staff": ticket.assigned_to.name if ticket.assigned_to else "Not Assigned",

            "date": ticket.created_at.strftime("%d-%m-%Y"),

        })

    return JsonResponse({
        "tickets": data
    })
  
def send_email(request):
    if request.method == "POST":
        to_email = request.POST.get("to_email")
        cc_email = request.POST.get("cc_email")
        bcc_email = request.POST.get("bcc_email")
        subject = request.POST.get("subject")
        body = request.POST.get("body")
        sent_email = SentEmail.objects.create(
            sender_email=settings.EMAIL_HOST_USER,
            to_email=to_email,
            cc_email=cc_email,
            bcc_email=bcc_email,
            subject=subject,
            body=body,
        )
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[x.strip() for x in to_email.split(",") if x.strip()],
            cc=[x.strip() for x in cc_email.split(",") if x.strip()] if cc_email else [],
            bcc=[x.strip() for x in bcc_email.split(",") if x.strip()] if bcc_email else [],
        )
        files = request.FILES.getlist("attachments")
        for uploaded_file in files:
            attachment = EmailAttachment.objects.create(
                email=sent_email,
                file=uploaded_file
            )
            uploaded_file.seek(0)
            email.attach(
                uploaded_file.name,
                uploaded_file.read(),
                uploaded_file.content_type
            )

        email.send(fail_silently=False)

        return redirect("send_email")

    return render(request, "send_email.html")
def email_list(request):
    emails = SentEmail.objects.all().prefetch_related(
        "attachments"
    ).order_by("-id")

    search = request.GET.get("search")

    from_date = request.GET.get("from_date")

    to_date = request.GET.get("to_date")

    if search:

        emails = emails.filter(

            Q(sender_email__icontains=search) |
            Q(subject__icontains=search) |
            Q(body__icontains=search) |
            Q(to_email__icontains=search) |
            Q(cc_email__icontains=search) |
            Q(bcc_email__icontains=search)

        )

    if from_date:

        emails = emails.filter(
            created_at__date__gte=from_date
        )
    if to_date:

        emails = emails.filter(
            created_at__date__lte=to_date
        )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":

        table_html = ""

        for email in emails:

            attachments = ""

            for file in email.attachments.all():

                attachments += f"""

                    <div class="badge">

                        {file.file.name.replace('email_attachments/', '')}

                    </div>

                """

            if not attachments:

                attachments = "-"

            table_html += f"""

            <tr>

                <td>#{email.id}</td>

                <td>{email.sender_email}</td>

                <td>

                    <div class="subject">

                        {email.subject}

                    </div>

                </td>

                <td>{email.to_email}</td>

                <td>{email.cc_email or '-'}</td>

                <td>{email.bcc_email or '-'}</td>

                <td>

                    <div class="message">

                        {email.body}

                    </div>

                </td>

                <td>

                    {attachments}

                </td>

                <td>

                    {email.created_at.strftime('%d %b %Y %I:%M %p')}

                </td>

            </tr>

            """

        if not table_html:

            table_html = """

            <tr>

                <td colspan="9">

                    <div class="empty">

                        No Emails Found

                    </div>

                </td>

            </tr>

            """

        return JsonResponse({
            "table": table_html
        })

    context = {
        "emails": emails,
        "sender_email": settings.EMAIL_HOST_USER
    }

    return render(request, "email_list.html", context)