from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('banking/', include('banking.urls')),
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
]
