import shutil
import tempfile


from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post, Comment
from posts.forms import PostForm


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    """Проверка постов."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        """Удаляет временную директорию и всё её содержимое"""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.guest_client = Client()

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        # Подсчитаем количество записей в Post
        posts_count = Post.objects.count()
        form_data = {
            'author': self.user.username,
            'text': 'Тестовый текст',
            'group': self.group.id,
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        # Проверяем, что запись создалась
        last_post = Post.objects.all().order_by('-pk')[0]
        self.assertEqual(last_post.author.username, form_data['author'])
        self.assertEqual(last_post.group.id, form_data['group'])
        self.assertEqual(last_post.text, form_data['text'])

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        # Подсчитаем количество записей в Post
        posts_count = Post.objects.count()
        form_data = {
            'author': self.user.username,
            'text': 'Измененный тестовый текст',
            'group': self.group.id,
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        # Проверяем, что число постов не увеличилось
        self.assertEqual(Post.objects.co unt(), posts_count)
        # Проверяем, что запись изменилась
        last_post = Post.objects.get(id=self.post.id)
        self.assertEqual(last_post.author.username, form_data['author'])
        self.assertEqual(last_post.group.id, form_data['group'])
        self.assertEqual(last_post.text, form_data['text'])

    def test_title_label(self):
        """Проверяет метки полей формы"""
        text_label = self.form.fields['text'].label
        group_label = self.form.fields['group'].label
        self.assertEqual(text_label, 'Текст поста')
        self.assertEqual(
            group_label,
            'Группа'
        )

    def test_title_help_text(self):
        """Проверяет тексты подсказок"""
        text_help_text = self.form.fields['text'].help_text
        group_help_text = self.form.fields['group'].help_text
        self.assertEqual(text_help_text, '')
        self.assertEqual(group_help_text, '')

    def test_create_comment(self):
        """Валидная форма создаст комментарий у поста."""
        comments_count = Comment.objects.count()
        post = Post.objects.first()
        form_data = {'text': 'test comment'}
        expected_redirect = reverse(
            'posts:post_detail',
            kwargs={'post_id': post.id}
        )

        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, expected_redirect)
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
                author=self.user,
                post=post
            ).exists()
        )

    def test_guest_cant_create_comment(self):
        """Не авторизованный пользователь не сможет создать комментарий."""
        comments_count = Comment.objects.count()
        post = Post.objects.first()
        form_data = {'text': 'test comment'}
        next_url = f'/posts/{post.id}/comment/'
        expected_redirect = f'{reverse(settings.LOGIN_URL)}?next={next_url}'

        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, expected_redirect)
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertFalse(
            Comment.objects.filter(
                text=form_data['text'],
                author=self.user,
                post=post
            ).exists()
        )
