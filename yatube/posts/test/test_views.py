import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django import forms
from django.conf import settings
from posts.forms import PostForm
from django.core.cache import cache

from ..models import Follow, Post, Group, Comment

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
        post_text = 'cached_index_page_post'
        post = Post.objects.create(
            text=post_text,
            author=self.user
        )

        response_before_post_delete = self.client.get(reverse('posts:index'))
        post.delete()
        response_before_clear_cache = self.client.get(reverse('posts:index'))
        cache.clear()
        response_after_clear_cache = self.client.get(reverse('posts:index'))

        self.assertIn(post_text, str(response_before_post_delete.content))
        self.assertNotIn(post_text, str(response_after_clear_cache.content))
        self.assertNotEqual(response_before_clear_cache,
                            response_after_clear_cache)

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
        cls.group = Group.objects.create(
            title='test group',
            slug='test-group',
            description='test description group'
        )
        cls.user = User.objects.create_user(username='PaginatorViewsTest')
        cls.POSTS_COUNT = 15
        for _ in range(cls.POSTS_COUNT):
            Post.objects.create(
                text='test post',
                author=cls.user,
                group=cls.group
            )

        cls.INDEX_URL = reverse('posts:index')
        cls.GROUP_POSTS = reverse(
            'posts:group_list',
            kwargs={'slug': cls.group.slug}
        )
        cls.PROFILE_URL = reverse(
            'posts:profile',
            kwargs={'username': cls.user.username}
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.user)

    def test_first_page_contains_10_records(self):
        """
        Первая страница шаблонов:
        index, group_posts, profile отображает 10 постов.
        """
        names_urls = {
            'index': self.INDEX_URL,
            'group_posts': self.GROUP_POSTS,
            'profile': self.PROFILE_URL,
        }
        for name, url in names_urls.items():
            with self.subTest(name=name):
                response = self.authorized_client.get(url)
                self.assertEqual(
                    len(response.context['page_obj']), 10)

    def test_second_page_contains_5_records(self):
        """
        Вторая страница шаблонов:
        index, group_posts, profile отображает 5 постов.
        """
        names_urls = {
            'index': self.INDEX_URL + '?page=2',
            'group_posts': self.GROUP_POSTS + '?page=2',
            'profile': self.PROFILE_URL + '?page=2',
        }
        posts_on_second_page = self.POSTS_COUNT - 10
        for name, url in names_urls.items():
            with self.subTest(name=name):
                response = self.authorized_client.get(url)
                self.assertEqual(
                    len(response.context['page_obj']), posts_on_second_page)


class PostImageViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Описание тестовой группы',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='Test_user')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            pub_date='2022-08-23 9-00-00',
            image=cls.image
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.post.author)

    def context_post_and_page(self, response, flag=False):
        """Проверка поста на странице."""
        if flag is True:
            post = response.context['post']
        else:
            post = response.context['page_obj'][0]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.id, self.post.id)
        self.assertEqual(post.image, self.post.image)

    def test_context_post_in_page_index(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.context_post_and_page(response)

    def test_context_post_in_page_group(self):
        """Шаблон group_list сформирован с правильным контекстом
        отфильтрованных по группе.
        """
        response = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        self.context_post_and_page(response)
        group = response.context['group']
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(response.context['group'], self.group)

    def test_post_not_used_in_other_group(self):
        """Пост не используется в чужой группе."""
        Post.objects.all().delete()
        Post.objects.create(
            author=self.user,
            text='Тестовый текст_2',
            group=self.group
        )
        group_new = Group.objects.create(
            title='Тестовая группа_2',
            slug='test_slug_2',
            description='Описание тестовой группы_2'
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', args=(group_new.slug,)))
        self.assertEqual(len(response.context['page_obj']), 0)
        response = self.authorized_client.get(
            reverse('posts:group_list', args=(self.group.slug,)))
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_context_post_in_page_profile(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.user.username,)))
        self.context_post_and_page(response)
        self.assertEqual(
            response.context['author'], self.post.author
        )

    def test_context_post_in_page_post_detail(self):
        """Шаблон post_detail сформирован
        с правильным контекстом.
        """
        response = self.authorized_client.get(
            reverse('posts:post_detail', args=(self.post.id,)))
        self.context_post_and_page(response, True)

    def test_context_post_in_page_edit_and_create_post(self):
        """Шаблон create_post сформирован с
        правильным контекстом.
        """
        url_page = (
            ('posts:post_edit', (self.post.id,)),
            ('posts:post_create', None,)
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for name, args in url_page:
            with self.subTest(name=name):
                response = self.authorized_client.get(
                    reverse(name, args=args)
                )
                self.assertIn('form', response.context)
                self.assertIsInstance(
                    response.context['form'], PostForm
                )
                for value, expect in form_fields.items():
                    with self.subTest(value=value):
                        field_type = (
                            response
                            .context
                            .get('form')
                            .fields
                            .get(value)
                        )
                        self.assertIsInstance(field_type, expect)


class CommentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth1')
        cls.user2 = User.objects.create_user(username='auth2')
        cls.group = Group.objects.create(title='Тестовая группа',
                                         slug='test_group')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            group=cls.group,
            author=cls.user)
        cls.comment = Comment.objects.create(
            post_id=cls.post.id,
            author=cls.user,
            text='Тестовый коммент')

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с
           правильным контекстом комментария."""
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
        self.assertEqual(count_followers, 0)
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
