from django.shortcuts import render, get_object_or_404
from .models import ChatHistory


def chat_view(request):
    return render(request, 'chat/chat.html')


def result_view(request, id):
    chat = get_object_or_404(ChatHistory, id=id)
    return render(request, 'chat/result.html', {'chat': chat})


def history_view(request):
    chats = ChatHistory.objects.all()[:20]
    return render(request, 'chat/history.html', {'chats': chats})
