from django.shortcuts import render, get_object_or_404  
from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from acciones.models import Corredora
from .models import User
from .serializers import SignupSerializer, CurrentUserCalificacionesSerializer, UserApprovalSerializer
from .tokens import create_jwt_pair_for_user

class SignUpView(generics.GenericAPIView):
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'usuarios/signup.html'

    def get_renderers(self):
        if self.request.method == 'POST':
            return [JSONRenderer()]
        return [TemplateHTMLRenderer()]

    def get(self, request):
        corredoras = Corredora.objects.all().values('id', 'nombre')
        context = {'corredoras': corredoras}
        return render(request, 'usuarios/signup.html', context)

    def post(self, request: Request):
        data = request.data
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            serializer.save()
            response = {
                "message": "Registro exitoso. La aprobación de tu cuenta está pendiente.",
                "data": {
                    "email": serializer.data.get('email'),
                    "first_name": serializer.data.get('first_name'),
                    "last_name": serializer.data.get('last_name')
                }
            }
            return Response(data=response, status=status.HTTP_201_CREATED)
        
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'usuarios/login.html'

    def get_renderers(self):
        if self.request.method == 'POST':
            return [JSONRenderer()]
        return [TemplateHTMLRenderer()]

    def get(self, request: Request):
        return Response({}, template_name=self.template_name)

    def post(self, request: Request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                data={"message": "Email y contraseña son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(email=email, password=password)

        if user is not None:
            if not user.is_active:
                return Response(
                    data={"message": "Tu cuenta está pendiente de aprobación por un administrador."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            redirect_url = '/calificaciones/'
            if user.is_staff:
                redirect_url = '/auth/admin/dashboard/'

            tokens = create_jwt_pair_for_user(user)
            response = {
                "message": "Login exitoso",
                "tokens": tokens,
                "redirect_url": redirect_url,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_staff": user.is_staff
                }
            }
            return Response(data=response, status=status.HTTP_200_OK)
        else:
            return Response(
                data={"message": "Correo o contraseña incorrecto"},
                status=status.HTTP_401_UNAUTHORIZED
            )

@api_view(http_method_names=['GET'])
@permission_classes([IsAuthenticated])
def get_calificaciones_for_current_user(request: Request):
    user = request.user
    serializer = CurrentUserCalificacionesSerializer(
        instance=user, 
        context={"request": request}
    )
    return Response(data=serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request: Request):
    user = request.user
    data = {
        "id": user.id,
        "email": user.email,
        "rut": user.rut,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_active": user.is_active,
        "corredora": user.corredora.nombre if user.corredora else None,
        "date_joined": user.date_joined
    }
    return Response(data=data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request: Request):
    return Response(
        data={"message": "Logout exitoso."},
        status=status.HTTP_200_OK
    )


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'usuarios/admin.html'

    def get_renderers(self):
        if self.request.method == 'POST':
            return [JSONRenderer()]
        return [TemplateHTMLRenderer()]

    def get(self, request):
        pending_users = User.objects.filter(is_active=False, is_staff=False).order_by('-date_joined')
        
        pending_users_data = UserApprovalSerializer(
            pending_users, 
            many=True,
            context={'request': request}
        ).data
        
        corredoras = Corredora.objects.all().values('id', 'nombre')
        
        dashboard_data = {
            "title": "Panel de Administración",
            "pending_count": pending_users.count(),
            "pending_users": pending_users_data,
            "corredoras": list(corredoras),
            "total_users": User.objects.filter(is_active=True, is_staff=False).count(),
            "total_corredoras": Corredora.objects.count()
        }
        
        return Response(data=dashboard_data, template_name=self.template_name)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def approve_user(request: Request, user_id: int):
    try:
        user = User.objects.get(id=user_id, is_active=False)
        
        nueva_corredora_id = request.data.get('corredora')
        if nueva_corredora_id:
            user.corredora_id = nueva_corredora_id
        
        user.is_active = True
        user.save()
        
        return Response({
            "message": f"Usuario {user.email} aprobado exitosamente",
            "user": UserApprovalSerializer(user).data
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            "message": "Usuario no encontrado o ya aprobado"
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def reject_user(request: Request, user_id: int):
    try:
        user = User.objects.get(id=user_id, is_active=False)
        email = user.email
        user.delete()
        
        return Response({
            "message": f"Usuario {email} rechazado y eliminado"
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            "message": "Usuario no encontrado"
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def pending_users_list(request: Request):
    pending_users = User.objects.filter(is_active=False, is_staff=False).order_by('-date_joined')
    serializer = UserApprovalSerializer(pending_users, many=True, context={'request': request})
    
    return Response({
        "count": pending_users.count(),
        "users": serializer.data
    }, status=status.HTTP_200_OK)

