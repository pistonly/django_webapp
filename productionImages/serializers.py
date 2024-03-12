from rest_framework import serializers
from django.utils.text import slugify
from photologue.models import Photo

class PhotoUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['image', 'title', 'caption', 'slug']
