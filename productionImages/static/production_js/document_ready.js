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

var ws;
var ws_plc;

function startWS() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        console.log("WebSocket is already connected.");
        return; // Exit the function to prevent a new connection
    }

    ws = new WebSocket("ws://" + window.location.host + "/ws/camera/");

    ws.onopen = function (e) {
        console.log("Connection established!");
    };

    ws.onmessage = function (e) {
        var data = JSON.parse(e.data);
        $(data.img_id).attr({src: data.thumbnail,
                             alt: data.title,
                             'data-original-url': data.url,
                             'data-title': data.title});
    };

    ws.onerror = function (e) {
        console.error("WebSocket error: ", e);
    };

    ws.onclose = function (e) {
        console.log("WebSocket closed");
    };

    ws_plc = new WebSocket("ws://" +window.location.host + "/ws/plc_check/");
    ws_plc.onopen = function(e) {
        console.log("ws plc connection established");
        ws_plc.send(JSON.stringify({client_id: 'web'}));
    };

    ws_plc.onclose = function (e) {
        console.log("WebSocket closed");
    };

}


$(document).ready(function() {
    getLatestProduct();
    searchProduct();

    $('.grid-images').click(function () {
        const url = $(this).data('original-url');
        const title = $(this).data('title');
        $("#origin-image").attr({src: url,
                                 alt: title});
    });

    $('#start-camera-background').click(function (){
        console.log("start");
        $.ajax({
            url: start_camera_url,
            type: 'POST',
            data: {
                batch_number: $('#production-input').val(),
                uri: "ws://" + window.location.host + "/ws/camera/",
                upload_url: $('#upload-url').data('url')
            },
            beforeSend: function (xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(response) {
                console.log("start success");
            }
        });
    });

    $('#stop-camera-background').click(function () {
        console.log("stop");
        if (ws && ws.readyState === WebSocket.OPEN){
            ws.send("stop");
        }
    });

});
