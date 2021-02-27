from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from posts.models import Post, Group, Follow, Comment
import shutil
import tempfile
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache


User = get_user_model()


class PostViewsTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.uploaded_2 = SimpleUploadedFile(
            name='big.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.test_author = User.objects.create_user(username='username')
        cls.group_1 = Group.objects.create(title='Группа-1', slug='test-slug-1', description='Group')
        cls.group_2 = Group.objects.create(title='Группа-2', slug='test-slug-2')
        cls.test_author_2 = User.objects.create_user(username='username_2')
        cls.test_author_3 = User.objects.create_user(username='username_3')

    @classmethod
    def tearDownClass(cls):
        # Модуль shutil - библиотека Python с прекрасными инструментами
        # для управления файлами и директориями:
        # создание, удаление, копирование, перемещение, изменение папок|файлов
        # Метод shutil.rmtree удаляет директорию и всё её содержимое
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        # Создаем авторизованный клиент
        self.guest_client = Client()
        self.user = User.objects.create_user(username='StanislavaBasova')
        self.authorized_client = Client()
        self.authorized_client_2 = Client()
        self.authorized_client_3 = Client()
        self.authorized_client.force_login(self.user)
        self.editor_client = Client()
        self.editor_client.force_login(PostViewsTests.test_author)
        self.authorized_client_2.force_login(PostViewsTests.test_author_2)
        self.authorized_client_3.force_login(PostViewsTests.test_author_3)

    def test_paginator(self):
        cache.clear()
        all_posts = []
        for i in range(0, 12, 1):
            all_posts.append(Post(text='Тестовый пост' + str(i), author=self.test_author))
        Post.objects.bulk_create(all_posts)
        response = self.guest_client.get(reverse('index'))
        self.assertEqual(len(response.context.get('page').object_list), 10)

    def test_correct_template_views(self):
        cache.clear()
        templates_pages_names = {
            'posts/index.html': reverse('index'),
            'posts/new.html': reverse('new_post'),
            'posts/group.html': (reverse('group_posts', args={'test-slug-1'}))
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_main_page_show_correct_context(self):
        cache.clear()
        self.post = Post.objects.create(
            text='Текст',
            author=self.test_author,
            group=self.group_1,
            image=self.uploaded
        )
        response = self.guest_client.get(reverse('index'))
        post_info_0 = response.context.get('page')[0]
        post_text_0 = post_info_0.text
        post_author_0 = post_info_0.author
        post_group_0 = post_info_0.group
        post_image_0 = post_info_0.image
        self.assertEqual(post_text_0, 'Текст')
        self.assertEqual(post_author_0.username, 'username')
        self.assertEqual(post_group_0.title, 'Группа-1')
        self.assertEqual(post_image_0, self.post.image)

    def test_group_page_show_correct_context(self):
        cache.clear()
        self.post = Post.objects.create(
            text='Текст',
            author=self.test_author,
            group=self.group_1,
            image=self.uploaded
        )
        response = self.authorized_client.get(reverse('group_posts', args={'test-slug-1'}))
        test_group_info = response.context.get('group')
        test_group_title_0 = test_group_info.title
        test_group_slug_0 = test_group_info.slug
        test_group_image_0 = response.context.get('page')[0].image
        self.assertEqual(test_group_title_0, 'Группа-1')
        self.assertEqual(test_group_slug_0, 'test-slug-1')
        self.assertEqual(test_group_image_0, self.post.image)

    def test_new_page_show_correct_context(self):
        cache.clear()
        response = self.authorized_client.get(reverse('new_post'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        for fiels_name, expected in form_fields.items():
            with self.subTest(value=fiels_name):
                form_field = response.context.get('form').fields.get(fiels_name)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    def test_post_in_correct_group(self):
        cache.clear()
        self.post = Post.objects.create(
            text='Текст',
            author=self.test_author,
            group=self.group_1
        )
        group_list = {
            'correct_group': reverse('group_posts', args={'test-slug-1'}),
            'wrong_group': reverse('group_posts', args={'test-slug-2'})
        }

        for the_group, reverse_name in group_list.items():
            with self.subTest():
                response = self.authorized_client.get(reverse_name)
                post_in_group = response.context.get('page')
                if the_group == 'correct_group':
                    self.assertIn(self.post, post_in_group)
                else:
                    self.assertNotIn(self.post, post_in_group)

    def test_main_page_shows_post(self):
        cache.clear()
        self.post = Post.objects.create(
            text='Текст',
            author=self.test_author,
            group=self.group_1
        )
        response = self.authorized_client.get(reverse("index"))
        main_page = response.context.get('page')
        self.assertIn(self.post, main_page)

    def test_edit_page_show_correct_context(self):
        cache.clear()
        self.post = Post.objects.create(
            text='Текст',
            author=self.test_author,
            group=self.group_1
        )
        response = self.editor_client.get('/username/1/edit/')
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        for fiels_name, expected in form_fields.items():
            with self.subTest(value=fiels_name):
                form_field = response.context.get('form').fields.get(fiels_name)
                self.assertIsInstance(form_field, expected)

    def test_profile_page_show_correct_context(self):
        cache.clear()
        self.post = Post.objects.create(
            text='Текст',
            author=self.test_author,
            group=self.group_1,
            image=self.uploaded
        )
        response = self.guest_client.get(reverse('profile', args={'username'}))
        post_info_0 = response.context.get('page')[0]
        post_text_0 = post_info_0.text
        post_author_0 = post_info_0.author
        post_group_0 = post_info_0.group
        post_image_0 = post_info_0.image
        self.assertEqual(post_text_0, 'Текст')
        self.assertEqual(post_author_0.username, 'username')
        self.assertEqual(post_group_0.title, 'Группа-1')
        self.assertEqual(post_image_0, self.post.image)

    def test_post_page_show_correct_context(self):
        cache.clear()
        self.post = Post.objects.create(
            text='Текст',
            author=self.test_author,
            group=self.group_1,
            image=self.uploaded
        )
        response = self.guest_client.get('/username/1/')
        post_info = response.context.get('post')
        post_text = post_info.text
        post_author = post_info.author
        post_group = post_info.group
        post_image = post_info.image
        self.assertEqual(post_text, 'Текст')
        self.assertEqual(post_author.username, 'username')
        self.assertEqual(post_group.title, 'Группа-1')
        self.assertEqual(post_image, self.post.image)

    def test_post_create_post_with_image(self):
        cache.clear()
        self.post = Post.objects.create(
            text='Текст',
            author=self.test_author,
            group=self.group_1
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст',
            'group': self.group_1.id,
            'image': self.uploaded_2
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(reverse('new_post'), data=form_data,\
             follow=True)
        # Проверяем, увеличилось ли число постов
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_page_is_not_updated_becuase_of_cash(self):
        post = Post.objects.create(
            text='Текст',
            author=self.test_author,
            group=self.group_1
        )
        response = self.authorized_client.get('index')
        cached_response_content = response.content
        # удалить один из постов который есть на закешированной странице
        Post.objects.filter(id=post.id).delete()
        response = self.authorized_client.get('index')
        self.assertEqual(cached_response_content, response.content)

    def test_authorized_user_can_follow_and_unfollow(self):
        Follow.objects.all().delete()
        Follow.objects.create(
            user=self.test_author,
            author=self.test_author_2
        )
        follow = Follow.objects.count() 
        form_data = {
            'user': self.test_author,
            'author': self.test_author_3
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(reverse('profile_follow', args={'username'}),\
             data=form_data, follow=True)
        # Проверяем, увеличилось ли число подписок
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Follow.objects.count(), follow + 1)

        response = self.authorized_client.post(reverse('profile_unfollow', args={'username'}),\
             data=form_data, follow=True)
        # Проверяем, уменьшилось ли число подписок
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Follow.objects.count(), follow)

    def test_new_post_appeared_for_followers_and_not_for_nonfollowers(self):
        cache.clear()
        self.post_1 = Post.objects.create(
            text='Текст_тест',
            author=self.test_author,
            group=self.group_1
        )
        self.post_2 = Post.objects.create(
            text='Текст_тест_2',
            author=self.test_author_3,
            group=self.group_1
        )
        form_data = {
            'user': self.test_author_2,
            'author': self.test_author
        }
        # Отправляем POST-запрос
        response = self.authorized_client_2.post(reverse('profile_follow', args={'username'}),\
             data=form_data, follow=True)
        follow_page = response.context.get('page')
        # появляется пост автора, на которого подписаны, и не появляется, на которого не подписаны
        self.assertIn(self.post_1, follow_page)
        self.assertNotIn(self.post_2, follow_page)

    def test_comments_only_for_authorized(self):
        cache.clear()
        self.post = Post.objects.create(
            text='Текст_тест',
            author=self.test_author,
            group=self.group_1
        )
        comments= Comment.objects.count()
        form_data_1 = {
            'post': self.post,
            'author': self.test_author_2,
            'text': 'Комментарий_1'
        }
        form_data_2 = {
            'post': self.post,
            'author': self.guest_client,
            'text': 'Комментарий_2'
        }
        # Отправляем POST-запрос
        response = self.authorized_client_2.post(reverse('add_comment', args=['username', 1]),\
            data=form_data_1, follow=True)
        self.assertEqual(Comment.objects.count(), comments + 1)
        response = self.guest_client.post(reverse('add_comment', args=['username', 1]),\
             data=form_data_2, follow=True)
        # комментариев не прибавилось
        self.assertEqual(Comment.objects.count(), comments + 1)
