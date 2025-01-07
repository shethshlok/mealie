from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import UUID4

from mealie.repos.repository_factory import AllRepositories
from mealie.schema.recipe.recipe import Recipe
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser

x
@pytest.fixture(scope="function")
def unique_recipe(api_client: TestClient, unique_user: TestUser):
    payload = {"name": random_string(length=20)}
    response = api_client.post(api_routes.recipes, json=payload, headers=unique_user.token)
    assert response.status_code == 201

    response_data = response.json()
    recipe_response = api_client.get(api_routes.recipes_slug(response_data), headers=unique_user.token)

    return Recipe(**recipe_response.json())


def random_comment(recipe_id: UUID4) -> dict:
    if recipe_id is None:
        raise ValueError("recipe_id is required")
    return {
        "recipeId": str(recipe_id),
        "text": random_string(length=50),
    }


def test_create_comment(api_client: TestClient, unique_recipe: Recipe, unique_user: TestUser):
    # Update user's full name
    update_data = {"name": "Test User Full Name"}

    # Create Comment
    create_data = random_comment(unique_recipe.id)
    response = api_client.post(api_routes.comments, json=create_data, headers=unique_user.token)
    assert response.status_code == 201

    response_data = response.json()
    
    # Add a check for the 'user' and 'name' fields
    assert "user" in response_data
    assert "name" in response_data["user"]
    assert response_data["user"]["name"] == update_data["name"]

    # Check for Proper Association
    response = api_client.get(api_routes.recipes_slug_comments(unique_recipe.slug), headers=unique_user.token)
    assert response.status_code == 200

    comments = response.json()
    assert len(comments) == 1
    assert len(comments[0]["user"]["name"]) > 0
    assert comments[0]["user"]["name"] == update_data["name"]


def test_update_comment(api_client: TestClient, unique_recipe: Recipe, unique_user: TestUser):
    # Create Comment
    create_data = random_comment(unique_recipe.id)
    response = api_client.post(api_routes.comments, json=create_data, headers=unique_user.token)
    assert response.status_code == 201

    comment_id = response.json()["id"]

    # Update Comment
    update_data = random_comment(unique_recipe.id)
    update_data["id"] = comment_id

    response = api_client.put(api_routes.comments_item_id(comment_id), json=update_data, headers=unique_user.token)

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["recipeId"] == str(unique_recipe.id)
    assert response_data["text"] == update_data["text"]
    assert response_data["userId"] == str(unique_user.user_id)


def test_delete_comment(api_client: TestClient, unique_recipe: Recipe, unique_user: TestUser):
    # Create Comment
    create_data = random_comment(unique_recipe.id)
    response = api_client.post(api_routes.comments, json=create_data, headers=unique_user.token)
    assert response.status_code == 201

    # Delete Comment
    comment_id = response.json()["id"]
    response = api_client.delete(api_routes.comments_item_id(comment_id), headers=unique_user.token)
    assert response.status_code == 200

    # Validate Deletion
    response = api_client.get(api_routes.comments_item_id(comment_id), headers=unique_user.token)

    assert response.status_code == 404


def test_admin_can_delete(
    unfiltered_database: AllRepositories,
    api_client: TestClient,
    unique_recipe: Recipe,
    unique_user: TestUser,
    admin_user: TestUser,
):
    # Make sure admin belongs to same group/household as user
    admin_data = unfiltered_database.users.get_one(admin_user.user_id)
    assert admin_data
    admin_data.group_id = UUID(unique_user.group_id)
    admin_data.household_id = UUID(unique_user.household_id)
    unfiltered_database.users.update(admin_user.user_id, admin_data)

    # Create Comment
    create_data = random_comment(unique_recipe.id)
    response = api_client.post(api_routes.comments, json=create_data, headers=unique_user.token)
    assert response.status_code == 201

    # Delete Comment
    comment_id = response.json()["id"]
    response = api_client.delete(api_routes.comments_item_id(comment_id), headers=admin_user.token)
    assert response.status_code == 200

    # Validate Deletion
    response = api_client.get(api_routes.comments_item_id(comment_id), headers=admin_user.token)

    assert response.status_code == 404


def test_user_can_comment_on_other_household(api_client: TestClient, unique_recipe: Recipe, h2_user: TestUser):
    # Create Comment
    create_data = random_comment(unique_recipe.id)
    response = api_client.post(api_routes.comments, json=create_data, headers=h2_user.token)
    assert response.status_code == 201

    # Delete Comment
    comment_id = response.json()["id"]
    response = api_client.delete(api_routes.comments_item_id(comment_id), headers=h2_user.token)
    assert response.status_code == 200

    # Validate Deletion
    response = api_client.get(api_routes.comments_item_id(comment_id), headers=h2_user.token)

    assert response.status_code == 404
