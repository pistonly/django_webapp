    function addImagesToDiv(data) {

        data.forEach(function(photo) {
            $(photo.img_id).attr({
                src: photo.thumbnail,
                alt: photo.title,
                'data-original-url': photo.url,
                'data-title': photo.title
            });
        });
        if (data.length) {
            showOriginImage(data[0].url, data[0].title);
        }
    }

    function showOriginImage(url, title) {
        $("#origin-image").attr("src", url);
        $("#origin-image").attr("alt", title);
    }

    function getProductImages(batch_number) {

        $.ajax({
            url: product_image_url,
            type: "POST",
            data: {
                batch_number: batch_number
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(data) {
                addImagesToDiv(data.urls);
            },
            error: function(xhr, status, error) {
                console.error("An error occurred: " + error);
            }
        });
    }

    function getLatestProduct() {
        const url = $("#latest-product-url").data("url");
        $.ajax({
            url: url,
            type: "POST",
            dataType: "json",
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(data) {
                console.log("getlast product");
                console.log(data);
                $('#production-input').val(data.batch_number);
                // addImagesToDiv(data.urls);
                data.urls.forEach(function(photo) {
                    console.log(photo);
                    $(photo.img_id).attr({
                        src: photo.thumbnail,
                        alt: photo.title,
                        'data-original-url': photo.url,
                        'data-title': photo.title
                    });
                });
            },
            error: function(xhr, status, error) {
                console.error("An error occurred: " + error);
            }
        });
    }
