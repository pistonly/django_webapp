from django.contrib import admin
from .models import ProductBatch
from photologue.admin import GalleryAdmin
from photologue.models import Gallery

class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'operator', 'production_date', 'gallery_link')

    def gallery_link(self, obj):
        return u'<a href="/admin/photologue/gallery/%s/">%s</a>' % (obj.gallery.id, obj.gallery.title)
    gallery_link.allow_tags = True
    gallery_link.short_description = 'Gallery'

admin.site.register(ProductBatch, ProductBatchAdmin)

