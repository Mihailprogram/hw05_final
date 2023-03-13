from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.models import Group, Post

User = get_user_model()

POST_STR_LENGTH: int = 15


class PostModelTest(TestCase):
    """Тестовый пост."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = User.objects.create_user(username='Miha')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Длинный текст ну'
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у модели Post корректно работает __str__."""
        post = PostModelTest.post
        expected_object_name = post.text[:POST_STR_LENGTH]
        self.assertEqual(
            expected_object_name,
            str(post),
            (
                f'{POST_STR_LENGTH} символов поста'
            )
        )


class GroupModelTest(TestCase):
    """Тестовая группа."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у модели Group корректно работает __str__."""
        group = GroupModelTest.group
        expected_object_name = group.title
        self.assertEqual(
            expected_object_name,
            str(group),
            'Метод __str__ модели Group должен выводить название группы'
        )
