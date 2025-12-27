from django.shortcuts import render

def help_center(request):
    return render(request, 'resident_help_center.html')