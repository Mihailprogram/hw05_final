from django.views.generic.base import TemplateView
from django.shortcuts import render, get_object_or_404, redirect
from posts.models import Follow, Post, Group, Comment, User


class About(TemplateView):
    # В переменной template_name обязательно указывается имя шаблона,
    # на основе которого будет создана возвращаемая страница
    template_name = 'about/abouts.html'


def about(request):
    post = Post.objects.filter(author=request.user)
    user = User.objects.get(username=request.user)
    folow = Follow.objects.filter(user=request.user).count()
    folower = Follow.objects.filter(author=request.user).count()
    
    context = {
        'count': post.count(),
        'user': user,
        'folow': folow,
        'folower': folower,
    }
    return render(request, 'about/abouts.html', context)

class AboutTechView(TemplateView):
    # В переменной template_name обязательно указывается имя шаблона,
    # на основе которого будет создана возвращаемая страница
    template_name = 'about/tech.html'
