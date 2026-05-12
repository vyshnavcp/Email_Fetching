from enum import unique
from django.core import mail
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password

# Create your models here.


class Staff(models.Model):
    name  = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  # hashed password

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.name
 
class Ticket(models.Model):
 
    STATUS_CHOICES = [
        ("unassigned",        "Unassigned"),
        ("assigned",    "Assigned"),
        ("closed",      "Closed"),
    ]
 
    # Auto ticket number  e.g.  TKT-0001
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
 
    # Email fields (saved once on first open)
    mail_id  = models.CharField(max_length=50, unique=True)   # IMAP mail id
    subject  = models.TextField(blank=True)
    sender   = models.CharField(max_length=255, blank=True)
    date     = models.CharField(max_length=100, blank=True)
    body     = models.TextField(blank=True)
 
    # Assignment
    assigned_to = models.ForeignKey(
        Staff,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unassigned")
 
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ["-created_at"]
 
    def save(self, *args, **kwargs):
        # Generate ticket number only on first save
        if not self.ticket_number:
            last = Ticket.objects.order_by("id").last()
            next_id = (last.id + 1) if last else 1
            self.ticket_number = f"TKT-{next_id:04d}"
        super().save(*args, **kwargs)
 
    def __str__(self):
        return f"{self.ticket_number} — {self.subject[:50]}"