"""
Test for the tags api
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Tag,
    Recipe
)

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Test deleting a tag."""
        tag = Tag.objects.create(user=self.user, name='Breakfast')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        tag = Tag.objects.create(user=self.user, name='tag1')
        tag_2 = Tag.objects.create(user=self.user, name='tag2')

        recipe = Recipe.objects.create(
            user=self.user,
            title="Recipe Title",
            time_minutes=25,
            price=Decimal('3.45')
        )

        recipe.tags.add(tag)

        response = self.client.get(TAGS_URL, {'assigned_only': 1})

        serializer_1 = TagSerializer(tag)
        serializer_2 = TagSerializer(tag_2)

        self.assertIn(serializer_1.data, response.data)
        self.assertNotIn(serializer_2.data, response.data)

    def test_filtered_tags_unique(self):
        tag = Tag.objects.create(user=self.user, name='tag1')
        Tag.objects.create(user=self.user, name='tag2')

        recipe_1 = Recipe.objects.create(
            user=self.user,
            title="Recipe Title 1",
            time_minutes=25,
            price=Decimal('3.45')
        )

        recipe_2 = Recipe.objects.create(
            user=self.user,
            title="Recipe Title 2",
            time_minutes=35,
            price=Decimal('4.45')
        )
        recipe_1.tags.add(tag)
        recipe_2.tags.add(tag)

        response = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(response.data), 1)
