from django.shortcuts import render
from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import SignupSerializer, CurrentUserCalificacionesSerializer
from .tokens import create_jwt_pair_for_user

class SignUpView(generics.GenericAPIView):
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]

    def get(self, request):
        return render(request, 'usuarios/signup.html')

    def post(self, request: Request):
        data = request.data
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            serializer.save()
            response = {
                "message": "Usuario creado correctamente",
                "data": serializer.data
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
        return super().get_renderers()

    def post(self, request: Request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(email=email, password=password)

        if user is not None:
            tokens = create_jwt_pair_for_user(user)
            response = {
                "message": "Login exitoso",
                "tokens": tokens
            }
            return Response(data=response, status=status.HTTP_200_OK)
        else:
            return Response(
                data={"message": "Correo o contraseña incorrecto"},
                status=status.HTTP_401_UNAUTHORIZED
            )

    def get(self, request: Request):
        content = {
            "user": str(request.user),
            "auth": str(request.auth)
        }
        return Response(data=content, status=status.HTTP_200_OK)

@api_view(http_method_names=['GET'])
@permission_classes([IsAuthenticated])
def get_calificaciones_for_current_user(request: Request):
    user = request.user
    serializer = CurrentUserCalificacionesSerializer(
        instance=user, 
        context={"request": request}
    )
    return Response(data=serializer.data, status=status.HTTP_200_OK)