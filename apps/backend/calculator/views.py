from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import json
from .models import CalculatorHistory
from engine.calculator_engine import CalculatorEngine

calc_engine = CalculatorEngine()


@csrf_exempt
def calculator_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST.dict()

        question = data.get('question', '').strip()
        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)

        result = calc_engine.calculate(question)

        CalculatorHistory.objects.create(
            input_data={'question': question},
            result_data=result,
        )

        return JsonResponse(result)

    return render(request, 'calculator/calculator.html')


def calculator_result_view(request):
    calc_id = request.GET.get('id')
    if calc_id:
        calc = get_object_or_404(CalculatorHistory, id=calc_id)
        return render(request, 'calculator/result.html', {'calc': calc})
    results = CalculatorHistory.objects.all()[:20]
    return render(request, 'calculator/result.html', {'results': results})
