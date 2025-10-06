# predictions/models.py
from django.db import models
from django.contrib.auth.models import User

class PredictionRun(models.Model):
    MODEL_CHOICES = [
        ('rf', 'RandomForest'),
        ('dt', 'DecisionTree'),
        ('lr', 'LogisticRegression'),   # 👈 NUEVO
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    model_choice = models.CharField(max_length=2, choices=MODEL_CHOICES)
    uploaded_csv = models.FileField(upload_to='uploads/')
    created_at = models.DateTimeField(auto_now_add=True)
    total_rows = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.get_model_choice_display()} - {self.created_at:%Y-%m-%d %H:%M}"

class PredictionResult(models.Model):
    run = models.ForeignKey(PredictionRun, on_delete=models.CASCADE, related_name='results')
    id_cliente = models.CharField(max_length=50, blank=True)
    apellidos_nombres = models.CharField(max_length=200, blank=True)
    pred_label = models.IntegerField()    # 1 = se pierde, 0 = no se pierde
    prob = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.id_cliente} -> {self.pred_label}"
