# predictions/views.py
import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .forms import UploadCSVForm
from .models import PredictionRun, PredictionResult
from .utils import load_model, preprocess_dataframe, load_feature_list, align_features

# (Opcional) deja explícito qué exporta este módulo
__all__ = ["upload_and_predict", "runs_history", "run_results"]


@login_required
def upload_and_predict(request):
    """
    Sube CSV/XLSX, elige modelo (rf/dt/lr), predice en masa y guarda resultados.
    """
    if request.method == 'POST':
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            run: PredictionRun = form.save(commit=False)
            run.user = request.user
            run.save()  # guarda el archivo en media/uploads/

            # Leer archivo
            fpath = run.uploaded_csv.path
            try:
                if fpath.lower().endswith('.xlsx'):
                    df = pd.read_excel(fpath)
                else:
                    df = pd.read_csv(fpath)
            except Exception as e:
                messages.error(request, f"Error leyendo archivo: {e}")
                return redirect('predictions:upload')

            # Columnas que quieres mostrar en la tabla de resultados
            for c in ['ID_Cliente', 'Apellido_Nombre']:
                if c not in df.columns:
                    df[c] = ''

            # Preprocesa según el modelo elegido (rf/dt/lr)
            X = preprocess_dataframe(df, run.model_choice)

            # Alinea a las columnas del entrenamiento
            expected = load_feature_list(run.model_choice)
            X = align_features(X, expected)

            # Carga modelo y predice
            model = load_model(run.model_choice)
            preds = model.predict(X)
            probs = None
            if hasattr(model, "predict_proba"):
                try:
                    probs = model.predict_proba(X)[:, 1]
                except Exception:
                    probs = None

            run.total_rows = len(df)
            run.save()

            # Guarda resultados
            bulk = []
            for i in range(len(df)):
                bulk.append(PredictionResult(
                    run=run,
                    id_cliente=str(df.loc[i, 'ID_Cliente']),
                    apellidos_nombres=str(df.loc[i, 'Apellido_Nombre']),
                    pred_label=int(preds[i]),
                    prob=float(probs[i]) if probs is not None else None
                ))
            PredictionResult.objects.bulk_create(bulk)

            messages.success(request, "Predicción completada.")
            return redirect('predictions:run_results', run_id=run.id)
    else:
        form = UploadCSVForm()

    return render(request, 'predictions/upload.html', {'form': form})


@login_required
def runs_history(request):
    """
    Historial de ejecuciones del usuario (o todas si es admin).
    """
    if request.user.is_staff:
        runs = PredictionRun.objects.all().order_by('-created_at')
    else:
        runs = PredictionRun.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'predictions/history.html', {'runs': runs})


@login_required
def run_results(request, run_id):
    run = get_object_or_404(PredictionRun, id=run_id)

    # seguridad: los empleados solo ven sus runs
    if (not request.user.is_staff) and (run.user_id != request.user.id):
        return redirect('predictions:history')

    results = run.results.all().order_by('-id')

    # Métricas
    total = results.count()
    perdidos = results.filter(pred_label=1).count()
    retenidos = total - perdidos

    # Datos para gráficos con probabilidades (si existen)
    probs = [r.prob for r in results if r.prob is not None]
    has_probs = len(probs) > 0

    # Histograma 10 bins (0.0–0.1 … 0.9–1.0)
    bin_labels = [f"{i/10:.1f}-{(i+1)/10:.1f}" for i in range(10)]
    hist_counts = [0] * 10
    if has_probs:
        for p in probs:
            if p is None: 
                continue
            if p <= 0: idx = 0
            elif p >= 1: idx = 9
            else: idx = int(p * 10)
            hist_counts[idx] += 1

    # Barrido de umbral: % marcado como 1 según threshold
    thr_labels = [f"{i/100:.2f}" for i in range(0, 101, 5)]
    thr_rate = []
    thr_count = []
    n = len(probs)
    if has_probs:
        for t in [i/100 for i in range(0, 101, 5)]:
            c = sum(1 for p in probs if p is not None and p >= t)
            thr_count.append(c)
            thr_rate.append(round((c / n) * 100, 2) if n else 0)
    else:
        thr_rate = [0]*len(thr_labels)
        thr_count = [0]*len(thr_labels)

    context = {
        'run': run,
        'results': results,
        'total': total,
        'perdidos': perdidos,
        'retenidos': retenidos,
        'has_probs': has_probs,
        'hist_labels': bin_labels,
        'hist_counts': hist_counts,
        'thr_labels': thr_labels,
        'thr_rate': thr_rate,
        'thr_count': thr_count,
    }
    return render(request, 'predictions/results.html', context)

