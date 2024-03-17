function getCameraList() {

    // Use jQuery's ajax method to fetch data
    $.ajax({
        url: camera_list_url,
        type: 'GET',
        dataType: 'json',
        success: function(data) {
            const cameras = data.cameras;
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
        },
        error: function(xhr, status, error) {
            console.error('Error fetching camera list:', error);
        }
    });
}


function getCameraParameters() {
    console.log($('#select_camera').val());
    $.ajax({
        url: '/api/camera/parameters/',
        type: 'GET',
        data: {
            camera_id: $('#select_camera').val()
        },
        success: function(data) {
            // 处理数据...
            console.log(data);
            // Update camera-name
            $('#camera-name-sel').val(data.name);

            // Update trigger mode radios
            $('input[name="trigger"][value="' + data.triggerMode + '"]').prop('checked', true);
            trigger_mode = data.triggerMode;
            $('#triggerDelayTime').val(data.triggerDelayTime);
            $('#triggerCount').val(data.triggerCount);
            /* $('input[name="trigger"][value="' + data.triggerMode + '"]').trigger('change'); */

            // Update ae_state time
            $('input[name="ae_state"][value="' + data.ae_state + '"]').prop('checked', true);
            $('#manualExposureTime').val(data.expose_time);
            $('#ae_target').attr('min', data.ae_target_range[0])
                .attr('max', data.ae_target_range[1])
                .val(data.ae_target)
            $('input[name="ae_state"][value="' + data.ae_state + '"]').trigger('change');

            // Update gamma and contrast values and ranges
            $('#gamma-value').text(data.lut_gamma);
            $('#gamma-range').attr('min', data.lut_gamma_range[0])
                .attr('max', data.lut_gamma_range[1])
                .val(data.lut_gamma);

            $('#contrast-value').text(data.lut_contrast);
            $('#contrast-range').attr('min', data.lut_contrast_range[0])
                .attr('max', data.lut_contrast_range[1])
                .val(data.lut_contrast);

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
        }
    });
}
