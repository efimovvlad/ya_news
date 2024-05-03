# test_logic.py
from django.urls import reverse
import pytest
from pytest_django.asserts import assertRedirects, assertFormError
from pytils.translit import slugify
from http import HTTPStatus
from django.urls import reverse
from news.forms import BAD_WORDS, WARNING
from news.models import Comment, News


@pytest.mark.django_db
def test_anonymous_user_cant_create_comment(client, news, form_data):
    url = reverse('news:detail', args=(news.id,))
    # Совершаем запрос от анонимного клиента, в POST-запросе отправляем
    # предварительно подготовленные данные формы с текстом комментария.
    client.post(url, data=form_data)
    # Считаем количество комментариев.
    comments_count = Comment.objects.count()
    # Ожидаем, что комментариев в базе нет - сравниваем с нулём.
    assert comments_count == 0


def test_user_can_create_comment(author_client, news, form_data, author):
    # Совершаем запрос через авторизованный клиент.
    url = reverse('news:detail', args=(news.id,))
    response = author_client.post(url, data=form_data)
    # Проверяем, что редирект привёл к разделу с комментами.
    assertRedirects(response, f'{url}#comments')
    # Считаем количество комментариев.
    comments_count = Comment.objects.count()
    # Убеждаемся, что есть один комментарий.
    assert comments_count == 1
    # Получаем объект комментария из базы.
    comment = Comment.objects.get()
    # Проверяем, что все атрибуты комментария совпадают с ожидаемыми.
    assert comment.text == form_data['text']
    assert comment.news == news
    assert comment.author == author


def test_user_cant_use_bad_words(author_client, news):
    url = reverse('news:detail', args=(news.id,))
    # Формируем данные для отправки формы; текст включает
    # первое слово из списка стоп-слов.
    bad_words_data = {'text': f'Какой-то текст, {BAD_WORDS[0]}, еще текст'}
    # Отправляем запрос через авторизованный клиент.
    response = author_client.post(url, data=bad_words_data)
    # Проверяем, есть ли в ответе ошибка формы.
    assertFormError(
        response,
        form='form',
        field='text',
        errors=WARNING
    )
    # Дополнительно убедимся, что комментарий не был создан.
    comments_count = Comment.objects.count()
    assert comments_count == 0


def test_author_can_delete_comment(author_client, comment, news):
    url = reverse('news:detail', args=(news.id,))
    url_to_comments = url + '#comments'
    delete_url = reverse('news:delete', args=(comment.id,))
    # От имени автора комментария отправляем DELETE-запрос на удаление.
    response = author_client.delete(delete_url)
    # Проверяем, что редирект привёл к разделу с комментариями.
    # Заодно проверим статус-коды ответов.
    assertRedirects(response, url_to_comments)
    # Считаем количество комментариев в системе.
    comments_count = Comment.objects.count()
    # Ожидаем ноль комментариев в системе.
    assert comments_count == 0


def test_user_cant_delete_comment_of_another_user(not_author_client, comment):
    delete_url = reverse('news:delete', args=(comment.id,))
    # Выполняем запрос на удаление от пользователя-читателя.
    response = not_author_client.delete(delete_url)
    # Проверяем, что вернулась 404 ошибка.
    assert response.status_code == HTTPStatus.NOT_FOUND
    # Убедимся, что комментарий по-прежнему на месте.
    comments_count = Comment.objects.count()
    assert comments_count == 1


def test_author_can_edit_comment(author_client, news, comment, form_data):
    url = reverse('news:detail', args=(news.id,))
    url_to_comments = url + '#comments'
    edit_url = reverse('news:edit', args=(comment.id,))
    # Выполняем запрос на редактирование от имени автора комментария.
    response = author_client.post(edit_url, data=form_data)
    # Проверяем, что сработал редирект.
    assertRedirects(response, url_to_comments)
    # Обновляем объект комментария.
    comment.refresh_from_db()
    # Проверяем, что текст комментария соответствует обновленному.
    assert comment.text == form_data['text']


def test_user_cant_edit_comment_of_another_user(not_author_client, comment, form_data):
    edit_url = reverse('news:edit', args=(comment.id,))
    # Выполняем запрос на редактирование от имени другого пользователя.
    response = not_author_client.post(edit_url, data=form_data)
    # Проверяем, что вернулась 404 ошибка.
    assert response.status_code == HTTPStatus.NOT_FOUND
    # Обновляем объект комментария.
    comment.refresh_from_db()
    # Проверяем, что текст остался тем же, что и был.
    assert comment.text == 'Текст комментария'
