from django.views.debug import default_urlconf
from enum import unique
from django.core import mail
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password

# Create your models here.



class Staff(models.Model):
    STATUS_CHOICE = [
        ('active', 'Active'),
        ('Inactive', 'Inactive'),
    ]
    name  = models.CharField(max_length=100)
    email  = models.EmailField(unique=True)
    status  = models.CharField(max_length=10, choices=STATUS_CHOICE, default='active')
    password = models.CharField(max_length=255)
 
    # ── Email signature stored per-staff ──────────────────────────────────────
    signature = models.TextField(blank=True, default='')
 
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
 
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
 
    def __str__(self):
        return self.name
 
 
class Ticket(models.Model):
    STATUS_CHOICES = [
        ("unassigned", "Unassigned"),
        ("assigned",   "Assigned"),
        ("closed",     "Closed"),
    ]

    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    mail_id  = models.CharField(max_length=50, unique=True)
    subject = models.TextField(blank=True)
    sender = models.CharField(max_length=255, blank=True)
    date  = models.CharField(max_length=100, blank=True)
    body  = models.TextField(blank=True)
    cc    = models.TextField(blank=True, default="")
    bcc   = models.TextField(blank=True, default="")
    is_deleted= models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    assigned_to = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets")
    created_by  = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_tickets")
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unassigned")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            last    = Ticket.objects.order_by("id").last()
            next_id = (last.id + 1) if last else 1
            self.ticket_number = f"TKT-{next_id:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} — {self.subject[:50]}"
 
 
class TicketAttachment(models.Model):
    ticket  = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    file  = models.FileField(upload_to="ticket_attachments/")
    filename  = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
 
    def __str__(self):
        return self.filename
 
 
class TicketNote(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notes')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return f"{self.staff.name} - {self.created_at}"
 
 
class TicketHistory(models.Model):
    ACTION_CHOICES = [
        ("assigned",   "Assigned"),
        ("reassigned", "Reassigned"),
        ("closed",     "Closed"),
        ("note",       "Note Added"),
        ("replied",    "Reply Sent"),
    ]
    ticket      = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="history")
    staff       = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.SET_NULL)
    action      = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    # ── Add these two lines ──────────────────────────────────────────
    note  = models.ForeignKey('TicketNote',  null=True, blank=True, on_delete=models.SET_NULL, related_name="history_entries")
    reply = models.ForeignKey('TicketReply', null=True, blank=True, on_delete=models.SET_NULL, related_name="history_entries")

    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.action}"
 
    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.action}" 
# ── NEW: stores every reply e-mail sent from the ticket detail page ───────────
class TicketReply(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="replies")
    sent_by = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.SET_NULL)
    to_email = models.TextField()                          # comma-separated
    cc_email = models.TextField(blank=True, default='')
    bcc_email = models.TextField(blank=True, default='')
    subject = models.CharField(max_length=500)
    body = models.TextField()
    signature = models.TextField(blank=True, default='')   # snapshot at send time
    sent_at = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f"Reply to {self.ticket.ticket_number} by {self.sent_by}"
 
 
class TicketReplyAttachment(models.Model):
    reply = models.ForeignKey(TicketReply, on_delete=models.CASCADE, related_name="attachments")
    file  = models.FileField(upload_to="ticket_reply_attachments/")
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
 
    def __str__(self):
        return self.filename
 
 
class SentEmail(models.Model):
    sender_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    to_email = models.TextField()
    cc_email  = models.TextField(blank=True, null=True)
    bcc_email = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return self.subject
 
 
class EmailAttachment(models.Model):
    email = models.ForeignKey(SentEmail, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to="email_attachments/")
 
    def __str__(self):
        return self.file.name

    
    
    
    