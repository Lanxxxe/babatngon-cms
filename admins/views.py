from django.shortcuts import render

# Create your views here.
def admin_dashboard(request):

    return render(request, 'admin_dashboard.html')

def admin_analytics(request):


    return render(request, 'admin_analytics.html')


def admin_complaints(request):

    return render(request, 'admin_complaints.html')


def admin_resident(request):

    return render(request, 'admin_resident.html')

def admin_notification(request):


    return render(request, 'admin_notification.html')