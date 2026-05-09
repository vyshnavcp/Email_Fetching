
from django.urls import include
from django.contrib import admin
from django.urls import path
from myapp import views

urlpatterns = [
    path("",views.login_page, name="login"),
    path("inbox/", views.inbox, name="inbox"),
    path("email/<mail_id>/", views.email_detail, name="email_detail"),
    path("assign/<int:ticket_id>/", views.assign_ticket, name="assign_ticket"),
    path("logout/", views.logout_page,name="logout"),

]
