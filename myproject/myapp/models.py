from enum import unique
from django.core import mail
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password

# Create your models here.


class Staff(models.Model):
    name  = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)  

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

    ticket_number = models.CharField(max_length=20, unique=True, editable=False)

    mail_id  = models.CharField(max_length=50, unique=True)  
    subject  = models.TextField(blank=True)
    sender   = models.CharField(max_length=255, blank=True)
    date     = models.CharField(max_length=100, blank=True)
    body     = models.TextField(blank=True)
 
 
    assigned_to = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets" )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unassigned")
 
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ["-created_at"]
 
    def save(self, *args, **kwargs):
       
        if not self.ticket_number:
            last = Ticket.objects.order_by("id").last()
            next_id = (last.id + 1) if last else 1
            self.ticket_number = f"TKT-{next_id:04d}"
        super().save(*args, **kwargs)
 
    def __str__(self):
        return f"{self.ticket_number} — {self.subject[:50]}"
    
class TicketAttachment(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments"
    )
    file = models.FileField(upload_to="ticket_attachments/")
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.filename

class TicketNote(models.Model):
    ticket=models.ForeignKey(Ticket,on_delete=models.CASCADE,related_name='notes')
    staff=models.ForeignKey(Staff,on_delete=models.CASCADE)
    note= models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.staff.name} - {self.created_at}"