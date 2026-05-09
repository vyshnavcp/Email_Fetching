from django.contrib import admin
from myapp.models import Staff
# Register your models here.
@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display  = ("name", "email")
    search_fields = ("name", "email")

    fields = ("name", "email", "password")   # show password field in form

    readonly_fields = ()  # keep editable