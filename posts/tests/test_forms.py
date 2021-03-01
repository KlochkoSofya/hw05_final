from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Post, Group
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache


User = get_user_model()


class PostCreateFormTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем запись в базе данных

        cls.group = Group.objects.create(title='Группа', slug='test-slug')
        cls.post = Post.objects.create(
            text='Текст',
            author=User.objects.create_user(username='StasBasov'),
            group=cls.group
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        self.user = User.objects.create_user(username='StanislavaBasova')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post_only_with_correct_image(self):
        cache.clear()
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
            content_type='image/gif'
        )
        form_data = {
            'image': uploaded,
            'text': 'Текст',
            'group': Group.objects.get(slug='test-slug').id
        }
        posts_count = Post.objects.count()
        # Отправляем POST-запрос
        response = self.authorized_client.post(reverse('new_post'), data=form_data, follow=True)
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, 200)

    def test_create_post_only_with_correct_image(self):
        cache.clear()
        small_text = (b'\x47\x49\x46\x38\x39\x61\x02\x00')
        uploaded_2 = SimpleUploadedFile(
            name='small.txt',
            content=small_text,
            content_type='pain/txt'
        )
        form_data_2 = {
            'image': uploaded_2,
            'text': 'Текст',
            'group': Group.objects.get(slug='test-slug').id
        }
        posts_count = Post.objects.count()
        # Отправляем POST-запрос
        response_2 = self.authorized_client.post(reverse('new_post'), data=form_data_2, follow=True)
        # Проверяем, что число постов не увеличилось
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFormError(response_2, 'form', 'image', (
            'Загрузите правильное изображение. Файл, который вы загрузили, поврежден или не является изображением.'))
    
    def test_edit_post(self):
        form_data = {'text': 'Текст'}
        self.authorized_client.post(
            reverse('post_edit', args=[self.user.username, self.post.id]), data=form_data, follow=True)
        self.assertEqual(Post.objects.filter(id=self.post.id).last().text, 'Текст')
