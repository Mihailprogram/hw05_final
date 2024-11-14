def user_group(request):
    # Проверяем, аутентифицирован ли пользователь и в какой группе он состоит
    
    user_groups = request.user.groups.filter(name='all').exists()
    return {'user_groups': True}