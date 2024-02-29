from django.shortcuts import get_object_or_404, render

# def product_batch_gallery(request, batch_number):
#     batch = get_object_or_404(ProductBatch, batch_number=batch_number)
#     photos = batch.gallery.photos.all()
#     return render(request, 'gallery.html', {'batch': batch, 'photos': photos})

def production_view(request):
    return render(request, "productionImages/gallery.html")
