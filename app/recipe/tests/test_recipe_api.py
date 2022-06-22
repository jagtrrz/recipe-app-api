"""
Test for the recipe api
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """ Test the public features of the recipe API. """

    def setUp(self):
        self.client = APIClient()
    
    