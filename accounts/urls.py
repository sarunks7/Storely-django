from django.urls import path
from . import views


urlpatterns = [   
    
    # Define your accounts-related URL patterns here

    path('register/',views.register, name='register'),
    path('login/',views.login, name='login'),
    path('logout/',views.logout, name='logout'),
    path('dashboard/',views.dashboard, name='dashboard'),
    path('',views.dashboard, name='dashboard'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('forgot-password/', views.forgotPassword, name='forgotPassword'),
    path('resetpassword_validate/<uidb64>/<token>/', views.resetPassword_validate, name='resetPassword_validate'),
    path('resetpassword/', views.resetPassword, name='resetPassword'),
    
]