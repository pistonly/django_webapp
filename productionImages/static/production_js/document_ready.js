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
var start_status = false;
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
            update_thumbnail(data);
        }
        if (data.message) {
            console.log(data.message);
        }
        if (data.status) {
            console.log(data);
            if (data.status == "duplicated") {
                alert("其他的网页正在运行");
                $("body").empty();
                $("body").append("<h1>页面错误:其他的网页正在运行</h1>");
            } else {
                if (data.plc_checking) {
                    $('#background-status').text("运行中...")
                        .removeClass().addClass("input-group-text bg-info");

                    set_current_running(data.current_product);
                    startOrstop(false);
                } else {
                    $('#background-status').text("空闲中...")
                        .removeClass().addClass("input-group-text bg-success");
                    startOrstop(true);
                }
            }
        }

        if (data.start_status) {
            if (data.start_status == "success") {
                $('#background-status').text("运行中...")
                    .removeClass().addClass("input-group-text bg-info");
                startOrstop(false);
            } else {
                setTimeout(()=>{
                    ws_plc.send(JSON.stringify({start: 1}));
                }, 600);
            }
        }

        if (data.speed) {
            $('#dev-speed').val(data.speed);
            $('#product-speed').val(data.speed);
        }

        if (data.hasOwnProperty("ng_full")) {
            console.log(data);
            $('#pass-num').val(data.noNG_num);
            $('#pass-rate').val(data.noNG_rate);
            // update_noNGrate($('#production-input').val(), data.ng);
        }
    };
}

function update_noNGrate(product_name, ng) {
    $.ajax({
        url: update_noNGrate_url,
        type: "POST",
        contentType: 'application/json',
        data: JSON.stringify({
            product_name: product_name,
            ng: ng,
        }),
        beforeSend: function (xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (data) {
            console.log("update success");
            console.log(data);
            $('#pass-num').val(data.noNG_num);
            $('#pass-rate').val(data.noNG_rate);
        }
    });
}

function startOrstop(start) {
    if (start) {
        $('#start-camera-background').prop("disabled", false);
        $('#stop-camera-background').prop("disabled", true);
    } else {
        $('#start-camera-background').prop("disabled", true);
        $('#stop-camera-background').prop("disabled", false);
    }
}

function set_current_running(product) {
    $('#production-input').val(product).prop("disabled", true);
}

function update_thumbnail(data) {
    if (data.thumbnail) {
        $(data.img_id).attr({
            src: data.thumbnail,
            alt: data.title,
            'data-original-url': data.url,
            'data-title': data.title
        });
    }
}

$(document).ready(function () {
    // getLatestProduct();
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
                $('#production-input').prop("disabled", true);
                $('#start-camera-background').prop("disabled", true);
                $('#stop-camera-background').prop("disabled", true);
                $('#background-status').text("启动中...")
                    .removeClass().addClass("input-group-text bg-warning");
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (response) {
                console.log("start success");
                ws_plc.send(JSON.stringify({ start: 1 }));
            }
        });
    });

    $('#stop-camera-background').click(function () {
        if (ws_plc && ws_plc.readyState === WebSocket.OPEN) {
            ws_plc.send(JSON.stringify({ "stop_signal": 1 }));
            $('#background-status').text("停止中...")
                .removeClass().addClass("input-group-text bg-warning");
            $('#production-input').prop("disabled", false);
            $('#stop-camera-background').prop("disabled", true);
        }
    });

});
