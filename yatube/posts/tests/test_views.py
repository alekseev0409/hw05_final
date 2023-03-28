from django import forms
from django.test import Client, TestCase
from django.urls import reverse
from django.conf import settings
from ..models import Group, Post, User, Follow
from django.core.cache import cache


class PostTests(TestCase):
    def check_info(self, post):
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author.username, self.post.author.username)
        self.assertEqual(post.group.title, self.post.group.title)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.auth_user = User.objects.create_user(username='TestAuthUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='new-group-2',
            description='Тестовое описание 2'
        )

        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client_author = Client()
        self.authorized_client.force_login(PostTests.auth_user)
        self.authorized_client_author.force_login(PostTests.author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        page_names_templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.post.author}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.pk}
            ): 'posts/create_post.html',
            reverse('posts:create'): 'posts/create_post.html',
        }
        for reverse_name, template in page_names_templates.items():
            with self.subTest(template=template):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Шаблон главной страницы сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_info(response.context.get('page_obj')[0])

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        url = reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}
        )
        response = self.authorized_client.get(url)
        group_title = response.context.get('group').title
        group_description = response.context.get('group').description
        group_slug = response.context.get('group').slug
        self.assertEqual(group_title, self.group.title)
        self.assertEqual(group_description, self.group.description)
        self.assertEqual(group_slug, self.group.slug)
        self.check_info(response.context.get('page_obj')[0])

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        url = reverse('posts:profile', kwargs={'username': PostTests.author})
        response = self.authorized_client_author.get(url)
        self.check_info(response.context.get('page_obj')[0])

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        url = reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        response = self.authorized_client_author.get(url)
        self.check_info(response.context.get('post'))

    def test_create_post_edit_show_correct_context(self):
        """Шаблон редактирования поста create_post сформирован
        с правильным контекстом.
        """
        url = reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        response = self.authorized_client_author.get(url)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for field, expected in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context.get('form').fields.get(field)
                self.assertIsInstance(form_field, expected)

    def test_create_post_show_correct_context(self):
        """Шаблон создания поста create_post сформирован
        с правильным контекстом.
        """
        url = reverse('posts:create')
        response = self.authorized_client.get(url)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for field, expected in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context.get('form').fields.get(field)
                self.assertIsInstance(form_field, expected)

    def test_create_post_show_home_group_list_profile_pages(self):
        """Созданный пост отобразился на главной, на странице группы,
        в профиле пользователя.
        """
        urls = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ),
        )
        for url in urls:
            response = self.authorized_client_author.get(url)
            self.assertIn(self.post, response.context['page_obj'])

    def test_post_right_group(self):
        "Проверка правильной группы поста"
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertIn(self.post, response.context['page_obj'])

    def test_cache(self):
        "Тестирование кеша страницы index"
        response = self.client.get('posts:index')
        content = response.content
        Post.objects.all().delete()
        response = self.client.get('posts:index')
        self.assertEqual(response.content, content)
        cache.clear()
        response = self.client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, content)


class PaginatorViewsTest(TestCase):
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
        cls.posts = [
            Post(
                author=cls.author,
                text=f'Тестовый пост {i}',
                group=cls.group,
            )
            for i in range(settings.AMOUNT_POSTS)
        ]
        Post.objects.bulk_create(cls.posts)

    def test_first_page_contains_ten_records(self):
        """Количество постов на страницах index, group_list, profile
        равно 10.
        """
        urls = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ),
        )
        for url in urls:
            response = self.client.get(url)
            amount_posts = len(response.context.get('page_obj').object_list)
            self.assertEqual(amount_posts, settings.NUMBER_OBJECTS)

    def test_second_page_contains_three_records(self):
        """На страницах index, group_list, profile
        должно быть по три поста.
        """
        urls = (
            reverse('posts:index') + '?page=2',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ) + '?page=2',
            reverse(
                'posts:profile', kwargs={'username': self.author.username}
            ) + '?page=2',
        )
        for url in urls:
            response = self.client.get(url)
            amount_posts = len(response.context.get('page_obj').object_list)
            self.assertEqual(amount_posts, settings.LEN_PAGE_OBJ)


class FollowingViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = User.objects.create_user(username='author_1')
        cls.user_2 = User.objects.create_user(username='author_2')
        cls.post = Post.objects.create(
            author=cls.user_2,
            text='Тестовый текст',
        )
        cls.post_2 = Post.objects.create(
            author=cls.user_1,
            text='Тестовый текст 2',
        )
        cls.follow = Follow.objects.create(
            user=cls.user_2,
            author=cls.user_1
        )

    def setUp(self):
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(FollowingViewsTest.user_1)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(FollowingViewsTest.user_2)

    def test_follow(self):
        "Тест подписки пользователя"
        self.authorized_client_1.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_2.username}),
        )
        follower = Follow.objects.latest('id')
        user_following_count = self.user_1.follower.count()
        self.assertEqual(user_following_count, 1)
        self.assertEqual(self.user_1.id, follower.user.id)
        self.assertEqual(self.user_2.id, follower.author.id)

    def test_unfollow(self):
        self.authorized_client_2.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_1.username}),
        )
        user_unfollowing_count = self.user_2.follower.count()
        self.assertEqual(user_unfollowing_count, 0)

    def test_folowing_post(self):
        "Тест ленты подписок"
        self.authorized_client_1.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_2.username}),
        )
        response = self.authorized_client_1.get(
            reverse('posts:follow_index'),
        )
        self.assertIn('page_obj', response.context)
        post_text = response.context['page_obj'][0].text
        self.assertEqual(post_text, FollowingViewsTest.post.text)
        self.assertTemplateUsed(response, 'posts/follow.html')

    def test_not_folowing_post(self):
        "Тест ленты подписок не подписанного пользователя"
        self.authorized_client_1.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_2.username}),
        )
        response = self.authorized_client_2.get(
            reverse('posts:follow_index'),
        )
        self.assertIn('page_obj', response.context)
        context = response.context.get('page_obj')
        self.assertNotIn(FollowingViewsTest.post, context)
