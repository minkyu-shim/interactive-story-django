"""
URL configuration for django_engine project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from gameplay.views import (
    story_list, play_node, start_story, global_stats,
    create_story_view, edit_story_view, delete_story_view,
    add_page_view, add_choice_view, author_dashboard, signup,
    submit_rating_comment, edit_page_view, delete_page_view,
    edit_choice_view, delete_choice_view
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', signup, name='signup'),
    path('', story_list, name='story_list'),
    path('author/', author_dashboard, name='author_dashboard'),

    # Logic to find the start node
    path('story/<int:story_id>/start/', start_story, name='start_story'),
    path('story/<int:story_id>/rate/', submit_rating_comment, name='submit_rating_comment'),

    # Play node
    path('play/<int:story_id>/<str:node_id>/', play_node, name='play_node'),
    
    # Stats
    path('stats/', global_stats, name='global_stats'),

    # Author CRUD
    path('author/story/create/', create_story_view, name='create_story'),
    path('author/story/<int:story_id>/edit/', edit_story_view, name='edit_story'),
    path('author/story/<int:story_id>/delete/', delete_story_view, name='delete_story'),
    
    # Pages
    path('author/story/<int:story_id>/page/add/', add_page_view, name='add_page'),
    path('author/story/<int:story_id>/page/<str:page_id>/edit/', edit_page_view, name='edit_page'),
    path('author/story/<int:story_id>/page/<str:page_id>/delete/', delete_page_view, name='delete_page'),

    # Choices
    path('author/story/<int:story_id>/page/<str:page_id>/choice/add/', add_choice_view, name='add_choice'),
    path('author/story/<int:story_id>/page/<str:page_id>/choice/<int:choice_id>/edit/', edit_choice_view, name='edit_choice'),
    path('author/story/<int:story_id>/choice/<int:choice_id>/delete/', delete_choice_view, name='delete_choice'),
]
