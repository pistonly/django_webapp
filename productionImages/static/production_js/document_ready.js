function searchProduct(){
    var $input = $("#production-input");
    var search_url = $("#search-batch-url").data("url");

    $input.autocomplete({
        source: function(request, response) {
            $.ajax({
                url: search_url,
                dataType: "json",
                data: { term: request.term },
                success: function(data) {
                    // Ensure the data is mapped to an array of objects with label and value
                    response($.map(data, function(item) {
                        return { label: item, value: item };
                    }));
                }
            });
        },
        select: function(event, ui) {
            getProductImages(ui.item.value);
        }
    });
}

var ws_plc;

function startWS() {
    ws_plc = new WebSocket("ws://" + window.location.host + "/ws/plc_check/");
    ws_plc.onopen = function () {
        ws_plc.send(JSON.stringify({ client_id: 'web' }));
        console.log("ws plc connection established");
    };

    ws_plc.onclose = function (e) {
        console.log("ws_plc WebSocket closed");
    };

    ws_plc.onerror = function (e) {
        console.error("ws_plc WebSocket error: ", e);
    };
    ws_plc.onmessage = function(e) {
        console.log(e);
        const data = JSON.parse(e.data);
        if (data.img_id) {
            update_thumbnail(data.img_id, data.gallery_id);
        }
    };
}

function update_thumbnail(img_id, gallery_id) {
    console.log("update thumbnail");
    $.ajax({
        url: gallery_url,
        type: "GET",
        data: { "gallery_title": gallery_id },
        success: function (data) {
            if (data.thumbnail) {
                $(img_id).attr({
                    src: data.thumbnail,
                    alt: data.title,
                    'data-original-url': data.url,
                    'data-title': data.title
                });
            } else {
                console.log(data);
            }
        }
    });
}

$(document).ready(function () {
    getLatestProduct();
    searchProduct();
    startWS();

    $('.grid-images').click(function () {
        const url = $(this).data('original-url');
        const title = $(this).data('title');
        $("#origin-image").attr({src: url,
                                 alt: title});
    });

    $('#start-camera-background').click(function (){
        console.log("start");
        const batch_number = $('#production-input').val();
        if (batch_number.length == 0) {
            alert("产品批号错误");
            return;
        }
        $.ajax({
            url: start_camera_url,
            type: 'POST',
            data: {
                batch_number: batch_number,
                uri: "ws://" + window.location.host + "/ws/plc_check/",
                upload_url: $('#upload-url').data('url')
            },
            beforeSend: function (xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(response) {
                ws_plc.send(JSON.stringify({start: 1}));
                console.log("start success");
            }
        });
    });

    $('#stop-camera-background').click(function () {
        if (ws_plc && ws_plc.readyState === WebSocket.OPEN){
            ws_plc.send(JSON.stringify({"stop_signal": 1}));
        }
    });

});
