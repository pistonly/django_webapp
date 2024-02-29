from django.db import models
from photologue.models import Gallery
from django.contrib.auth.models import User

class ProductBatch(models.Model):
    batch_number = models.CharField(max_length=100, unique=True)
    gallery = models.OneToOneField(Gallery, on_delete=models.CASCADE, related_name='product_batch')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_batches')
    production_date = models.DateField()

    def __str__(self):
        return self.batch_number
