from http import HTTPStatus
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Group, Post, User


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )

        cls.user_author = User.objects.create_user(
            username='user_author')
        cls.another_user = User.objects.create_user(
            username='another_user')

        cls.post = Post.objects.create(
            text='Текст который просто больше 15 символов...',
            author=cls.user_author,
            group=cls.group,
        )

        cls.url_guest_client = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.user_author}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
        }
        cls.url_authorized_client = {
            f'/posts/{cls.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        cls.url_found = [
            f'/posts/{cls.post.id}/comment/',
            f'/profile/{cls.user_author}/follow/',
            f'/profile/{cls.user_author}/unfollow/',
        ]

        cls.field_urls_code = {
            reverse(
                'posts:index'): HTTPStatus.OK,
            reverse(
                'posts:group_list',
                kwargs={'slug': cls.group.slug}): HTTPStatus.OK,
            reverse(
                'posts:group_list',
                kwargs={'slug': 'bad_slug'}): HTTPStatus.NOT_FOUND,
            reverse(
                'posts:profile',
                kwargs={'username': cls.user_author}): HTTPStatus.OK,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': cls.post.id}): HTTPStatus.OK,
            reverse(
                'posts:post_edit',
                kwargs={'post_id': cls.post.id}): HTTPStatus.FOUND,
            reverse(
                'posts:create'): HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        cls.field_urls_code_not_user = {
            reverse('posts:create'): HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND
        }

    def setUp(self):
        self.unauthorized_user = Client()
        self.post_author = Client()
        self.post_author.force_login(self.user_author)
        self.authorized_user = Client()
        self.authorized_user.force_login(self.another_user)

    def test_unauthorized_user_urls_status_code(self):
        """Проверка status_code для неавторизованного пользователя."""
        for url, template in self.url_guest_client.items():
            with self.subTest(url=url):
                response = self.unauthorized_user.get(url)
                self.assertTemplateUsed(response, template)

    def test_authorized_user_urls_status_code(self):
        """Проверка status_code для авторизованного пользователя."""
        for url, response_code in self.field_urls_code.items():
            with self.subTest(url=url):
                status_code = self.authorized_user.get(url).status_code
                self.assertEqual(status_code, response_code)

    def test_author_user_urls_status_code(self):
        """Проверка status_code для авторизированого автора."""
        for url, response_code in self.field_urls_code_not_user.items():
            with self.subTest(url=url):
                status_code = self.post_author.get(url).status_code
                self.assertEqual(status_code, response_code)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            reverse(
                'posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.user_author}): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}): 'posts/create_post.html',
            reverse(
                'posts:create'): 'posts/create_post.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.post_author.get(adress)
                self.assertTemplateUsed(response, template)
