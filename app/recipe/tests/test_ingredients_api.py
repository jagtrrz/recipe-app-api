from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe
)

from recipe.serializers import (
    IngredientSerializer
)

INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """Create and return a tag- detail URL."""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='test@test.com', password='test123'):
    user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

    return user


class PublicIngredientsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        Ingredient.objects.create(user=self.user, name='ingredient1')
        Ingredient.objects.create(user=self.user, name='ingredient2')

        response = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_ingredients_list_to_user(self):
        other_user = create_user(email='example3@example.com',
                                 password='12345670')

        ingredient = Ingredient.objects.create(user=self.user,
                                               name='ingredient1')
        Ingredient.objects.create(user=other_user, name='ingredient2')

        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['name'], ingredient.name)
        self.assertEqual(response.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        ingredient = Ingredient.objects.create(user=self.user,
                                               name='ingredient1')

        payload = {
            'name': 'update ingredient'
        }
        url = detail_url(ingredient.id)

        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        ingredient = Ingredient.objects.create(user=self.user,
                                               name='ingredient1')

        url = detail_url(ingredient.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        ingredient = Ingredient.objects.create(user=self.user,
                                               name='ingredient1')
        ingredient_2 = Ingredient.objects.create(user=self.user,
                                                 name='ingredient2')

        recipe = Recipe.objects.create(
            user=self.user,
            title="Recipe Title",
            time_minutes=25,
            price=Decimal('3.45')
        )

        recipe.ingredients.add(ingredient)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        serializer_1 = IngredientSerializer(ingredient)
        serializer_2 = IngredientSerializer(ingredient_2)

        self.assertIn(serializer_1.data, response.data)
        self.assertNotIn(serializer_2.data, response.data)

    def test_filtered_ingredientes_unique(self):
        ingredient = Ingredient.objects.create(user=self.user,
                                               name='ingredient1')
        Ingredient.objects.create(user=self.user,
                                  name='ingredient2')

        recipe_1 = Recipe.objects.create(
            user=self.user,
            title="Recipe Title 1",
            time_minutes=25,
            price=Decimal('3.45')
        )

        recipe_2 = Recipe.objects.create(
            user=self.user,
            title="Recipe Title 2",
            time_minutes=45,
            price=Decimal('5.45')
        )
        recipe_1.ingredients.add(ingredient)
        recipe_2.ingredients.add(ingredient)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(response.data), 1)
