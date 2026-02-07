from django.urls import path


def empty_view(request):
    pass


urlpatterns = [
    path("articles/<object_id:pk>/", empty_view, name="article-detail"),
]
