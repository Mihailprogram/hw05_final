from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from ..models import Group, Post
from http import HTTPStatus

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Miha')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_posts_url_exists_for_unauthorized_user(self):
        """Проверка доступности страниц для неавторизованного пользователя."""
        field_urls = {
            'index': '/',
            'group_list': f'/group/{self.group.slug}/',
            'profile': f'/profile/{self.user}/',
            'post_detail': f'/posts/{self.post.pk}/'
        }
        for value, expected in field_urls.items():
            response = self.guest_client.get(expected)
            with self.subTest(value=value):
                self.assertEqual(
                    response.status_code,
                    HTTPStatus.OK,
                    f'Страница {value} не доступна'
                )

    def test_create_url_exists_for_authorized_user(self):
        """Проверка доступности страниц для авторизованного пользователя."""
        field_urls = {
            'post_create': '/create/',
            'post_edit': f'/posts/{self.post.pk}/edit/'
        }
        for value, expected in field_urls.items():
            response = self.authorized_client.get(expected)
            with self.subTest(value=value):
                self.assertEqual(
                    response.status_code,
                    HTTPStatus.OK,
                    f'Страница {value} не доступна'
                )

    def test_access_edit_post_author(self):
        """Проверяем доступность редактирования поста автором"""
        self.assertEqual(
            self.authorized_client.get(
                f"/posts/{StaticURLTests.post.id}/edit/"
            ).status_code,
            HTTPStatus.OK
        )

    def test_access_not_exist_page(self):
        """Проверяем, что при обращении к несуществующей странице возвращается
        ошибка 404"""
        self.assertEqual(
            self.guest_client.get(
                "/not_exist_page/"
            ).status_code,
            HTTPStatus.NOT_FOUND
        )

    def test_urls_redirect_anonymous(self):
        """Проверяем адреса перенаправления неавторизованного пользователя"""
        for url, redirect_url in {
            "/create/": "/auth/login/?next=/create/",
            f"/posts/{StaticURLTests.post.id}/edit/":
            f"/profile/{self.user}/",
        }.items():
            with self.subTest(url=url):
                self.assertRedirects(
                    self.guest_client.get(url, follow=True),
                    redirect_url
                )

    def test_url(self):
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{self.group.slug}/',
            'posts/profile.html': f'/profile/{self.user}/',
            'posts/post_detail.html': f'/posts/{self.post.pk}/',
            'posts/create_post.html': '/create/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
