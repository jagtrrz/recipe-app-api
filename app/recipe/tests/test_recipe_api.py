from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Recipe, Tag, Ingredient)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)
    new_recipe = Recipe.objects.create(user=user, **defaults)
    return new_recipe


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(RECIPES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        other_user = create_user(email='other@example.com', password='test123')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        response = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(response.data, serializer.data)

    def test_create_recipe(self):
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 30,
            'price': Decimal('5.99'),
        }

        response = self.client.post(RECIPES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link,
        )

        payload = {'title': 'New recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link='https://exmaple.com/recipe.pdf',
            description='Sample recipe description.',
        )

        payload = {
            'title': 'New recipe title',
            'link': 'https://example.com/new-recipe.pdf',
            'description': 'New recipe description',
            'time_minutes': 10,
            'price': Decimal('2.50'),
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_users_recipe_error(self):
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        payload = {
            'title': 'Paella',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [
                {'name': 'Spanish'},
                {'name': 'rice'}
            ]
        }
        response = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertTrue(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in recipe.tags.all():
            exists = recipe.tags.filter(
                name=tag.name,
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tag(self):
        tag_indian = Tag.objects.create(name='Indian', user=self.user)
        payload = {
            'title': 'Pongal',
            'time_minutes': 35,
            'price': Decimal('4.00'),
            'tags': [{'name': 'Indian'}, {'name': 'asian'}]
        }
        response = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertTrue(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_with_exist_recipe_on_update(self):
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assing_tag(self):
        tag_breakfast = Tag.objects.create(name='Breakfast', user=self.user)
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(name='Lunch', user=self.user)
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        tag = Tag.objects.create(name='Breakfast', user=self.user)
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)
        self.assertNotIn(tag, recipe.tags.all())

    def test_create_recipe_with_new_ingredient(self):
        payload = {
            'title': 'Paella',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'ingredients': [
                {'name': 'rice'},
                {'name': 'salt'}
            ],
        }
        response = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in recipe.ingredients.all():
            exists = recipe.ingredients.filter(
                name=ingredient.name,
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        ingredient = Ingredient.objects.create(user=self.user,
                                               name='ingredient1')
        payload = {
            'title': 'Paella',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'ingredients': [
                {'name': 'ingredient1'},
                {'name': 'salt'}
            ],
        }

        response = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertTrue(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_recipe_update(self):
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'Lemon'}]}
        url = detail_url(recipe.id)

        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        new_ingredient = Ingredient.objects.get(user=self.user, name='Lemon')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        new_ingredient = Ingredient.objects.create(user=self.user,
                                                   name='ingredient1')

        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(new_ingredient)

        lemon_ingredient = Ingredient.objects.create(name='lemon',
                                                     user=self.user)
        payload = {'ingredients': [{'name': 'lemon'}]}

        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(lemon_ingredient, recipe.ingredients.all())
        self.assertNotIn(new_ingredient, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        ingredient = Ingredient.objects.create(user=self.user,
                                               name='ingredient1')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_filter_recipes_by_tag(self):
        first_recipe = create_recipe(user=self.user, title="First Recipe")
        second_recipe = create_recipe(user=self.user, title="Second Recipe")
        third_recipe = create_recipe(user=self.user, title="Third Recipe")

        first_tag = Tag.objects.create(name='FirstTag', user=self.user)
        second_tag = Tag.objects.create(name='SecondTag', user=self.user)

        first_recipe.tags.add(first_tag)
        second_recipe.tags.add(second_tag)

        params = {'tags': f'{first_tag.id},{second_tag.id}'}

        response = self.client.get(RECIPES_URL, params)

        first_serializer = RecipeSerializer(first_recipe)
        second_serializer = RecipeSerializer(second_recipe)
        third_serializer = RecipeSerializer(third_recipe)

        self.assertIn(first_serializer.data, response.data)
        self.assertIn(second_serializer.data, response.data)
        self.assertNotIn(third_serializer.data, response.data)

    def test_filter_recipes_by_ingredients(self):
        first_recipe = create_recipe(user=self.user, title="First Recipe")
        second_recipe = create_recipe(user=self.user, title="Second Recipe")
        third_recipe = create_recipe(user=self.user, title="Third Recipe")

        first_ingredient = Ingredient.objects.create(name='FirstIngredient',
                                                     user=self.user)
        second_ingredient = Ingredient.objects.create(name='SecondIngredient',
                                                      user=self.user)

        first_recipe.ingredients.add(first_ingredient)
        second_recipe.ingredients.add(second_ingredient)

        params = {'ingredients': f'{first_ingredient.id},'
                                 f'{second_ingredient.id}'}

        response = self.client.get(RECIPES_URL, params)

        first_serializer = RecipeSerializer(first_recipe)
        second_serializer = RecipeSerializer(second_recipe)
        third_serializer = RecipeSerializer(third_recipe)

        self.assertIn(first_serializer.data, response.data)
        self.assertIn(second_serializer.data, response.data)
        self.assertNotIn(third_serializer.data, response.data)


class ImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123',
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
