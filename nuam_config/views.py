from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

api_view(http_method_names=['GET'])
@permission_classes([AllowAny])    
def homepage(request):
    return render(request, 'index.html')

