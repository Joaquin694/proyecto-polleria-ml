# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from accounts.models import EmployeeProfile
from predictions.models import PredictionRun, PredictionResult
from .forms import EmployeeSignupForm
from django.db.models.functions import TruncDate
from django.db.models import Count, Q


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True  # si ya está logueado, no volver al login

@login_required
def profile(request):
    profile = getattr(request.user, "profile", None)
    return render(request, 'accounts/profile.html', {"profile": profile})

def signup(request):
    # si quieres limitarlo a admin, descomenta:
    # if not request.user.is_authenticated or not request.user.is_staff:
    #     return redirect('accounts:login')

    if request.method == 'POST':
        form = EmployeeSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('accounts:login')
    else:
        form = EmployeeSignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def dashboard(request):
    """
    Dashboard:
    - Admin ve todo; empleado ve solo lo suyo.
    - Métricas + series de tiempo + totales por modelo (RF/DT/LR).
    """
    profile = getattr(request.user, "profile", None)

    if request.user.is_staff:
        runs_qs = PredictionRun.objects.all().order_by('-created_at')
        results_qs = PredictionResult.objects.all().select_related('run')
        empleados = EmployeeProfile.objects.all()
    else:
        runs_qs = PredictionRun.objects.filter(user=request.user).order_by('-created_at')
        results_qs = PredictionResult.objects.filter(run__user=request.user).select_related('run')
        empleados = None

    # 1) Pastel: retenidos vs perdidos
    retenidos = results_qs.filter(pred_label=0).count()
    perdidos  = results_qs.filter(pred_label=1).count()

    # 2) “Satisfacción” usando prob como proxy (ajusta umbrales a tu realidad)
    alta  = results_qs.filter(prob__gte=0.80).count()
    media = results_qs.filter(prob__gte=0.50, prob__lt=0.80).count()
    baja  = results_qs.filter(prob__lt=0.50).count()

    # 3) Series por día (últimos 10 días) usando agregación
    days = 10
    agg_qs = (
        results_qs
        .annotate(day=TruncDate('run__created_at'))
        .values('day')
        .annotate(
            retenidos=Count('id', filter=Q(pred_label=0)),
            perdidos=Count('id',  filter=Q(pred_label=1)),
        )
        .order_by('-day')[:days]   # <- cortar en la DB sin índice negativo
    )
    agg = list(reversed(list(agg_qs)))  # cronológico: más antiguo → hoy

    labels_days = [a['day'].strftime('%d-%m') for a in agg]
    data_retenidos_days = [a['retenidos'] for a in agg]
    data_perdidos_days  = [a['perdidos']  for a in agg]

    # 4) Barras: totales por modelo (RF, DT, LR)
    rf_total = runs_qs.filter(model_choice='rf').count()
    dt_total = runs_qs.filter(model_choice='dt').count()
    lr_total = runs_qs.filter(model_choice='lr').count()  # <- faltaba

    context = {
        "profile": profile,
        "empleados": empleados,
        "runs": runs_qs,

        # pastel
        "retenidos": retenidos,
        "perdidos": perdidos,

        # tarjetas prob
        "alta": alta, "media": media, "baja": baja,

        # líneas
        "labels_days": labels_days,
        "data_retenidos_days": data_retenidos_days,
        "data_perdidos_days": data_perdidos_days,

        # barras por modelo
        "rf_total": rf_total, "dt_total": dt_total, "lr_total": lr_total,
    }
    return render(request, "dashboard.html", context)