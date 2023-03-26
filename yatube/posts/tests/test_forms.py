from http import HTTPStatus

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post, User, Comment


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.auth_user = User.objects.create_user(username='TestAuthUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст поста',
            group=cls.group,
        )
        cls.form = PostForm()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client_author = Client()
        self.authorized_client.force_login(PostCreateFormTests.auth_user)
        self.authorized_client_author.force_login(PostCreateFormTests.author)
        self.guest_client = Client()

    def test_create_new_post(self):
        "Отправка формы со страницы create"
        count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )
        form_data = {
            'text': 'тест',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client_author.post(
            reverse('posts:create'),
            data=form_data,
            follow=True,
        )
        new_post = Post.objects.latest('created')
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.post.author}),
        )
        self.assertEqual(Post.objects.count(), count + 1)
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group.pk, form_data['group'])
        self.assertTrue(new_post.image)
        self.assertEqual(new_post.author, self.author)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_author_edit_post(self):
        """Валидная форма изменяет запись в Posts."""

        self.authorized_client_author.get(f'/posts/{self.post.pk}/edit/')
        form_data = {
            'text': 'Отредактированный в форме текст',
            'group': self.group.pk,
        }
        response = self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )

        edit_post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(edit_post.text, form_data['text'])
        self.assertEqual(edit_post.group.pk, form_data['group'])

    def test_comment_post(self):
        "Отправка формы add_comment авторизированным пользователем"
        count = Comment.objects.count()
        form_data = {
            'text': 'Тест',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        comment = self.post.comments.all()[0]
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
        )
        self.assertEqual(Comment.objects.count(), count + 1)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, self.auth_user)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_comment_guest_client_post(self):
        "Отправка формы add_comment гостем "
        count = Comment.objects.count()
        form_data = {
            'text': 'Тест',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), count)
        self.assertRedirects(
            response,
            ('/auth/login/?next=/posts/1/comment/'),
        )
