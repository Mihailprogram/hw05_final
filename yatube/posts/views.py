from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Follow, Post, Group, Comment, User
from django.core.paginator import Paginator
from django.shortcuts import render
from .forms import PostForm, CommentForm
from django.views.decorators.cache import cache_page
from django.conf import settings

def paginator(request, posts):
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj

@cache_page(20 * 1)
def index(request):
    post_list = Post.objects.all().order_by('-pub_date')
    paginator = Paginator(post_list, 10)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)

    post_list = group.groups.all().order_by('-pub_date')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.select_related('group').order_by('-pub_date')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    total = page_obj.paginator.count
    if Follow.objects.filter(author=author.id):
        following = True
    else:
        following = False
    context = {
        "page_obj": page_obj,
        "author": author,
        "total": total,
        "following": following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    total = post.author.posts.count
    form = CommentForm(request.POST or None)
    comments = Comment.objects.select_related('post').filter(post=post_id)
    context = {
        "post": post,
        "total": total,
        "form": form,
        "comments": comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    template = "posts/create_post.html"
    title = "Новый пост"
    is_edit = False
    if request.method == "GET":
        context = {"form": PostForm(), "is_edit": is_edit, "title": title, }
        return render(request, template, context)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect("posts:profile", request.user)
    context = {"form": form, "is_edit": is_edit, "title": title, }
    return render(request, template, context)


def post_edit(request, post_id):
    post_s = get_object_or_404(Post, pk=post_id)
    title = "Редактировать пост"
    is_edit = True
    if request.user != post_s.author:
        return redirect("posts:profile", post_s.author)
    if request.method == 'POST':
        form = PostForm(
            request.POST or None,
            instance=post_s,
            files=request.FILES or None
        )
        if form.is_valid():
            post_s.save()
            return redirect("posts:post_detail", post_id)
        return render(request, 'posts/create_post.html',
                      {'form': form,
                       "is_edit": is_edit,
                       'title': title})
    form = PostForm(instance=post_s)
    context = {
        'form': form,
        "is_edit": is_edit,
        'title': title
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    # Получите пост и сохраните его в переменную post.
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    posts = Post.objects.select_related('author', 'group').filter(
        author__following__user=request.user
        )
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    template = 'posts/follow.html'
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    # Подписаться на автора
    author = User.objects.get(username=username)
    if request.user!=author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect("posts:profile", username=author)

@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    author = User.objects.get(username=username)
    is_follower = Follow.objects.filter(user=request.user, author=author)
    if is_follower.exists():
        is_follower.delete()
    return redirect('posts:profile', username=author)