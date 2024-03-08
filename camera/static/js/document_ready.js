$(document).ready(function() {

    startWS();

    const continous_mode_radio = $('#continous-mode');
    $('#select_camera').change(getCameraParameters);
    // Listen for changes on the ae_state radio buttons
    $('input[name="ae_state"]').change(function() {
        // Check if the auto ae_state is selected
        if ($('#autoExposure').is(':checked')) {
            $('#auto-exposure-settings').show(); // Show auto ae_state settings
            $('#manual-exposure-settings').hide(); // Hide manual ae_state settings
        } else if ($('#manualExposure').is(':checked')) {
            $('#auto-exposure-settings').hide(); // Hide auto ae_state settings
            $('#manual-exposure-settings').show(); // Show manual ae_state settings
        }
        // setting
        var exposureMode = $(this).val();
        $.ajax({
            url: '/api/camera/parameters/',
            type: 'POST',
            data: {
                camera_id: $('#select_camera').val(),
                ae_state: exposureMode,
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(response) {
                // 成功时的处理，例如显示一个消息
                console.log('ae_state mode changed to: ' + exposureMode);
                // 也可以在页面上显示一些反馈
                $('#status').text('ae_state mode changed to: ' + exposureMode);
            },
            error: function(xhr, status, error) {
                // 错误处理
                console.error('An error occurred: ' + error);
                $('#status').text('Error changing ae_state mode.');
            }
        });
    });

    // update camera list
    getCameraList();

    $('#manualExposureTime').change(function() {
        $.ajax({
            url: '/api/camera/parameters/',
            type: 'POST',
            data: {
                camera_id: $('#select_camera').val(),
                exposureTime: $('#manualExposureTime').val(),
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(response) {
                // 成功时的处理，例如显示一个消息
                console.log('exposure time changed');
                // 也可以在页面上显示一些反馈
                $('#status').text('exposure time changed');
            },
            error: function(xhr, status, error) {
                // 错误处理
                console.error('An error occurred: ' + error);
                $('#status').text('Error changing exposure time.');
            }
        });
    });

    // resolution
    $('.resolution-option').click(function(e) {
        // 阻止<a>标签的默认行为
        e.preventDefault();
        // 获取点击的分辨率选项的文本，并设置到输入框中
        var resolution = $(this).text();
        $('#resolution-input').val(resolution);
        // setting 
        $.ajax({
            url: '/api/camera/parameters/',
            type: 'POST',
            data: {
                camera_id: $('#select_camera').val(),
                resolution: resolution,
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(data) {
                console.log("resolution setting success");
            }
        });
    });

    // config 
    $('.config-option').click(function(e) {
        // 阻止<a>标签的默认行为
        e.preventDefault();
        // 获取点击的分辨率选项的文本，并设置到输入框中
        var configure_file = $(this).text();
        $('#configure-file').val(configure_file);
        // setting 
    });
    // trigger mode
    // Listen for changes on the trigger mode radio buttons
    $('input[name="trigger"]').change(function() {
        if (continous_mode_radio.is(':checked')) {
            // Show the trigger button when "软件触发" is selected
            $('#trigger-settings').hide();
            $('#start-preview').prop('disabled', false);
            $('#stop-preview').prop('disabled', false);
            // stop ws
            stopPreview();
        } else {
            // Hide the trigger button for other selections
            $('#trigger-settings').show();
            // stop ws
            stopPreview();
        }
        trigger_mode = $(this).val();
        // setting
        $.ajax({
            url: '/api/camera/parameters/',
            type: 'POST',
            data: {
                camera_id: $('#select_camera').val(),
                triggerMode: trigger_mode,
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(data) {
                console.log("triggerMode setting success");
                startPreview();
                if (!continous_mode_radio.is(':checked')) {
                    $('#start-preview').prop('disabled', true);
                    $('#stop-preview').prop('disabled', true);
                }
            }
        });
    });

    $('#triggerDelayTime').change(function() {
        // setting
        $.ajax({
            url: '/api/camera/parameters/',
            type: 'POST',
            data: {
                camera_id: $('#select_camera').val(),
                triggerDelayTime: $(this).val(),
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(data) {
                console.log("triggerDelayTime setting success");
            }
        });
    });

    $('#triggerCount').change(function() {
        // setting
        $.ajax({
            url: '/api/camera/parameters/',
            type: 'POST',
            data: {
                camera_id: $('#select_camera').val(),
                triggerCount: $(this).val(),
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(data) {
                console.log("triggerDelayTime setting success");
            }
        });
    });

    // lut mapping
    $('#gamma-range').on('input', function() {
        $('#gamma-value').text($(this).val());
    });

    $('#gamma-range').on('mouseup', function() {
        // 发送数据到后端url1
        $.ajax({
            url: '/api/camera/parameters/',
            type: 'POST',
            data: {
                camera_id: $('#select_camera').val(),
                lut_gamma: $(this).val(),
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(data) {
                console.log("lut_gamma setting success");
            }
        });
    });

    $('#contrast-range').on('input', function() {
        $('#contrast-value').text($(this).val());
    });

    $('#contrast-range').on('mouseup', function() {
        // 发送数据到后端url1
        $.ajax({
            url: '/api/camera/parameters/',
            type: 'POST',
            data: {
                camera_id: $('#select_camera').val(),
                lut_contrast: $(this).val(),
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function(data) {
                console.log("contrast setting success");
            }
        });
    });

    $('#trigger-btn').click(function (e) {
        // 阻止<a>标签的默认行为
        e.preventDefault();
        ws.send(JSON.stringify({
            'camera_id': $('#select_camera').val(),
            'trigger_mode': trigger_mode,
            'soft_trigger': 1
        }));
    });

    $('#save-configure').click(function() {
        const configure = $('#configure-file');
        if (configure.val()){
            $.ajax({
                url: save_configure_url,
                type: 'POST',
                data: {
                    camera_id: $('#select_camera').val(),
                    config_f: configure.val(),
                },
                beforeSend: function (xhr) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success: function (data) {
                    console.log("contrast setting success");
                }
            });
        }
    });

    $('#load-configure').click(function() {
        const configure = $('#configure-file');
        if (configure.val()){
            $.ajax({
                url: load_configure_url,
                type: 'POST',
                data: {
                    camera_id: $('#select_camera').val(),
                    config_f: configure.val(),
                },
                beforeSend: function (xhr) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success: function (data) {
                    console.log("contrast setting success");
                }
            });
        }
    });

    $('#reset-configure').click(function() {
        const configure = $('#configure-file');
        if (configure.val()){
            $.ajax({
                url: reset_configure_url,
                type: 'POST',
                data: {
                    camera_id: $('#select_camera').val(),
                    config_f: configure.val(),
                },
                beforeSend: function (xhr) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success: function (data) {
                    console.log("contrast setting success");
                }
            });
        }
    });
});
