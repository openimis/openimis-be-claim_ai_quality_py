from django.urls import path

from claim_ai_quality import views

urlpatterns = [
    path('report/', views.miscategorisation_report, name='miscategorisation_report'),
]
