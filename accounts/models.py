from django.db import models
from django.contrib.auth.models import User

class EmployeeProfile(models.Model):
    ROLES = (
        ('admin', 'Administrador'),
        ('empleado', 'Empleado'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nombre = models.CharField(max_length=150)
    cargo = models.CharField(max_length=100)
    fecha_registro = models.DateField(auto_now_add=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='empleado')

    def __str__(self):
        return f"{self.nombre} ({self.cargo})"
