function updateCameraList(cameras) {
    const selectCamera = $("#select_camera");

    // Clear existing options using jQuery
    selectCamera.empty();

    // Add new options for each camera
    cameras.forEach(function(camera) {
        selectCamera.append($('<option></option>').val(camera).text(camera));
    });

    // Default to the first camera, if available
    if (cameras.length > 0) {
        selectCamera.val(cameras[0]);
    }
    // 
    getCameraParameters();
}

function updateSettingPan(data) {
    // Update camera-name
    $('#camera-name-sel').val(data.name);

    // Update trigger mode radios
    $('input[name="trigger"][value="' + data.triggermode + '"]').prop('checked', true);
    trigger_mode = data.triggermode;
    $('#triggerDelayTime').val(data.triggerdelaytime);
    $('#triggerCount').val(data.triggercount);
    /* $('input[name="trigger"][value="' + data.triggerMode + '"]').trigger('change'); */

    // Update ae_state time
    $('input[name="ae_state"][value="' + data.aestate + '"]').prop('checked', true);
    $('#manualExposureTime').val(data.exposuretime);
    $('#ae_target').attr('min', data.ae_target_range[0])
        .attr('max', data.ae_target_range[1])
        .val(data.aetarget);
    $('input[name="ae_state"][value="' + data.aestate + '"]').trigger('change');

    // Update gamma and contrast values and ranges
    $('#gamma-value').text(data.gamma);
    $('#gamma-range').attr('min', data.gamma_range[0])
        .attr('max', data.gamma_range[1])
        .val(data.gamma);
    $('#analoggain-value').text(data.analoggain);
    $('#analoggain-range').attr('min', data.analoggain_range[0])
        .attr('max', 100)
        .val(data.analoggain);

    $('#contrast-value').text(data.contrast);
    $('#contrast-range').attr('min', data.contrast_range[0])
        .attr('max', data.contrast_range[1])
        .val(data.contrast);

    // update rotation
    console.log("data.rotation");
    console.log(data.rotation);
    $('#rotation').val(data.rotation);

    // roi
    $('#roi-x0-0').val(data.roi0[0]);
    $('#roi-y0-0').val(data.roi0[1]);
    $('#roi-x1-0').val(data.roi0[2]);
    $('#roi-y1-0').val(data.roi0[3]);
    $('#roi-x0-1').val(data.roi1[0]);
    $('#roi-y0-1').val(data.roi1[1]);
    $('#roi-x1-1').val(data.roi1[2]);
    $('#roi-y1-1').val(data.roi1[3]);
    if (data.roi0_disabled > 0) {
        $('#check-roi-0').prop('disabled', true);
    } else {
        $('#check-roi-0').prop('disabled', false);
    }
    if (data.roi1_disabled > 0) {
        $('#check-roi-1').prop('disabled', true);
    } else {
        $('#check-roi-1').prop('disabled', false);
    }

    // configure
    $('#configure-file').val(data.configure_name_alias);
    // update configure files
    $('#configure-files').empty();
    data.configure_f.forEach(function(conf) {
        $('#configure-files').append(
            $('<a class="dropdown-item config-option" ></a>').val(conf).text(conf));
    });
}

function getCameraParameters() {
    console.log($('#select_camera').val());
    ws.send(JSON.stringify({
        "get_camera_info": 1,
        "sn": $('#select_camera').val()
    }));
}

function getCameraList() {
    ws.send(JSON.stringify({
        "get_camera_list": 1,
    }));
}
