"""
Test for the tags api
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag

from recipe.serializers import (
    TagSerializer
)


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    """Create and return a tag- detail URL."""
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='test@test.com', password='test'):
    user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

    return user


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags."""
        Tag.objects.create(user=self.user, name='test1')
        Tag.objects.create(user=self.user, name='test2')

        response = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_tag_list_limited_to_user(self):
        """Test list of tags is limited to authenticated user."""
        other_user = create_user(email='other@example.com', password='test123')

        Tag.objects.create(user=other_user, name='test user 2')
        tag = Tag.objects.create(user=self.user, name='test2')

        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['name'], tag.name)
        self.assertEqual(response.data[0]['id'], tag.id)

    def test_update_tag(self):
        """ Test updating tags """
        tag = Tag.objects.create(user=self.user, name='test2')

        payload = {
            'name': 'update name'
        }
        url = detail_url(tag.id)

        response = self.client.patch(url, payload)
        
        self.assertEqual(response.status_code, status_code.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    # def test_get_recipe_detail(self):
    #     """Test get recipe detail."""
    #     recipe = create_recipe(user=self.user)

    #     url = detail_url(recipe.id)
    #     response = self.client.get(url)

    #     serializer = RecipeDetailSerializer(recipe)
    #     self.assertEqual(response.data, serializer.data)

    # def test_create_recipe(self):
    #     """Test to create a new recipe """
    #     payload = {
    #         'title': 'Sample recipe',
    #         'time_minutes': 30,
    #         'price': Decimal('5.99'),
    #     }

    #     response = self.client.post(RECIPES_URL, payload)

    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     recipe = Recipe.objects.get(id=response.data['id'])
    #     for k, v in payload.items():
    #         self.assertEqual(getattr(recipe, k), v)
    #     self.assertEqual(recipe.user, self.user)

    # def test_partial_update(self):
    #     """Test partial update of a recipe."""
    #     original_link = 'https://example.com/recipe.pdf'
    #     recipe = create_recipe(
    #         user=self.user,
    #         title='Sample recipe title',
    #         link=original_link,
    #     )

    #     payload = {'title': 'New recipe title'}
    #     url = detail_url(recipe.id)
    #     res = self.client.patch(url, payload)

    #     self.assertEqual(res.status_code, status.HTTP_200_OK)
    #     recipe.refresh_from_db()
    #     self.assertEqual(recipe.title, payload['title'])
    #     self.assertEqual(recipe.link, original_link)
    #     self.assertEqual(recipe.user, self.user)

    # def test_full_update(self):
    #     """Test full update of recipe."""
    #     recipe = create_recipe(
    #         user=self.user,
    #         title='Sample recipe title',
    #         link='https://exmaple.com/recipe.pdf',
    #         description='Sample recipe description.',
    #     )

    #     payload = {
    #         'title': 'New recipe title',
    #         'link': 'https://example.com/new-recipe.pdf',
    #         'description': 'New recipe description',
    #         'time_minutes': 10,
    #         'price': Decimal('2.50'),
    #     }
    #     url = detail_url(recipe.id)
    #     res = self.client.put(url, payload)

    #     self.assertEqual(res.status_code, status.HTTP_200_OK)
    #     recipe.refresh_from_db()
    #     for k, v in payload.items():
    #         self.assertEqual(getattr(recipe, k), v)
    #     self.assertEqual(recipe.user, self.user)

    # def test_update_user_returns_error(self):
    #     """Test changing the recipe user results in an error."""
    #     new_user = create_user(email='user2@example.com', password='test123')
    #     recipe = create_recipe(user=self.user)

    #     payload = {'user': new_user.id}
    #     url = detail_url(recipe.id)
    #     self.client.patch(url, payload)

    #     recipe.refresh_from_db()
    #     self.assertEqual(recipe.user, self.user)

    # def test_delete_recipe(self):
    #     """Test deleting a recipe successful."""
    #     recipe = create_recipe(user=self.user)

    #     url = detail_url(recipe.id)
    #     res = self.client.delete(url)

    #     self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
    #     self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    # def test_recipe_other_users_recipe_error(self):
    #     """Test trying to delete another users recipe gives error."""
    #     new_user = create_user(email='user2@example.com', password='test123')
    #     recipe = create_recipe(user=new_user)

    #     url = detail_url(recipe.id)
    #     res = self.client.delete(url)

    #     self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
    #     self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())
