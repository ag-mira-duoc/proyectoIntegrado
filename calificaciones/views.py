from django.shortcuts import render
from rest_framework import generics, status, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from .models import Calificacion
from .serializers import CalificacionSerializer
from .permissions import AuthorOrReadOnly


# Vista HTML para el frontend
@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def calificaciones_page(request):
    return render(request, 'calificaciones/calificaciones.html')


# API Views
class CalificacionListCreateView(generics.GenericAPIView,
                                 mixins.ListModelMixin,
                                 mixins.CreateModelMixin):

    serializer_class = CalificacionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Calificacion.objects.all()

    def perform_create(self, serializer):
        user = self.request.user        
        calificacion = serializer.save(
            user=user,
        )
        return calificacion
    
    def get(self, request: Request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
    
    def post(self, request: Request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class CalificacionRetrieveUpdateDeleteView(generics.GenericAPIView,
                                           mixins.RetrieveModelMixin,
                                           mixins.UpdateModelMixin,
                                           mixins.DestroyModelMixin):

    serializer_class = CalificacionSerializer
    queryset = Calificacion.objects.all()
    permission_classes = [AuthorOrReadOnly]

    def get(self, request: Request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
    
    def put(self, request: Request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
    
    def patch(self, request: Request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
    
    def delete(self, request: Request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)