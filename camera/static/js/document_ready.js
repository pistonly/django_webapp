$(document).ready(function() {

    startWS();

    $('#plc-settings').on('show.bs.collapse', function() {
        $('.collapse-indicator-1').removeClass('fa-chevron-down').addClass('fa-chevron-up');
    }).on('hide.bs.collapse', function() {
        $('.collapse-indicator-1').removeClass('fa-chevron-up').addClass('fa-chevron-down');
    });

    $('#camera-setting').on('show.bs.collapse', function() {
        $('.collapse-indicator-0').removeClass('fa-chevron-down').addClass('fa-chevron-up');
    }).on('hide.bs.collapse', function() {
        $('.collapse-indicator-0').removeClass('fa-chevron-up').addClass('fa-chevron-down');
    });

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
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                "aeState": exposureMode
            }
        }));
    });


    $('#manualExposureTime-btn').click(function() {
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                exposureTime: $('#manualExposureTime').val(),
            }
        }));
    });

    $('#ae_target-btn').click(function() {
        console.log("here");
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                aeTarget: $('#ae_target').val(),
            }
        }));
    });

    // config 
    $('#configure-files').on('click', '.config-option', function() {
        var text = $(this).text(); // 获取点击项的文本
        $('#configure-file').val(text); // 将文本设置为input的值
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
        let trigger_mode_val = trigger_mode;
        if (trigger_mode_val == "2"){
            trigger_mode_val = "1";
        }
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                triggerMode: trigger_mode_val,
            }
        }));
        if (!continous_mode_radio.is(':checked')) {
            $('#start-preview').prop('disabled', true);
            $('#stop-preview').prop('disabled', true);
        }

    });

    $('#triggerDelayTime').change(function() {
        // setting
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                triggerDelayTime: $(this).val(),
            }
        }));
    });

    // lut mapping
    $('#gamma-range').on('input', function() {
        $('#gamma-value').text($(this).val());
    });

    $('#gamma-range').on('mouseup', function() {
        // 发送数据到后端url1
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                gamma: $(this).val(),
            }
        }));
    });


    $('#contrast-range').on('input', function() {
        $('#contrast-value').text($(this).val());
    });

    $('#contrast-range').on('mouseup', function() {
        // 发送数据到后端url1
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                contrast: $(this).val(),
            }
        }));
    });

    $('#name-btn').click(function(e) {
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                name: $('#camera-name-sel').val(),
            }
        }));
    });

    $('#rotation-left').click(function(e) {
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                rotation: "plus",
            }
        }));
    });

    $('#rotation-right').click(function (e) {
        ws.send(JSON.stringify({
            "set_camera": 1,
            "sn": $('#select_camera').val(),
            "params": {
                rotation: "minus",
            }
        }));
    });

    $('#trigger-btn').click(function(e) {
        // 阻止<a>标签的默认行为
        e.preventDefault();
        ws.send(JSON.stringify({
            'camera_id': $('#select_camera').val(),
            'trigger_mode': trigger_mode,
            'soft_trigger': 1
        }));
        $(this).prop("disabled", true);
    });


    $('#save-configure').click(function() {
        const configure = $('#configure-file');
        if (configure.val()) {
            ws.send(JSON.stringify({
                "save_configure": 1,
                "sn": $('#select_camera').val(),
                config_f: configure.val(),
            }));
        }
    });

    $('#load-configure').click(function () {
        const configure = $('#configure-file');
        if (configure.val()) {
            ws.send(JSON.stringify({
                "load_configure": 1,
                "sn": $('#select_camera').val(),
                config_f: configure.val(),
            }));
        }
    });

    $('#reset-configure').click(function () {
        const configure = $('#configure-file');
        if (configure.val()) {
            ws.send(JSON.stringify({
                "reset_configure": 1,
                "sn": $('#select_camera').val(),
                config_f: configure.val(),
            }));
        }
    });

});
