
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
    path("staff/", views.staff_asigned_ticket, name="staff_asigned_ticket"),
    path("staff/ticket/<int:ticket_id>/", views.staff_ticket_detail, name="staff_ticket_detail"),
    path("tickets/",views.ticket_list,name="ticket_list"),
    path("ticket/<int:ticket_id>/history/", views.ticket_history, name="ticket_history"),
    path("create-staff/", views.create_staff, name="create_staff"),
    path("staff-list/", views.staff_list, name="staff_list"),
    path("create-ticket/", views.create_ticket, name="create_ticket"),
    path("tickets_list/", views.tickets_list, name="tickets_list"),
    path("filter-tickets/", views.filter_tickets, name="filter_tickets"),
    path("filter-staffs/", views.filter_staffs, name="filter_staffs"),
    path("change-staff-status/<int:staff_id>/",views.change_staff_status,name="change_staff_status"),
    path("send-email/", views.send_email, name="send_email" ),
     path("email-list/",views. email_list, name="email_list"),
    

]
