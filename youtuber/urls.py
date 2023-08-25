from django.urls import path

from youtuber import views

urlpatterns = [
    path('callback/', views.handle_push_notification),
]