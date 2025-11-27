"""
Context processors personalizados para NUAM

Proveen variables globales a todos los templates.
"""


def user_role_processor(request):
    """
    Agrega información del rol del usuario al contexto de templates.

    Variables disponibles en templates:
    - user_role: String con el rol ('Administrador', 'Analista Tributario', 'Auditor', 'Sin Rol')
    - is_administrador: Boolean
    - is_analista: Boolean
    - is_auditor: Boolean
    - user_corredora: Objeto Corredora del usuario (si está autenticado)

    Example en template:
        {% if is_analista %}
            <a href="{% url 'calificaciones:crear' %}">Nueva Calificación</a>
        {% endif %}
    """
    context = {
        'user_role': 'Sin Rol',
        'is_administrador': False,
        'is_analista': False,
        'is_auditor': False,
        'user_corredora': None,
    }

    if request.user.is_authenticated:
        # Obtener rol del usuario
        grupos = request.user.groups.values_list('name', flat=True)

        if 'Administradores' in grupos:
            context['user_role'] = 'Administrador'
            context['is_administrador'] = True
        elif 'Analistas' in grupos:
            context['user_role'] = 'Analista Tributario'
            context['is_analista'] = True
        elif 'Auditores' in grupos:
            context['user_role'] = 'Auditor'
            context['is_auditor'] = True

        # Corredora del usuario
        if hasattr(request.user, 'corredora'):
            context['user_corredora'] = request.user.corredora

    return context
