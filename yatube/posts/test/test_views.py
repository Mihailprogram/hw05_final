from functools import cache
import shutil
import tempfile
from tokenize import Comment
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile


from ..models import Follow, Post, Group

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': cls.post.author}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': cls.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': cls.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

    def setUp(self):
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Шаблон index соответствует ожидаемому контексту."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        author_0 = first_object.author
        text_0 = first_object.text
        group_0 = first_object.group
        self.assertEqual(author_0, self.user)
        self.assertEqual(text_0, 'Тестовый пост')
        self.assertEqual(group_0, self.group)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list соответствует ожидаемому контексту."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        first_object = response.context['page_obj'][0]
        author_0 = first_object.author
        text_0 = first_object.text
        group_0 = first_object.group
        self.assertEqual(author_0, self.user)
        self.assertEqual(text_0, 'Тестовый пост')
        self.assertEqual(group_0, self.group)

        second_object = response.context['group']
        title_1 = second_object.title
        slug_1 = second_object.slug
        description_1 = second_object.description
        self.assertEqual(title_1, 'Тестовая группа')
        self.assertEqual(slug_1, 'test-slug')
        self.assertEqual(description_1, 'Тестовое описание')

    def test_profile_show_correct_context(self):
        """Шаблон profile соответствует ожидаемому контексту."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.post.author,))
        )
        first_object = response.context['page_obj'][0]
        author_0 = first_object.author
        text_0 = first_object.text
        group_0 = first_object.group
        self.assertEqual(author_0, self.user)
        self.assertEqual(text_0, 'Тестовый пост')
        self.assertEqual(group_0, self.group)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail соответствует ожидаемому контексту."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)

    def test_create_edit_show_correct_context(self):
        """Шаблон create_edit соответствует ожидаемому контексту."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        """Шаблон create соответствует ожидаемому контексту."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверяем создание поста с группой на страницах."""
        pages = {
            reverse('posts:index'): Post.objects.get(group=self.post.group),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                'posts:profile', kwargs={'username': self.post.author}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in pages.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                page = response.context['page_obj']
                self.assertIn(expected, page)

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем, что созданный пост с не попал в другую группу."""
        pages = {
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in pages.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                page = response.context['page_obj']
                self.assertNotIn(expected, page)

    def test_index_page_caches_posts(self):
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        Post.objects.create(
            text='Текст тестового поста',
            author=self.user
        )
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_2.content, response_3.content)

    def test_auth_user_can_follow(self):
        """Работают ли подписки"""
        user1 = User.objects.create_user(username='test1')
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_follow', args=(user1.username,))
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertEqual(Follow.objects.first().user, self.user)
        self.assertEqual(Follow.objects.first().author, user1)

    def test_auth_user_can_unfollow(self):
        user2 = User.objects.create_user(username='test2')
        Follow.objects.create(
            user=self.user,
            author=user2
        )
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_unfollow', args=(user2.username,))
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)

    def test_new_post_appears_on_right_user(self):
        """Новый пост на нужной странице"""
        user1 = User.objects.create(username='test1')
        user2 = User.objects.create(username='test2')
        just_client = Client()
        just_client.force_login(user2)
        Follow.objects.create(
            user=self.user,
            author=user1
        )
        clients_posts = ((just_client, 0), (self.authorized_client, 0))
        for man, num in clients_posts:
            with self.subTest(man=man):
                response = man.get(
                    reverse('posts:follow_index')
                )
                self.assertEqual(
                    len(response.context['page_obj'].object_list), num
                )
        Post.objects.create(
            text='test',
            author=user1
        )
        clients_posts = ((just_client, 0), (self.authorized_client, 1))
        for man, num in clients_posts:
            with self.subTest(man=man):
                response = man.get(
                    reverse('posts:follow_index')
                )
                self.assertEqual(
                    len(response.context['page_obj'].object_list), num
                )


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.group = Group.objects.create(title='Тестовая группа',
                                         slug='test-slug')
        new_post = []
        for i in range(13):
            new_post.append(Post(text=f'Тестовый текст {i}',
                                 group=cls.group,
                                 author=cls.user))
        Post.objects.bulk_create(new_post)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_correct_page_context_authorized_client(self):
        """Проверка паджинатора"""
        pages = [reverse('posts:index'),
                 reverse('posts:profile',
                         kwargs={'username': f'{self.user.username}'}),
                 reverse('posts:group_list',
                         kwargs={'slug': f'{self.group.slug}'})]
        for page in pages:
            response1 = self.authorized_client.get(page)
            response2 = self.authorized_client.get(page + '?page=2')
            self.assertEqual(len(response1.context['page_obj']), 10)
            self.assertEqual(len(response2.context['page_obj']), 3)


class PostImageViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='PostImageViewsTest')
        cls.group = Group.objects.create(
            title='PostImageViewsTest',
            slug='post_image_views_test'
        )
        small_gif = (
            "https://w-dog.ru/wallpapers/9/17/322057789001671/"
            + "zakat-nebo-solnce-" +
            + "luchi-oblaka-tuchi-pole-kolosya-zelenye-trava.jpg"
        )
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='some text',
            author=cls.user,
            group=cls.group,
            image=cls.image
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_images_show_in_context(self):
        """
        Изображение передаётся на страницы:
        index, group_posts, profile, post_detail.
        """
        urls = (
            reverse('posts:index'),
            reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ),
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            ),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                page_obj = response.context.get('page_obj', [None])
                post = page_obj[0] or response.context.get('post')
                self.assertIsNotNone(post.image)


class CommentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth1')
        cls.user2 = User.objects.create_user(username='auth2')

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Тестовая группа',
                                          slug='test_group')
        self.post = Post.objects.create(text='Тестовый текст',
                                        group=self.group,
                                        author=self.user)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с
           правильным контекстом комментария."""
        self.comment = Comment.objects.create(post_id=self.post.id,
                                              author=self.user,
                                              text='Тестовый коммент')
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        comments = {response.context['comments'][0].text: 'Тестовый коммент',
                    response.context['comments'][0].author: self.user.username
                    }
        for value, expected in comments.items():
            self.assertEqual(comments[value], expected)
        self.assertTrue(response.context['form'], 'форма получена')


class FollowTests(TestCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.user = User.objects.create_user(
            username='User1'
        )
        self.author = User.objects.create_user(
            username='User2')
        self.test_post = Post.objects.create(
            author=self.author,
            text='Текстовый текст')

        self.FOLLOW_URL = reverse(
            'posts:profile_follow', kwargs={'username': self.author.username}
        )
        self.UNFOLLOW_URL = reverse(
            'posts:profile_unfollow', kwargs={'username': self.author.username}
        )
        self.PROFILE_URL = reverse('posts:profile',
                                   kwargs={'username':
                                           self.author.username})
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_auth_user_can_follow(self):
        """Тест авторизованный пользователь может
        подписываться."""
        count_followers = Follow.objects.all().count()
        response = self.authorized_client.post(self.FOLLOW_URL)
        self.assertEqual(count_followers, 1)
        self.assertRedirects(response, self.PROFILE_URL)

    def test_auth_user_can_unfollow(self):
        """Тест авторизованный пользователь может
        отписаться."""

        count_followers = Follow.objects.all().count()
        self.authorized_client.get(self.FOLLOW_URL)
        self.authorized_client.get(self.UNFOLLOW_URL)
        self.assertEqual(count_followers, 0)

    def test_follower_see_new_post(self):
        """У подписчика появляется новый пост автора.
        А у не подписчика его нет"""
        Follow.objects.create(user=self.user,
                              author=self.author)
        response_follow = self.authorized_client.get(
            reverse('posts:follow_index'))
        posts_follow = response_follow.context['page_obj']
        self.assertIn(self.test_post, posts_follow)

    def test_follower_not_see_new_post(self):
        """У не подписчика не появляется новый пост автора."""
        Follow.objects.create(user=self.user,
                              author=self.author)
        response_no_follower = self.author_client.get(
            reverse('posts:follow_index'))
        posts_no_follow = response_no_follower.context['page_obj']
        self.assertNotIn(self.test_post, posts_no_follow)
