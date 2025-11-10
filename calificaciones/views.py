from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from rest_framework import generics, status, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from .models import Calificacion
from .serializers import CalificacionSerializer
from .permissions import AuthorOrReadOnly


# Vista HTML para el frontend - PROTEGIDA
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calificaciones_page(request):
    """
    Vista principal de calificaciones.
    Solo accesible para usuarios autenticados.
    """
    # Verificar si hay token JWT en el request
    if not request.user.is_authenticated:
        return redirect('usuarios:login')
    
    return render(request, 'calificaciones/calificaciones.html', {
        'user': request.user
    })


# API Views
class CalificacionListCreateView(generics.GenericAPIView,
                                 mixins.ListModelMixin,
                                 mixins.CreateModelMixin):
    """
    API para listar y crear calificaciones.
    Requiere autenticación.
    """
    serializer_class = CalificacionSerializer
    permission_classes = [IsAuthenticated]  # Solo usuarios autenticados
    queryset = Calificacion.objects.all()

    def get_queryset(self):
        """
        Filtrar calificaciones por usuario si no es staff
        """
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Calificacion.objects.all()
        return Calificacion.objects.filter(user=user)

    def perform_create(self, serializer):
        """
        Asignar automáticamente el usuario actual
        """
        user = self.request.user        
        calificacion = serializer.save(user=user)
        
        # Registrar en auditoría
        self._log_action('CREATE', calificacion, user)
        return calificacion
    
    def _log_action(self, action, calificacion, user):
        """
        Registrar acción en log de auditoría
        """
        from auditoria.models import LogAuditoria
        
        # Obtener IP del request
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        
        LogAuditoria.objects.create(
            user=user,
            calificacion=calificacion,
            accion=action,
            detalle=f"Calificación {calificacion.id} - {calificacion.instrumento}",
            ip_address=ip
        )
    
    def get(self, request: Request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
    
    def post(self, request: Request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class CalificacionRetrieveUpdateDeleteView(generics.GenericAPIView,
                                           mixins.RetrieveModelMixin,
                                           mixins.UpdateModelMixin,
                                           mixins.DestroyModelMixin):
    """
    API para ver, actualizar y eliminar calificaciones.
    Solo el autor o staff puede modificar/eliminar.
    """
    serializer_class = CalificacionSerializer
    queryset = Calificacion.objects.all()
    permission_classes = [IsAuthenticated, AuthorOrReadOnly]

    def perform_update(self, serializer):
        calificacion = serializer.save()
        self._log_action('UPDATE', calificacion)
        return calificacion
    
    def perform_destroy(self, instance):
        self._log_action('DELETE', instance)
        instance.delete()
    
    def _log_action(self, action, calificacion):
        """Registrar acción en auditoría"""
        from auditoria.models import LogAuditoria
        
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        
        LogAuditoria.objects.create(
            user=self.request.user,
            calificacion=calificacion if action != 'DELETE' else None,
            accion=action,
            detalle=f"Calificación {calificacion.id} - {calificacion.instrumento}",
            ip_address=ip
        )

    def get(self, request: Request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
    
    def put(self, request: Request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
    
    def patch(self, request: Request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
    
    def delete(self, request: Request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)