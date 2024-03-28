function startWS() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        console.log("WebSocket is already connected.");
        return; // Exit the function to prevent a new connection
    }

    var cameraId = $("#select_camera").val();
    ws = new WebSocket("ws://" + window.location.host + "/ws/camera/");

    ws.onopen = function(e) {
        console.log("Connection established!");
        // get camera list
        getCameraList();
    };

    ws.onmessage = function(e) {
        var data = JSON.parse(e.data);
        console.log(data);
        if (data.hasOwnProperty("message")) {
            console.log(data.message);
        }

        // camera_list
        if (data.hasOwnProperty("cameras")) {
            updateCameraList(data.cameras);
            return;
        }

        // camera info
        if (data.hasOwnProperty("camera_info")) {
            updateSettingPan(data.camera_info);
            return;
        }

        // arb-reg-r
        if (data.hasOwnProperty("arb_val")) {
            if (!data.arb_success) {
                alert(data.arb_val);
            } else {
                $('#arb-val').val(data.arb_val);
            }
            return;
        }

        // preview
        if (data.frame) {
            $("#camera-image").attr("src", "data:image/jpeg;base64," + data.frame);
            return;
        }

        if (data.hasOwnProperty("plc_online")) {
            if (data.plc_online) {
                $('#plc-status-on').css('display', 'block');
                $('#plc-status-off').css('display', 'none');

                data.M_data.forEach(function (m) {
                    console.log(m);
                    $(m.id).val(m.val);
                });
                data.D_data.forEach(function (d) {
                    console.log(d);
                    $(d.id).val(d.val);
                });
            } else {
                // off-line
                $('#plc-status-on').css('display', 'none');
                $('#plc-status-off').css('display', 'block');
                $('#offline-txt').text("离线，请点击连接");
            }
        }

        if (data.hasOwnProperty("plc_trigger_return")) {
            $('#trigger-btn').prop("disabled", false);
        }

        if (data.hasOwnProperty("soft_trigger_return")) {
            $('#trigger-btn').prop("disabled", false);
        }
    };

    ws.onerror = function(e) {
        console.error("WebSocket error: ", e);
    };

    ws.onclose = function(e) {
        console.log("WebSocket closed");
    };
    $('#start-preview').prop('disabled', false);
    $('#stop-preview').prop('disabled', true);
}

function startPreview() {
    if (ws) {
        console.log("start preview");
        ws.send(JSON.stringify({
            "start_preview": 1,
            "trigger_mode": trigger_mode,
            "sn": $('#select_camera').val(),
        }));
    }
    $('#start-preview').prop('disabled', true);
    $('#stop-preview').prop('disabled', false);
}

function stopPreview() {
    if (ws) {
        console.log("stop preview");
        ws.send(JSON.stringify({
            "stop_preview": 1
        }));
        $('#start-preview').prop('disabled', false);
        $('#stop-preview').prop('disabled', true);
    }
}


function saveImg() {
    console.log("saveImg");
    const camera_grab_url = $("#camera-grab-url").data("url");
    console.log(camera_grab_url);
    $.ajax({
        url: camera_grab_url,
        type: 'POST',
        data: {
            camera_id: $('#select_camera').val()
        },
        beforeSend: function(xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function(data) {
            console.log(data);
        }
    });
}
