from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('rapports/', views.reports_dashboard, name='rapports'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
]
