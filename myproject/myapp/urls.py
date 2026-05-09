
from django.urls import include
from django.contrib import admin
from django.urls import path
from myapp import views

urlpatterns = [
    path('', views.login_page, name='login'),
    path('logout/',views. logout_page, name='logout'),
    path("inbox/", views.inbox, name="inbox"),
    path("email/<str:mail_id>/", views.email_detail, name="email_detail"),
]
