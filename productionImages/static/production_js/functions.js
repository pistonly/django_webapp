    function addImagesToDiv(data) {
        var $imagesDiv = $('#product-images'); // 获取div元素
        $imagesDiv.empty(); // 清空div中的现有内容

        data.forEach(function(photo) {
            // 为每个图片URL创建一个<img>元素并设置其src属性
            var $img = $('<img>').attr({
                src: photo.thumbnail,
                alt: photo.title,
                class: 'img-fluid thumbnail', // Bootstrap的响应式图片类
                'data-original-url': photo.url,
                'data-title': photo.title
            }).css({
                margin: '5px', // 设置图片间隔
                maxWidth: '100px', // 设置图片最大宽度，根据需要调整
                maxHeight: '100px' // 设置图片最大高度，根据需要调整
            });

            $img.on('click', function() {
                showOriginImage($(this).data('original-url'), $(this).data('title'));
            });
            // 将<img>元素添加到div中
            $imagesDiv.append($img);
            showOriginImage(data[0].url, data[0].title);
        });
    }

    function showOriginImage(url, title) {
        $("#origin-image").attr("src", url);
        $("#origin-image").attr("alt", title);
    }

    function getProductImages(batch_number) {

        $.ajax({
            url: product_image_url,
            type: "POST",
            data: {batch_number: batch_number},
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(data) {
                addImagesToDiv(data);
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
                $('#production-input').val(data.batch_number);
                addImagesToDiv(data.urls);
            },
            error: function(xhr, status, error) {
                console.error("An error occurred: " + error);
            }
        });
    }
