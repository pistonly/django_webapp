    function startPreview() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            console.log("WebSocket is already connected.");
            return; // Exit the function to prevent a new connection
        }

        var cameraId = $("#select_camera").val();
        ws = new WebSocket("ws://" + window.location.host + "/ws/camera/");

        ws.onopen = function(e) {
            console.log("Connection established!");
            ws.send(JSON.stringify({
                'camera_id': cameraId,
                'trigger_mode': trigger_mode,
            }));
        };

        ws.onmessage = function(e) {
            var data = JSON.parse(e.data);
            $("#camera-image").attr("src", "data:image/jpeg;base64," + data.frame);
        };

        ws.onerror = function(e) {
            console.error("WebSocket error: ", e);
        };

        ws.onclose = function(e) {
            console.log("WebSocket closed");
        };
    }

    function stopPreview() {
        if (ws) {
            ws.close(1000, "stop preview.");
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
